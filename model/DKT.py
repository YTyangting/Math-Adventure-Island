import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
from sklearn.cluster import KMeans
from model.DGKT import ConceptEmbedding, KnowledgeDecoder, MappingLayer, MultiHeadAttention, future_mask, SeqIN
from model.AKT import Rash_ConceptEmbedding


def same_with_previous(x):
    batch_size, seq_len = x.shape
    # 初始化输出张量
    output = torch.zeros(batch_size, seq_len, device=x.device, dtype=torch.long)
    # 当前值与前一个值进行比较
    output[:, 1:] = (x[:, 1:] == x[:, :-1])
    return output


class raw_ConceptEmbedding(nn.Module):
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


class Rasch_ConceptEmbedding(nn.Module):
    def __init__(self, c_list, d_model=256):
        super().__init__()
        self.concept_embs1 = nn.ParameterList([nn.Parameter(torch.rand(max_c + 1, d_model)) for max_c in c_list])
        self.concept_embs2 = nn.ParameterList([nn.Parameter(torch.rand(max_c + 1, d_model)) for max_c in c_list])
        self.q_embs = nn.ModuleList([nn.Embedding(20000000, 1, padding_idx=-1) for i in c_list])
        self.centroid_emb = None
        self.A_matrix = None
        self.cluster_model = None
        self.c_list = c_list
        self.freedom = 0.1

    def forward(self, q_seq, concept_seq, domain, use_centroid=None, freedom=0.1):
        count = torch.sum(concept_seq, dim=-1, keepdim=True)
        count[count == 0] = 1
        concept_seq = concept_seq / count
        concept_embedding1 = torch.matmul(concept_seq, self.concept_embs1[domain])
        concept_embedding2 = torch.matmul(concept_seq, self.concept_embs2[domain])
        a = self.q_embs[domain](q_seq)
        concept_embedding = concept_embedding1 + a * concept_embedding2

        return concept_embedding


