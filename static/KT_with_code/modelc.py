import configc as config
import math
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import copy
import os

import torch
from torch import nn
from transformers import AutoTokenizer, AutoModel
from prob_data import *
from tqdm import tqdm

def future_mask(seq_length):
    future_mask = np.triu(np.ones((1, seq_length, seq_length)), k=1).astype('bool')
    return torch.from_numpy(future_mask)


def get_clones(module, N):
    return nn.ModuleList([copy.deepcopy(module) for _ in range(N)])


def attention(q, k, v, d_k, positional_bias=None, mask=None, dropout=None):
    scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(d_k)
    if mask is not None:
        mask = mask.unsqueeze(1)
    if positional_bias is not None:
        scores = scores + positional_bias
    if mask is not None:
        scores = scores.masked_fill(mask, -1e9)
    scores = F.softmax(scores, dim=-1)
    if dropout is not None:
        scores = dropout(scores)
    output = torch.matmul(scores, v)
    return output


class MultiHeadAttention(nn.Module):
    def __init__(self, embed_dim, num_heads, dropout=0.1):
        super(MultiHeadAttention, self).__init__()

        self.d_model = embed_dim
        self.d_k = embed_dim // num_heads
        self.h = num_heads

        self.q_linear = nn.Linear(embed_dim, embed_dim)
        self.v_linear = nn.Linear(embed_dim, embed_dim)
        self.k_linear = nn.Linear(embed_dim, embed_dim)
        self.dropout = nn.Dropout(dropout)
        self.out = nn.Linear(embed_dim, embed_dim)

    def forward(self, q, k, v, positional_bias=None,
                attn_mask=None):
        bs = q.size(0)

        k = self.k_linear(k).view(bs, -1, self.h, self.d_k)
        q = self.q_linear(q).view(bs, -1, self.h, self.d_k)
        v = self.v_linear(v).view(bs, -1, self.h, self.d_k)

        k = k.transpose(1, 2)
        q = q.transpose(1, 2)
        v = v.transpose(1, 2)

        scores = attention(q, k, v, self.d_k, positional_bias, attn_mask, self.dropout)

        concat = scores.transpose(1, 2).contiguous() \
            .view(bs, -1, self.d_model)

        output = self.out(concat)
        return output


