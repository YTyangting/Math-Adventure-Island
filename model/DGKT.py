import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
from sklearn.cluster import KMeans


def future_mask(seq_length):
    mask = np.triu(np.ones((1, seq_length, seq_length)), k=0).astype('bool')
    return torch.from_numpy(mask).cuda()


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
        return x + self.weight[:, :x.shape[1], :]  # ( 1,seq,  Feature)


class MultiHeadAttention(nn.Module):
    def __init__(self, embed_dim=256, num_heads=4, dropout=0.1, mask=None):
        super(MultiHeadAttention, self).__init__()

        self.d_model = embed_dim
        self.d_k = embed_dim // num_heads
        self.h = num_heads

        self.q_linear = nn.Linear(embed_dim, embed_dim)
        self.v_linear = nn.Linear(embed_dim, embed_dim)
        self.k_linear = nn.Linear(embed_dim, embed_dim)

        self.dropout = nn.Dropout(dropout)
        self.out = nn.Linear(embed_dim, embed_dim)
        self.mask = mask

    def forward(self, q, k, v):
        bs = q.size(0)
        k = self.k_linear(k).view(bs, -1, self.h, self.d_k)
        q = self.v_linear(q).view(bs, -1, self.h, self.d_k)
        v = self.q_linear(v).view(bs, -1, self.h, self.d_k)

        k = k.transpose(1, 2)
        q = q.transpose(1, 2)
        v = v.transpose(1, 2)

        scores = self.cal_attention_score(q, k, self.d_k, self.mask)
        scores = self.dropout(scores)
        output = torch.matmul(scores, v)
        concat = output.transpose(1, 2).contiguous().view(bs, -1, self.d_model)
        output = self.out(concat)
        return output

    def get_attention_score(self, q, k, v):
        bs = q.size(0)
        k = self.k_linear(k).view(bs, -1, self.h, self.d_k)
        q = self.v_linear(q).view(bs, -1, self.h, self.d_k)

        k = k.transpose(1, 2)
        q = q.transpose(1, 2)

        scores = self.cal_attention_score(q, k, self.d_k, self.mask)

        return scores

    def cal_attention_score(self, q, k, d_k, mask=None):
        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(d_k)
        if mask is not None:
            mask = mask.unsqueeze(1)
            scores = scores.masked_fill(mask, -1e32)
        scores = F.softmax(scores, dim=-1)
        scores = scores.masked_fill(mask, 0)
        return scores


class QC_Attention(nn.Module):
    def __init__(self, embed_dim=256, num_heads=4, dropout=0.1):
        super(QC_Attention, self).__init__()

        self.d_model = embed_dim
        self.d_k = embed_dim // num_heads
        self.h = num_heads

        self.q_linear = nn.Linear(embed_dim, embed_dim)
        self.v_linear = nn.Linear(embed_dim, embed_dim)
        self.k_linear = nn.Linear(embed_dim, embed_dim)

        self.qc_scalar = nn.Parameter(torch.tensor(0.0))

        self.dropout = nn.Dropout(dropout)
        self.out = nn.Linear(embed_dim, embed_dim)

    def forward(self, q, k, v, q_seq, c_seq):
        bs = q.size(0)
        k = self.k_linear(k).view(bs, -1, self.h, self.d_k)
        q = self.v_linear(q).view(bs, -1, self.h, self.d_k)
        v = self.q_linear(v).view(bs, -1, self.h, self.d_k)

        k = k.transpose(1, 2)
        q = q.transpose(1, 2)
        v = v.transpose(1, 2)

        mask = self.qc_mask(q_seq, c_seq)

        scores = self.cal_attention_score(q, k, self.d_k, mask)
        scores = self.dropout(scores)
        output = torch.matmul(scores, v)
        concat = output.transpose(1, 2).contiguous().view(bs, -1, self.d_model)
        output = self.out(concat)
        return output

    def qc_mask(self, q, c):
        with torch.no_grad():
            c = c.to(torch.int)
            seq_len = q.shape[1]
            k = c.shape[-1]
            batchsize, seqlen = q.shape
            q_expanded = q.unsqueeze(2).expand(batchsize, seqlen, seqlen)
            maskq = (q_expanded == q_expanded.transpose(1, 2)).to(torch.int)

            # Step 2: Generate mask based on c
            c_expanded1 = c.unsqueeze(2).expand(batchsize, seqlen, seqlen, k)
            c_expanded2 = c.unsqueeze(1).expand(batchsize, seqlen, seqlen, k)

            maskc = ((c_expanded1 & c_expanded2).sum(dim=-1) > 0).int()

            mask_tri = (1 - torch.from_numpy(np.triu(np.ones((1, seq_len, seq_len)), k=0))).to(q.device)
            mask = ((maskc + maskq + torch.ones_like(maskq)) * mask_tri).to(torch.int)  # 0-不可见 1-无关试题 2-知识点相关试题 3-相同试题
        return mask

    def cal_attention_score(self, q, k, d_k, mask):
        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(d_k)
        if mask is not None:

            mask = mask.unsqueeze(1)
            scores = scores.masked_fill(mask == 0, -1e32)
        scores = F.softmax(scores, dim=-1)
        mask_adjustments = torch.tensor([0.0, 0.5, 1.0, 2.0], device=mask.device)
        adjusted_score = scores * mask_adjustments[mask.long()]

        score_sums = scores.sum(dim=-1, keepdim=True)
        score_sums = torch.where(score_sums == 0, torch.ones_like(score_sums), score_sums)

        adjusted_score = adjusted_score / score_sums

        return adjusted_score


