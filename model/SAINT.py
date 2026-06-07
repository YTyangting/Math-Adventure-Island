from model.DGKT import *
from model.DKT import raw_ConceptEmbedding
from model.DGKT import ConceptEmbedding, SeqIN
from model.AKT import Rash_ConceptEmbedding


class SaintEncoder(nn.Module):
    def __init__(self, seq_len=200, d_model=256):
        super().__init__()
        self.attention = MultiHeadAttention(mask=future_mask(seq_len))
        self.feed_forward = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.ReLU(),
            nn.Linear(d_model, d_model)
        )
        self.LN = nn.LayerNorm(d_model)

    def forward(self, x):
        ln_X = self.LN(x)
        M = self.attention(ln_X, ln_X, ln_X) + x
        out = self.feed_forward(self.LN(M)) + M
        return out


class SaintDecoder(nn.Module):
    def __init__(self, seq_len=200, d_model=256):
        super().__init__()
        self.attention = MultiHeadAttention(mask=future_mask(seq_len))
        self.feed_forward = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Linear(d_model, d_model),
            nn.ReLU(),
            nn.Linear(d_model, d_model)
        )
        self.LN = nn.LayerNorm(d_model)
        self.LN2 = nn.LayerNorm(d_model)

    def forward(self, r, o):
        ln_r = self.LN(r)
        ln_o = self.LN2(o)
        M1 = self.attention(ln_r, ln_r, ln_r) + r
        M2 = self.attention(ln_o, ln_o, M1) + o
        L = self.feed_forward(M2) + M2
        return L


class SAINT(nn.Module):
    def __init__(self, c_list, d_model=256, seq_len=200):
        super().__init__()
        self.encoder = SaintEncoder(seq_len, d_model)
        self.decoder = SaintDecoder(seq_len, d_model)
        self.knowledge_decoder = KnowledgeDecoder(d_model)
        self.concept_emb = Rash_ConceptEmbedding(c_list, d_model)
        self.response_emb = nn.Embedding(3, d_model)

    def forward(self, q, c, r, domain=None, use_centroid=None):
        response = r.clone() + 1
        q = q + 1
        concept_embedding = self.concept_emb(q, c, domain, use_centroid=use_centroid)
        qr = self.response_emb(response.to(torch.long))
        o = self.encoder(concept_embedding)
        out = self.decoder(qr, o)
        y = self.knowledge_decoder(out, concept_embedding)
        return y


class DG_SAINT(nn.Module):
    def __init__(self, c_list, d_model=256, seq_len=200):
        super().__init__()
        self.encoder = SaintEncoder(seq_len, d_model)
        self.decoder = SaintDecoder(seq_len, d_model)
        self.knowledge_decoder = KnowledgeDecoder(d_model)
        self.concept_emb = ConceptEmbedding(c_list, d_model)
        self.response_emb = nn.Embedding(3, d_model)
        self.seqin = SeqIN(d_model)

    def forward(self, q, c, r, domain=None, use_centroid=None):
        response = r.clone() + 1
        concept_embedding = self.concept_emb(c, domain, use_centroid=use_centroid)
        qr = self.response_emb(response.to(torch.long))
        o = self.encoder(concept_embedding)
        o = self.seqin(o)
        out = self.decoder(qr, o)
        out = self.seqin(out)
        y = self.knowledge_decoder(out, concept_embedding)
        return y