class DKT(nn.Module):
    def __init__(self, c_list, d_model=256, seq_len=200, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.concept_emb = Rash_ConceptEmbedding(c_list, d_model)
        self.rnn = nn.RNN(d_model, d_model, 1, batch_first=True)
        self.fc = nn.ModuleList([nn.Linear(d_model, n + 1) for n in c_list])
        self.map1 = MappingLayer(2 * d_model, d_model)
        self.out = KnowledgeDecoder(d_model)

    def forward(self, q, c, r, domain=None, use_centroid=None):
        concept_embedding = self.concept_emb(q+1, c, domain, use_centroid=use_centroid)
        cr_embedding = self.get_orthogonal_cr(concept_embedding, r)
        mapped_cr_embbeding = self.map1(cr_embedding)
        x, _ = self.rnn(mapped_cr_embbeding)
        x = torch.roll(x, 1, 1)
        y = self.out(x, concept_embedding)
        return y

    def get_knowledge_state(self, q, c, r, domain=None, use_centroid=None):
        concept_embedding = self.concept_emb(q+1, c, domain, use_centroid=use_centroid)
        cr_embedding = self.get_orthogonal_cr(concept_embedding, r)
        mapped_cr_embbeding = self.map1(cr_embedding)
        x, _ = self.rnn(mapped_cr_embbeding)
        return x

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


class DG_DKT(nn.Module):
    def __init__(self, c_list, d_model=256, seq_len=200):
        super().__init__()
        self.concept_emb = ConceptEmbedding(c_list, d_model)

        self.map1 = MappingLayer(2 * d_model, d_model)
        self.rnn = nn.RNN(d_model, d_model, 1, batch_first=True)
        self.out = KnowledgeDecoder(d_model)

        self.cluster_model = None
        self.centorid_emb = None
        self.d_model = d_model
        self.c_list = c_list
        self.seqin = SeqIN(d_model)
        self.batch_norm = nn.BatchNorm1d(d_model)

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
        concept_embedding = self.concept_emb(c, domain, use_centroid=use_centroid)
        cr_embedding = self.get_orthogonal_cr(concept_embedding, r)
        mapped_cr_embbeding = self.map1(cr_embedding)
        x, _ = self.rnn(mapped_cr_embbeding)
        # x = self.seqin(x)

        bs, seqlen, d = x.shape
        x_reshaped = x.reshape(-1, d)  # 形状变为: (batchsize*seqlen, d)
        x_normalized = self.batch_norm(x_reshaped)
        # 变回原来的形状
        x = x_normalized.reshape(bs, seqlen, d)

        x = torch.roll(x, 1, 1)
        y = self.out(x, concept_embedding)
        return y


class DG_DKT_q_same(nn.Module):
    def __init__(self, c_list, d_model=256, seq_len=200):
        super().__init__()
        self.concept_emb = ConceptEmbedding(c_list, d_model)

        self.map1 = MappingLayer(2 * d_model, d_model)
        self.rnn = nn.RNN(d_model * 2, d_model, 1, batch_first=True)
        self.out = KnowledgeDecoder(d_model)

        self.cluster_model = None
        self.centorid_emb = None
        self.d_model = d_model
        self.c_list = c_list
        self.seqin = SeqIN(d_model)
        self.same_emb = nn.Embedding(2, d_model)

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
        q_same = same_with_previous(q)
        q_same_emb = self.same_emb(q_same)
        concept_embedding = self.concept_emb(c, domain, use_centroid=use_centroid)
        cr_embedding = self.get_orthogonal_cr(concept_embedding, r)
        mapped_cr_embbeding = self.map1(cr_embedding)
        input_feture = torch.cat([mapped_cr_embbeding, q_same_emb], dim=-1)
        x, _ = self.rnn(input_feture)
        x = self.seqin(x)
        x = torch.roll(x, 1, 1)
        y = self.out(x, concept_embedding)
        return y

class DG_LN_DKT(nn.Module):
    def __init__(self, c_list, d_model=256, seq_len=200):
        super().__init__()
        self.concept_emb = ConceptEmbedding(c_list, d_model)

        self.map1 = MappingLayer(2 * d_model, d_model)
        self.rnn = nn.RNN(d_model, d_model, 1, batch_first=True)
        self.out = KnowledgeDecoder(d_model)

        self.cluster_model = None
        self.centorid_emb = None
        self.d_model = d_model
        self.c_list = c_list
        self.ln = nn.LayerNorm(d_model)


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
        concept_embedding = self.concept_emb(c, domain, use_centroid=use_centroid)
        cr_embedding = self.get_orthogonal_cr(concept_embedding, r)
        mapped_cr_embbeding = self.map1(cr_embedding)
        x, _ = self.rnn(mapped_cr_embbeding)

        x = torch.roll(x, 1, 1)
        x = self.ln(x)
        y = self.out(x, concept_embedding)
        return y


class DG_BN_DKT(nn.Module):
    def __init__(self, c_list, d_model=256, seq_len=200):
        super().__init__()
        self.concept_emb = ConceptEmbedding(c_list, d_model)

        self.map1 = MappingLayer(2 * d_model, d_model)
        self.rnn = nn.RNN(d_model, d_model, 1, batch_first=True)
        self.out = KnowledgeDecoder(d_model)

        self.cluster_model = None
        self.centorid_emb = None
        self.d_model = d_model
        self.c_list = c_list
        self.seqin = SeqIN(d_model)
        self.batch_norm = nn.BatchNorm1d(d_model)

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
        concept_embedding = self.concept_emb(c, domain, use_centroid=use_centroid)
        cr_embedding = self.get_orthogonal_cr(concept_embedding, r)
        mapped_cr_embbeding = self.map1(cr_embedding)
        x, _ = self.rnn(mapped_cr_embbeding)

        bs, seqlen, d = x.shape
        x_reshaped = x.reshape(-1, d)  # 形状变为: (batchsize*seqlen, d)
        x_normalized = self.batch_norm(x_reshaped)
        # 变回原来的形状
        x = x_normalized.reshape(bs, seqlen, d)

        x = torch.roll(x, 1, 1)
        y = self.out(x, concept_embedding)
        return y