class MappingLayer(nn.Module):
    def __init__(self, in_dim, out_dim, dropout=0.2):
        super().__init__()
        self.linear = nn.Linear(in_dim, out_dim)
        self.layernorm = nn.LayerNorm(out_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        x = self.linear(x)
        x = self.layernorm(x)
        x = self.dropout(x)
        return x


class KnowledgeDecoder(nn.Module):
    def __init__(self, d_model):
        super().__init__()
        self.linear = nn.Linear(2 * d_model, 1)
        self.linear2 = self.f = nn.Sequential(
            nn.Linear(2 * d_model, d_model),
            nn.LayerNorm(d_model),
            nn.ReLU(),
            nn.Linear(d_model, 1)
        )

    def forward(self, knowledge_state, concept_embedding):
        x = torch.cat([knowledge_state, concept_embedding], dim=-1)
        out = self.linear2(x)
        return out


class KnowledgeStateMLP(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.f = nn.Sequential(
            nn.LayerNorm(dim),
            nn.Linear(dim, dim),
            nn.ReLU(),
            nn.Linear(dim, dim),
            nn.ReLU(),
            nn.LayerNorm(dim)
        )

    def forward(self, x):
        return self.f(x)


class AttentionEmbedding(nn.Embedding):
    def __init__(self, num_embeddings, embedding_dim, padding_idx=0, seq_len=50):
        super().__init__(num_embeddings, embedding_dim, padding_idx=padding_idx)
        mask = np.triu(np.ones((1, seq_len, seq_len)), k=1).astype('bool')
        self.attention = MultiHeadAttention(embedding_dim, mask=torch.from_numpy(mask).cuda())

    def forward(self, x):
        embedding = super().forward(x)
        embedding = self.attention(embedding, embedding, embedding)
        return embedding


class ConceptEmbedding(nn.Module):
    def __init__(self, c_list, d_model=256):
        super().__init__()
        self.concept_embs = nn.ParameterList([nn.Parameter(torch.rand(max_c + 1, d_model)) for max_c in c_list])
        self.centroid_emb = None
        self.A_matrix = None
        self.cluster_model = None
        self.c_list = c_list
        self.freedom = 0.1

    def compute_closest_centroid(self, concept_embedding_free, centroid_emb):
        # 创建副本以防止修改原始张量
        concept_embedding = concept_embedding_free.clone()
        centroid_embedding = centroid_emb.clone()

        flattened_features = concept_embedding.view(-1, 256)
        # 计算特征向量与聚类中心之间的欧氏距离
        distances = torch.cdist(flattened_features, centroid_embedding)
        # 找到每个特征向量对应的最近聚类中心的索引
        closest_cluster_indices = torch.argmin(distances, dim=1)
        # 将索引转换为对应的聚类中心向量
        closest_cluster_embedding = centroid_embedding[closest_cluster_indices].view(concept_embedding.size())

        return closest_cluster_embedding

    def forward(self, concept_seq, domain, use_centroid=None, freedom=0.1):
        concept_embedding = None
        count = torch.sum(concept_seq, dim=-1, keepdim=True)
        count[count == 0] = 1
        concept_seq = concept_seq / count
        if use_centroid is None:
            concept_embedding = torch.matmul(concept_seq, self.concept_embs[domain])
        elif use_centroid == "source":
            concept_embedding = torch.matmul(torch.matmul(concept_seq, self.A_matrix[domain]), self.centroid_emb)
        elif use_centroid == "target":
            assert domain == -1 or len(self.concept_embs) - 1
            concept_embedding_free = torch.matmul(concept_seq, self.concept_embs[domain])
            concept_embedding_centroid = self.compute_closest_centroid(concept_embedding_free, self.centroid_emb)
            concept_embedding = concept_embedding_free * self.freedom + concept_embedding_centroid * (1 - self.freedom)
        return concept_embedding

    def cluster_emb(self, k=5):
        embedding = None
        for domain_idx, matrix in enumerate(self.concept_embs[:-1]):
            if domain_idx == 0:
                embedding = self.concept_embs[domain_idx].cpu().detach().numpy()
            else:
                embedding = np.concatenate(
                    [embedding, self.concept_embs[domain_idx].cpu().detach().numpy()])

        self.cluster_model = KMeans(n_clusters=k).fit(embedding)
        embedding_weight = torch.tensor(self.cluster_model.cluster_centers_)
        self.centroid_emb = nn.Parameter(embedding_weight).cuda()
        self.A_matrix = [torch.zeros((max_c + 1, k)).cuda() for max_c in self.c_list[:-1]]

        labels = self.cluster_model.labels_
        begin_idx = 0
        for domain_idx, max_c in enumerate(self.c_list[:-1]):
            for i, centroid in enumerate(labels[begin_idx: begin_idx + max_c + 1]):
                self.A_matrix[domain_idx][i, centroid] = 1
            begin_idx += max_c + 1

    def init_target_embedding(self):
        k, d = self.centroid_emb.size()
        indices = torch.randint(k, (self.c_list[-1] + 1,))
        # 根据索引从第一个张量中选择向量
        self.concept_embs[-1] = self.centroid_emb[indices]


class DGKT(nn.Module):
    def __init__(self, c_list, d_model=256, seq_len=200):
        super().__init__()
        self.concept_emb = ConceptEmbedding(c_list, d_model)

        self.map1 = MappingLayer(2 * d_model, d_model)
        self.attention = MultiHeadAttention(mask=future_mask(seq_len))
        self.attention2 = MultiHeadAttention(mask=future_mask(seq_len))
        # self.attn_mlp = KnowledgeStateMLP(d_model)
        self.pos_emb1 = CosinePositionalEmbedding(d_model)
        self.pos_emb2 = CosinePositionalEmbedding(d_model)
        self.decoder = KnowledgeDecoder(d_model)
        self.seqin = SeqIN(d_model)

        self.cluster_model = None
        self.centorid_emb = None
        self.d_model = d_model
        self.c_list = c_list

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

        c_embedding_pos = self.pos_emb1(concept_embedding)
        cr_embedding_pos = self.pos_emb2(mapped_cr_embbeding)

        knowledge_state = self.attention(c_embedding_pos, c_embedding_pos, cr_embedding_pos)
        # knowledge_state = self.attention2(c_embedding_pos, c_embedding_pos, attn_out)
        knowledge_state = self.seqin(knowledge_state)

        prediction = self.decoder(knowledge_state, concept_embedding)
        return prediction


class DGKT_new(nn.Module):
    def __init__(self, c_list, d_model=256, seq_len=200):
        super().__init__()
        self.concept_emb = ConceptEmbedding(c_list, d_model)
        self.r_emb = nn.Embedding(3, d_model)
        self.map1 = MappingLayer(2 * d_model, d_model)
        self.attention = QC_Attention()
        self.attention2 = QC_Attention()
        self.q_emb = nn.Embedding(seq_len + 1, d_model)
        self.pos_emb1 = CosinePositionalEmbedding(d_model)
        self.pos_emb2 = CosinePositionalEmbedding(d_model)
        self.decoder = KnowledgeDecoder(d_model)
        self.seqin = SeqIN(d_model)
        self.mlp = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.ReLU(),
            nn.Linear(d_model, d_model),
            nn.ReLU()
        )
        self.concept_map = nn.Linear(2 * d_model, d_model)
        self.cluster_model = None
        self.centorid_emb = None
        self.d_model = d_model
        self.c_list = c_list

    def forward(self, q, c, r, domain=None, use_centroid=None):
        concept_embedding = self.concept_emb(c, domain, use_centroid=use_centroid)
        cr_embedding = self.get_orthogonal_cr(concept_embedding, r)
        mapped_cr_embbeding = self.map1(cr_embedding)

        c_embedding_pos = self.pos_emb1(concept_embedding)
        cr_embedding_pos = self.pos_emb2(mapped_cr_embbeding)

        attn_out = self.attention(c_embedding_pos, c_embedding_pos, cr_embedding_pos, q, c)
        knowledge_state = self.attention2(c_embedding_pos, c_embedding_pos, attn_out, q, c)
        knowledge_state = self.seqin(knowledge_state)

        prediction = self.decoder(knowledge_state, concept_embedding)
        return prediction


class SeqIN(nn.Module):
    def __init__(self, d_model, eps=1e-5):
        super(SeqIN, self).__init__()
        self.eps = eps
        self.gamma = torch.nn.Parameter(torch.ones(d_model))
        self.beta = torch.nn.Parameter(torch.zeros(d_model))

    def forward(self, x):
        batch_size, seq_length, d = x.shape
        # 累积和和累积平方和
        cumsum = torch.cumsum(x, dim=1)
        cumsum_sq = torch.cumsum(x ** 2, dim=1)
        # 构造时间步
        timestep = torch.arange(1, seq_length + 1, device=x.device).view(1, -1, 1)
        # 计算均值和方差
        cummean = cumsum / timestep
        cumvar = (cumsum_sq / timestep) - cummean ** 2
        # 计算标准差
        cumstd = torch.sqrt(cumvar + self.eps)
        # 归一化
        normalized_output = (x - cummean) / cumstd
        out = self.gamma * normalized_output + self.beta
        return out


class DGKT_q_attention(nn.Module):
    def __init__(self, c_list, d_model=256, seq_len=200):
        super().__init__()
        self.concept_emb = ConceptEmbedding(c_list, d_model)
        self.r_emb = nn.Embedding(3, d_model)
        self.map1 = MappingLayer(2 * d_model, d_model)
        self.attention = QC_Attention()
        self.attention2 = QC_Attention()
        self.pos_emb1 = CosinePositionalEmbedding(d_model)
        self.pos_emb2 = CosinePositionalEmbedding(d_model)
        self.decoder = KnowledgeDecoder(d_model)
        self.seqin = SeqIN(d_model)
        self.mlp = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.ReLU(),
            nn.Linear(d_model, d_model),
            nn.ReLU()
        )
        self.cluster_model = None
        self.centorid_emb = None
        self.d_model = d_model
        self.c_list = c_list
        self.seq_len = seq_len

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

        c_embedding_pos = self.pos_emb1(concept_embedding)
        cr_embedding_pos = self.pos_emb2(mapped_cr_embbeding)

        knowledge_state = self.attention(c_embedding_pos, c_embedding_pos, cr_embedding_pos, q, c)
        # knowledge_state = self.attention2(c_embedding_pos, c_embedding_pos, attn_out, q, c)
        # knowledge_state = self.seqin(knowledge_state)

        prediction = self.decoder(knowledge_state, concept_embedding)
        return prediction

if __name__ == "__main__":
    a = torch.ones((32, 200, 256))
    seqin = SeqIN()
    print(seqin(a))