class FFN(nn.Module):
    def __init__(self, d_model, d_ffn, dropout):
        super(FFN, self).__init__()
        self.lr1 = nn.Linear(d_model, d_ffn)
        self.act = nn.ReLU()
        self.lr2 = nn.Linear(d_ffn, d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        x = self.lr1(x)
        x = self.act(x)
        x = self.dropout(x)
        x = self.lr2(x)
        return x


class LANAEncoder(nn.Module):
    def __init__(self, d_model, n_heads, d_ffn, dropout, max_seq):
        super(LANAEncoder, self).__init__()
        self.max_seq = max_seq

        self.multi_attn = MultiHeadAttention(embed_dim=d_model, num_heads=n_heads, dropout=dropout)
        self.layernorm1 = nn.LayerNorm(d_model)
        self.layernorm2 = nn.LayerNorm(d_model)
        self.dropout1 = nn.Dropout(dropout)
        self.dropout2 = nn.Dropout(dropout)

        self.ffn = FFN(d_model, d_ffn, dropout)

    def forward(self, x, pos_embed, mask):
        out = x
        att_out = self.multi_attn(out, out, out, positional_bias=pos_embed, attn_mask=mask)
        out = out + self.dropout1(att_out)
        out = self.layernorm1(out)

        ffn_out = self.ffn(out)
        out = self.layernorm2(out + self.dropout2(ffn_out))
        return out


class LANADecoder(nn.Module):
    def __init__(self, d_model, n_heads, d_ffn, dropout, max_seq):
        super(LANADecoder, self).__init__()
        self.max_seq = max_seq

        self.multi_attn_1 = MultiHeadAttention(embed_dim=d_model, num_heads=n_heads, dropout=dropout)
        self.multi_attn_2 = MultiHeadAttention(embed_dim=d_model, num_heads=n_heads, dropout=dropout)

        self.layernorm1 = nn.LayerNorm(d_model)
        self.layernorm2 = nn.LayerNorm(d_model)
        self.layernorm3 = nn.LayerNorm(d_model)
        self.dropout1 = nn.Dropout(dropout)
        self.dropout2 = nn.Dropout(dropout)
        self.dropout3 = nn.Dropout(dropout)

        self.ffn = FFN(d_model, d_ffn, dropout)

    def forward(self, x, memory, pos_embed, mask1, mask2):
        out = x
        att_out_1 = self.multi_attn_1(out, out, out,
                                      positional_bias=pos_embed, attn_mask=mask1)
        out = out + self.dropout1(att_out_1)
        out = self.layernorm1(out)

        att_out_2 = self.multi_attn_2(out, memory, memory,
                                      positional_bias=pos_embed, attn_mask=mask2)
        out = out + self.dropout2(att_out_2)
        out = self.layernorm2(out)

        ffn_out = self.ffn(out)
        out = self.layernorm3(out + self.dropout3(ffn_out))
        return out


class PositionalBias(nn.Module):
    def __init__(self, max_seq, embed_dim, num_heads, bidirectional=True, num_buckets=32,
                 max_distance=config.MAX_SEQ):  #####32
        super(PositionalBias, self).__init__()
        self.d_model = embed_dim
        self.d_k = embed_dim // num_heads
        self.h = num_heads
        self.bidirectional = bidirectional
        self.num_buckets = num_buckets
        self.max_distance = max_distance

        self.pos_embed = nn.Embedding(max_seq, embed_dim)  # Encoder position Embedding
        self.pos_query_linear = nn.Linear(embed_dim, embed_dim)
        self.pos_key_linear = nn.Linear(embed_dim, embed_dim)
        self.pos_layernorm = nn.LayerNorm(embed_dim)

        self.relative_attention_bias = nn.Embedding(32, config.N_HEADS)

    def forward(self, pos_seq):
        bs = pos_seq.size(0)

        pos_embed = self.pos_embed(pos_seq)
        pos_embed = self.pos_layernorm(pos_embed)

        pos_query = self.pos_query_linear(pos_embed)
        pos_key = self.pos_key_linear(pos_embed)

        pos_query = pos_query.view(bs, -1, self.h, self.d_k).transpose(1, 2)
        pos_key = pos_key.view(bs, -1, self.h, self.d_k).transpose(1, 2)

        absolute_bias = torch.matmul(pos_query, pos_key.transpose(-2, -1)) / math.sqrt(self.d_k)
        relative_position = pos_seq[:, None, :] - pos_seq[:, :, None]

        relative_buckets = 0
        num_buckets = self.num_buckets
        if self.bidirectional:
            num_buckets = num_buckets // 2
            relative_buckets += (relative_position > 0).to(torch.long) * num_buckets
            relative_bias = torch.abs(relative_position)
        else:
            relative_bias = -torch.min(relative_position, torch.zeros_like(relative_position))

        max_exact = num_buckets // 2
        is_small = relative_bias < max_exact

        relative_bias_if_large = max_exact + (
                torch.log(relative_bias.float() / max_exact)
                / math.log(self.max_distance / max_exact)
                * (num_buckets - max_exact)
        ).to(torch.long)
        relative_bias_if_large = torch.min(
            relative_bias_if_large, torch.full_like(relative_bias_if_large, num_buckets - 1)
        )

        relative_buckets += torch.where(is_small, relative_bias, relative_bias_if_large)
        relative_position_buckets = relative_buckets.to(pos_seq.device)

        relative_bias = self.relative_attention_bias(relative_position_buckets)
        relative_bias = relative_bias.permute(0, 3, 1, 2)

        position_bias = absolute_bias + relative_bias
        return position_bias


class LANA(nn.Module):
    def __init__(self, d_model, n_head, n_encoder, n_decoder, dim_feedforward, dropout,
                 max_seq, n_exercises, n_probfield, n_resp, n_concepts, n_state):  ####one -hot  next to do
        super(LANA, self).__init__()
        self.max_seq = max_seq

        self.pos_embed = PositionalBias(max_seq, d_model, n_head, bidirectional=False, num_buckets=32,
                                        max_distance=max_seq)

        self.encoder_resp_embed = nn.Embedding(n_resp + 2, d_model,
                                               padding_idx=config.PAD)
        self.encoder_eid_embed = nn.Embedding(n_exercises + 2, d_model,
                                              padding_idx=config.PAD)
        self.encoder_concept_embed = nn.Embedding(n_concepts + 2, d_model,
                                                  padding_idx=config.PAD)  # Part Embedding, 0 for padding
        self.encoder_linear = nn.Linear(5 * d_model, d_model)  #########3
        self.encoder_layernorm = nn.LayerNorm(d_model)
        self.encoder_dropout = nn.Dropout(dropout)

        self.decoder_resp_embed = nn.Embedding(n_resp + 2, d_model,
                                               padding_idx=config.PAD)
        self.decoder_linear = nn.Linear(1 * d_model, d_model)
        self.decoder_layernorm = nn.LayerNorm(d_model)
        self.decoder_dropout = nn.Dropout(dropout)

        self.encoder = get_clones(LANAEncoder(d_model, n_head, dim_feedforward, dropout, max_seq), n_encoder)
        self.decoder = get_clones(LANADecoder(d_model, n_head, dim_feedforward, dropout, max_seq), n_decoder)

        self.layernorm_out = nn.LayerNorm(d_model)
        self.classifier = nn.Linear(d_model, 1)
        self.classifier2 = nn.Linear(d_model, config.TOTAL_PART)  #####8
        self.classifier3 = nn.Linear(d_model, n_state)

        # self.code_layer= nn.Linear(768,d_model)
        # self.code_layer1 = nn.Linear(d_model, 1)


        self.relu = torch.nn.ReLU()
        self.sigmoid = torch.nn.Sigmoid()

        # self.CodeBERT = AutoModel.from_pretrained("microsoft/codebert-base").cuda()
        # self.tokenizer = AutoTokenizer.from_pretrained("microsoft/codebert-base")
        # self.load_code()



    def load_code(self):
        self.code={}
        print('Loading Code...')
        for idx,(fid, pid) in tqdm(enumerate(prob_list)):
            if os.path.exists(r"code/(%d,%d).txt" % (fid, pid)):
                f = open(r"code/(%d,%d).txt" % (fid, pid))
                self.code[idx+2] = f.read()



    def get_pos_seq(self):
        return torch.arange(self.max_seq).unsqueeze(0)


    def _get_param_from_input(self, input):
        return (
            input["userid"].long().cuda(),
            input["probid"].long().cuda(),
            input["judgestatus"].long().cuda(),
            input["concept0"].long().cuda(),
            input["concept1"].long().cuda(),
            input["concept2"].long().cuda(),
        )

    def id_to_code_vector(self,id):
        print(id)
        if id in self.code:
            code_tokens = self.tokenizer.tokenize(self.code[id])
            tokens = code_tokens + [self.tokenizer.sep_token]
            tokens_ids = self.tokenizer.convert_tokens_to_ids(tokens)
            context_embeddings = self.CodeBERT(torch.tensor(tokens_ids)[None, :])[1]
            return context_embeddings
        else:
            return 0

    def forward(self, input):
        r_uid, r_exercise_seq, r_resp_seq, r_concept0_seq, r_concept1_seq, r_concept2_seq = self._get_param_from_input(
            input)
        pos_embed = self.pos_embed(self.get_pos_seq().to(r_exercise_seq.device))

        inter_seq = self.encoder_resp_embed(r_resp_seq)

        exercise_seq = self.encoder_eid_embed(r_exercise_seq)
        concept0_seq = self.encoder_concept_embed(r_concept0_seq)
        concept1_seq = self.encoder_concept_embed(r_concept1_seq)
        concept2_seq = self.encoder_concept_embed(r_concept2_seq)



        # flag1=False
        # for prob_seq in r_exercise_seq:
        #     flag=False
        #     for prob in prob_seq:
        #         code=self.code[prob] if prob in self.code else ""
        #         code_tokens = self.tokenizer.tokenize(code)
        #         tokens = code_tokens + [self.tokenizer.sep_token]
        #         tokens_ids = self.tokenizer.convert_tokens_to_ids(tokens)
        #         tokens_ids=torch.tensor(tokens_ids)[None, :].cuda()
        #         if flag:
        #             context_embedding = torch.cat([context_embedding,self.CodeBERT(tokens_ids)[1]]).squeeze(dim=1)
        #         else:
        #             context_embedding=self.CodeBERT(tokens_ids)[1]
        #             flag=True
        #         #context_embeddings.append(self.CodeBERT(tokens_ids)[1])
        #     if flag1:
        #         batch_context_embedding =torch.cat([batch_context_embedding,torch.unsqueeze(context_embedding,0)])
        #     else:
        #         batch_context_embedding =torch.unsqueeze(context_embedding,0)
        #         flag1=True
        # batch_context_embedding=self.code_layer(batch_context_embedding)
        # diff=self.sigmoid(self.code_layer1(batch_context_embedding))


        encoder_input = torch.cat([exercise_seq, concept0_seq, concept1_seq, concept2_seq,inter_seq,],
                                  dim=-1)  ####exercise_seq,
        encoder_input = self.encoder_linear(encoder_input)
        encoder_input = self.encoder_layernorm(encoder_input)
        encoder_input = self.encoder_dropout(encoder_input)

        resp_seq = self.decoder_resp_embed(r_resp_seq)

        decoder_input = torch.cat([resp_seq], dim=-1)
        decoder_input = self.decoder_linear(decoder_input)
        decoder_input = self.decoder_layernorm(decoder_input)
        decoder_input = self.decoder_dropout(decoder_input)

        attn_mask = future_mask(self.max_seq).cuda()

        encoding = encoder_input
        for mod in self.encoder:
            encoding = mod(encoding, pos_embed, attn_mask)

        decoding = decoder_input
        for mod in self.decoder:
            decoding = mod(decoding, encoding, pos_embed,
                           attn_mask, attn_mask)

        predict = self.classifier(decoding)
        predict2 = self.classifier3(decoding)

        target_mask = (input["probid"] != config.PAD).cuda()

        target_mask2 = target_mask.unsqueeze(-1)
        tl_predict = torch.masked_select(predict2, target_mask2)
        tl_predict2 = tl_predict.reshape(-1, config.STATE_DIMS)

        target_mask2 = target_mask.unsqueeze(-1)
        tl_predict1 = torch.masked_select(predict, target_mask2)
        tl_predict1 = tl_predict1.reshape(-1, 1)

        e_concept0 = torch.masked_select(r_concept0_seq, target_mask) - 2
        e_concept1 = torch.masked_select(r_concept1_seq, target_mask) - 2
        e_concept2 = torch.masked_select(r_concept2_seq, target_mask) - 2  # probability

        # print('e_concept0',e_concept0.shape,e_concept0)

        concept_onehot0 = torch.nn.functional.one_hot(e_concept0.to(torch.int64), config.TOTAL_PART)
        concept_onehot1 = torch.nn.functional.one_hot(e_concept1.to(torch.int64), config.TOTAL_PART)
        concept_onehot2 = torch.nn.functional.one_hot(e_concept2.to(torch.int64), config.TOTAL_PART)
        concept_onehot = (concept_onehot0 + concept_onehot1 + concept_onehot2).to(torch.float)

        probids = torch.masked_select(r_exercise_seq, target_mask) - 2
        stu_emb = tl_predict2
        #print(stu_emb.shape)
        #print((stu_emb * concept_onehot).shape)
        #input_x = e_discrimination * (stu_emb - k_difficulty) * concept_onehot
        target_mask2 = target_mask.unsqueeze(-1)
        # diff = torch.masked_select(diff, target_mask2)
        output0=(stu_emb * concept_onehot).sum(axis=1)#*diff



        # return predict5.squeeze(-1), tl_predict2.cpu().detach().numpy(), e_concept0,  r_exercise_seq, r_concept0_seq, r_resp_seq
        return output0.squeeze(-1), stu_emb