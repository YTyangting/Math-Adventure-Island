import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
from model.DGKT import MappingLayer, KnowledgeDecoder

class Raw_ConceptEmbedding(nn.Module):
    def __init__(self, c_list, d_model=256):
        super().__init__()
        self.concept_embs = nn.ParameterList([nn.Parameter(torch.rand(max_c + 1, d_model)) for max_c in c_list])
        self.centroid_emb = None
        self.A_matrix = None
        self.cluster_model = None
        self.c_list = c_list
        self.freedom = 0.1

    def forward(self, concept_seq, domain, use_centroid=None, freedom=0.1):
        count = torch.sum(concept_seq, dim=-1, keepdim=True)
        count[count == 0] = 1
        concept_seq = concept_seq / count
        concept_embedding = torch.matmul(concept_seq, self.concept_embs[domain])

        return concept_embedding


class Rash_ConceptEmbedding(nn.Module):
    def __init__(self, c_list, d_model=256):
        super().__init__()
        self.concept_embs = nn.ParameterList([nn.Parameter(torch.rand(max_c + 1, d_model)) for max_c in c_list])
        self.concept_embs2 = nn.ParameterList([nn.Parameter(torch.rand(max_c + 1, d_model)) for max_c in c_list])
        self.q_emb = nn.Embedding(200000, 1, padding_idx=-1)
        self.centroid_emb = None
        self.A_matrix = None
        self.cluster_model = None
        self.c_list = c_list
        self.freedom = 0.1

    def forward(self, q_seq, concept_seq, domain, use_centroid=None, freedom=0.1):
        count = torch.sum(concept_seq, dim=-1, keepdim=True)
        count[count == 0] = 1
        concept_seq = concept_seq / count
        concept_embedding1 = torch.matmul(concept_seq, self.concept_embs[domain])
        concept_embedding2 = torch.matmul(concept_seq, self.concept_embs2[domain])
        lam = self.q_emb(q_seq%200000)
        concept_embedding = concept_embedding1 + lam * concept_embedding2
        return concept_embedding

import torch
from torch import nn
from torch.nn.init import xavier_uniform_
from torch.nn.init import constant_
from torch.nn.init import xavier_normal_
import math
import torch.nn.functional as F
from enum import IntEnum
import numpy as np
from sklearn.cluster import KMeans


class Dim(IntEnum):
    batch = 0
    seq = 1
    feature = 2


class AKT(nn.Module):
    def __init__(self, c_list, d_model=256, seq_len=200):
        super().__init__()
        """
        Input:
            d_model: dimension of attention block
            final_fc_dim: dimension of final fully connected net before prediction
            n_heads: number of heads in multi-headed attention
            d_ff : dimension for fully conntected net inside the basic block
        """

        self.concept_emb = Rash_ConceptEmbedding(c_list, d_model)
        self.model = Architecture(n_question=1, n_blocks=2, n_heads=4, dropout=0.1,
                                  d_model=d_model, d_feature=d_model / 4, d_ff=2048, kq_same=True)
        self.map1 = MappingLayer(2 * d_model, d_model)
        self.out = KnowledgeDecoder(d_model)

    @staticmethod
    def get_orthogonal_cr(concept_emb, response):
        """
        :param concept_emb: shape = [batch size, max_len, d_model]
        :param response: shape = [batch size, max_len]
        :return:
        """
        # 优化qr代码
        zero_tensor = torch.zeros_like(concept_emb)
        QR_False = torch.cat([concept_emb, zero_tensor], dim=-1)
        QR_True = torch.cat([zero_tensor, concept_emb], dim=-1)
        QR_Zero = torch.zeros_like(QR_True)
        board_cast_r = response.unsqueeze(-1)  # shape = [batch size, max_len, 1]
        board_cast_r = board_cast_r.expand(board_cast_r.shape[0], board_cast_r.shape[1],
                                           concept_emb.shape[2] * 2)  # shape = [batch size, max_len, 2 * d_model]
        encoder_input_qr_norm = torch.where(board_cast_r == 1, QR_True, QR_False)
        encoder_input_qr_norm = torch.where(board_cast_r == -1, QR_Zero, encoder_input_qr_norm)
        return encoder_input_qr_norm

    def forward(self, q, c, r, domain=None, use_centroid=None):
        q = q + 1
        concept_embedding = self.concept_emb(q, c, domain, use_centroid=use_centroid)
        cr_embedding = self.get_orthogonal_cr(concept_embedding, r)
        mapped_cr_embbeding = self.map1(cr_embedding)
        d_output = self.model(concept_embedding, mapped_cr_embbeding)  # 211x512
        output = self.out(d_output, concept_embedding)

        return output


