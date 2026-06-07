import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
from sklearn.cluster import KMeans
from model.DGKT import *
from model.DKT import raw_ConceptEmbedding


class SimpleKT(nn.Module):
    def __init__(self, c_list, d_model=256, seq_len=200):
        super().__init__()
        self.concept_emb = raw_ConceptEmbedding(c_list, d_model)
        self.r_emb = nn.Embedding(3, d_model, padding_idx=-1)

        self.map1 = MappingLayer(2 * d_model, d_model)
        self.attention = MultiHeadAttention(mask=future_mask(seq_len))

        self.pos_emb1 = CosinePositionalEmbedding(d_model)
        self.pos_emb2 = CosinePositionalEmbedding(d_model)
        self.decoder = nn.Sequential(
            nn.Linear(2 * d_model, d_model),
            nn.ReLU(),
            nn.Linear(d_model, d_model),
            nn.ReLU(),
            nn.Linear(d_model, 1)
        )

        self.d_model = d_model
        self.c_list = c_list

    def forward(self, q, c, r, domain=None, use_centroid=None):
        concept_embedding = self.concept_emb(c, domain, use_centroid=use_centroid)
        cr_embedding = self.r_emb(r.to(torch.long) + 1)
        c_embedding_pos = self.pos_emb1(concept_embedding)
        cr_embedding_pos = self.pos_emb2(cr_embedding)
        knowledge_state = self.attention(c_embedding_pos, c_embedding_pos, cr_embedding_pos)
        prediction = self.decoder(torch.concatenate([knowledge_state, concept_embedding], dim=-1))
        return prediction


class DG_SimpleKT(nn.Module):
    def __init__(self, c_list, d_model=256, seq_len=200):
        super().__init__()
        self.concept_emb = ConceptEmbedding(c_list, d_model)
        self.r_emb = nn.Embedding(3, d_model, padding_idx=-1)

        self.map1 = MappingLayer(2 * d_model, d_model)
        self.attention = MultiHeadAttention(mask=future_mask(seq_len))

        self.pos_emb1 = CosinePositionalEmbedding(d_model)
        self.pos_emb2 = CosinePositionalEmbedding(d_model)
        self.seqin = SeqIN(d_model)
        self.decoder = nn.Sequential(
            nn.Linear(2 * d_model, d_model),
            nn.ReLU(),
            nn.Linear(d_model, d_model),
            nn.ReLU(),
            nn.Linear(d_model, 1)
        )

        self.d_model = d_model
        self.c_list = c_list

    def forward(self, q, c, r, domain=None, use_centroid=None):
        concept_embedding = self.concept_emb(c, domain, use_centroid=use_centroid)
        cr_embedding = self.r_emb(r.to(torch.long) + 1)
        c_embedding_pos = self.pos_emb1(concept_embedding)
        cr_embedding_pos = self.pos_emb2(cr_embedding)
        knowledge_state = self.attention(c_embedding_pos, c_embedding_pos, cr_embedding_pos)
        # knowledge_state = self.seqin(knowledge_state)
        prediction = self.decoder(torch.concatenate([knowledge_state, concept_embedding], dim=-1))
        return prediction