class Architecture(nn.Module):
    def __init__(self, n_question, n_blocks, d_model, d_feature,
                 d_ff, n_heads, dropout, kq_same, model_type='akt'):
        super().__init__()
        """
            n_block : number of stacked blocks in the attention
            d_model : dimension of attention input/output
            d_feature : dimension of input in each of the multi-head attention part.
            n_head : number of heads. n_heads*d_feature = d_model
        """
        self.d_model = d_model
        self.model_type = model_type

        if model_type in {'akt'}:
            self.blocks_1 = nn.ModuleList([
                TransformerLayer(d_model=d_model, d_feature=d_model // n_heads,
                                 d_ff=d_ff, dropout=dropout, n_heads=n_heads, kq_same=kq_same)
                for _ in range(n_blocks)
            ])
            self.blocks_2 = nn.ModuleList([
                TransformerLayer(d_model=d_model, d_feature=d_model // n_heads,
                                 d_ff=d_ff, dropout=dropout, n_heads=n_heads, kq_same=kq_same)
                for _ in range(n_blocks * 2)
            ])

    def forward(self, q_embed_data, qa_embed_data):
        # target shape  bs, seqlen
        seqlen, batch_size = q_embed_data.size(1), q_embed_data.size(0)

        qa_pos_embed = qa_embed_data
        q_pos_embed = q_embed_data

        y = qa_pos_embed
        seqlen, batch_size = y.size(1), y.size(0)
        x = q_pos_embed

        # encoder
        for block in self.blocks_1:  # encode qas
            y = block(mask=1, query=y, key=y, values=y)
        flag_first = True
        for block in self.blocks_2:
            if flag_first:  # peek current question
                x = block(mask=1, query=x, key=x,
                          values=x, apply_pos=False)
                flag_first = False
            else:  # dont peek current response
                x = block(mask=0, query=x, key=x, values=y, apply_pos=True)
                flag_first = True
        return x


class TransformerLayer(nn.Module):
    def __init__(self, d_model, d_feature,
                 d_ff, n_heads, dropout, kq_same):
        super().__init__()
        """
            This is a Basic Block of Transformer paper. It containts one Multi-head attention object. Followed by layer norm and postion wise feedforward net and dropout layer.
        """
        kq_same = kq_same == 1
        # Multi-Head Attention Block
        self.masked_attn_head = MultiHeadAttention(
            d_model, d_feature, n_heads, dropout, kq_same=kq_same)

        # Two layer norm layer and two droput layer
        self.layer_norm1 = nn.LayerNorm(d_model)
        self.dropout1 = nn.Dropout(dropout)

        self.linear1 = nn.Linear(d_model, d_ff)
        self.activation = nn.ReLU()
        self.dropout = nn.Dropout(dropout)
        self.linear2 = nn.Linear(d_ff, d_model)

        self.layer_norm2 = nn.LayerNorm(d_model)
        self.dropout2 = nn.Dropout(dropout)

    def forward(self, mask, query, key, values, apply_pos=True):
        """
        Input:
            block : object of type BasicBlock(nn.Module). It contains masked_attn_head objects which is of type MultiHeadAttention(nn.Module).
            mask : 0 means, it can peek only past values. 1 means, block can peek only current and pas values
            query : Query. In transformer paper it is the input for both encoder and decoder
            key : Keys. In transformer paper it is the input for both encoder and decoder
            Values. In transformer paper it is the input for encoder and  encoded output for decoder (in masked attention part)

        Output:
            query: Input gets changed over the layer and returned.

        """

        seqlen, batch_size = query.size(1), query.size(0)
        nopeek_mask = np.triu(
            np.ones((1, 1, seqlen, seqlen)), k=mask).astype('uint8')
        src_mask = (torch.from_numpy(nopeek_mask) == 0).cuda()
        if mask == 0:  # If 0, zero-padding is needed.
            # Calls block.masked_attn_head.forward() method
            query2 = self.masked_attn_head(
                query, key, values, mask=src_mask, zero_pad=True)
        else:
            # Calls block.masked_attn_head.forward() method
            query2 = self.masked_attn_head(
                query, key, values, mask=src_mask, zero_pad=False)

        query = query + self.dropout1((query2))
        query = self.layer_norm1(query)
        if apply_pos:
            query2 = self.linear2(self.dropout(
                self.activation(self.linear1(query))))
            query = query + self.dropout2((query2))
            query = self.layer_norm2(query)
        return query


class MultiHeadAttention(nn.Module):
    def __init__(self, d_model, d_feature, n_heads, dropout, kq_same, bias=True):
        super().__init__()
        """
        It has projection layer for getting keys, queries and values. Followed by attention and a connected layer.
        """
        self.d_model = d_model
        self.d_k = d_feature
        self.h = n_heads
        self.kq_same = kq_same

        self.v_linear = nn.Linear(d_model, d_model, bias=bias)
        self.k_linear = nn.Linear(d_model, d_model, bias=bias)
        if kq_same is False:
            self.q_linear = nn.Linear(d_model, d_model, bias=bias)
        self.dropout = nn.Dropout(dropout)
        self.proj_bias = bias
        self.out_proj = nn.Linear(d_model, d_model, bias=bias)
        self.gammas = nn.Parameter(torch.zeros(n_heads, 1, 1))
        torch.nn.init.xavier_uniform_(self.gammas)

        self._reset_parameters()

    def _reset_parameters(self):
        xavier_uniform_(self.k_linear.weight)
        xavier_uniform_(self.v_linear.weight)
        if self.kq_same is False:
            xavier_uniform_(self.q_linear.weight)

        if self.proj_bias:
            constant_(self.k_linear.bias, 0.)
            constant_(self.v_linear.bias, 0.)
            if self.kq_same is False:
                constant_(self.q_linear.bias, 0.)
            constant_(self.out_proj.bias, 0.)

    def forward(self, q, k, v, mask, zero_pad):

        bs = q.size(0)

        # perform linear operation and split into h heads

        k = self.k_linear(k).view(bs, -1, self.h, self.d_k)
        if self.kq_same is False:
            q = self.q_linear(q).view(bs, -1, self.h, self.d_k)
        else:
            q = self.k_linear(q).view(bs, -1, self.h, self.d_k)
        v = self.v_linear(v).view(bs, -1, self.h, self.d_k)

        # transpose to get dimensions bs * h * sl * d_model

        k = k.transpose(1, 2)
        q = q.transpose(1, 2)
        v = v.transpose(1, 2)
        # calculate attention using function we will define next
        gammas = self.gammas
        scores = attention(q, k, v, self.d_k,
                           mask, self.dropout, zero_pad, gammas)

        # concatenate heads and put through final linear layer
        concat = scores.transpose(1, 2).contiguous() \
            .view(bs, -1, self.d_model)

        output = self.out_proj(concat)

        return output


def attention(q, k, v, d_k, mask, dropout, zero_pad, gamma=None):
    """
    This is called by Multi-head atention object to find the values.
    """
    scores = torch.matmul(q, k.transpose(-2, -1)) / \
             math.sqrt(d_k)  # BS, 8, seqlen, seqlen
    bs, head, seqlen = scores.size(0), scores.size(1), scores.size(2)

    x1 = torch.arange(seqlen).expand(seqlen, -1).cuda()
    x2 = x1.transpose(0, 1).contiguous()

    with torch.no_grad():
        scores_ = scores.masked_fill(mask == 0, -1e32)
        scores_ = F.softmax(scores_, dim=-1)  # BS,8,seqlen,seqlen
        scores_ = scores_ * mask.float().cuda()
        distcum_scores = torch.cumsum(scores_, dim=-1)  # bs, 8, sl, sl
        disttotal_scores = torch.sum(
            scores_, dim=-1, keepdim=True)  # bs, 8, sl, 1
        position_effect = torch.abs(
            x1 - x2)[None, None, :, :].type(torch.FloatTensor).cuda()  # 1, 1, seqlen, seqlen
        # bs, 8, sl, sl positive distance
        dist_scores = torch.clamp(
            (disttotal_scores - distcum_scores) * position_effect, min=0.)
        dist_scores = dist_scores.sqrt().detach()
    m = nn.Softplus()
    gamma = -1. * m(gamma).unsqueeze(0)  # 1,8,1,1
    # Now after do exp(gamma*distance) and then clamp to 1e-5 to 1e5
    total_effect = torch.clamp(torch.clamp(
        (dist_scores * gamma).exp(), min=1e-5), max=1e5)
    scores = scores * total_effect

    scores = scores.masked_fill(mask == 0, -1e32)
    scores = F.softmax(scores, dim=-1)

    if zero_pad:
        pad_zero = torch.zeros(bs, head, 1, seqlen).cuda()
        scores = torch.cat([pad_zero, scores[:, :, 1:, :]], dim=2)
    scores = dropout(scores)
    output = torch.matmul(scores, v)
    return output


class LearnablePositionalEmbedding(nn.Module):
    def __init__(self, d_model, max_len=512):
        super().__init__()
        # Compute the positional encodings once in log space.
        pe = 0.1 * torch.randn(max_len, d_model)
        pe = pe.unsqueeze(0)
        self.weight = nn.Parameter(pe, requires_grad=True)

    def forward(self, x):
        return self.weight[:, :x.size(Dim.seq), :]  # ( 1,seq,  Feature)


class CosinePositionalEmbedding(nn.Module):
    def __init__(self, d_model, max_len=512):
        super().__init__()
        # Compute the positional encodings once in log space.
        pe = 0.1 * torch.randn(max_len, d_model)
        position = torch.arange(0, max_len).unsqueeze(1).float()
        div_term = torch.exp(torch.arange(0, d_model, 2).float() *
                             -(math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        self.weight = nn.Parameter(pe, requires_grad=False)

    def forward(self, x):
        return self.weight[:, :x.size(Dim.seq), :]  # ( 1,seq,  Feature)
