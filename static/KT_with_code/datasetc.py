from torch.utils.data import Dataset, DataLoader
import configc as config
import numpy as np

from tqdm import tqdm

class DKTDataset(Dataset):
    def __init__(self, group, max_seq, min_seq, overlap_seq):
        self.samples = group
        self.max_seq = max_seq
        self.min_seq = min_seq
        self.overlap_seq = overlap_seq
        self.data = []

        for uid,exercise, concept0,concept1,concept2, correctness in tqdm(self.samples, total=len(self.samples), desc="Loading Dataset"):
            content_len = len(exercise)
            if content_len < self.min_seq:
                continue

            if content_len > self.max_seq:
                initial = content_len % self.max_seq
                if initial >= self.min_seq:
                    self.data.extend([(
                                        np.append([config.START], uid[:initial]),
                                        np.append([config.START], exercise[:initial]),
                                       np.append([config.START], concept0[:initial]),
                                        np.append([config.START], concept1[:initial]),
                                        np.append([config.START], concept2[:initial]),
                                       np.append([config.START], correctness[:initial]))])
                for seq in range(content_len // self.max_seq):
                    start = initial + seq * self.max_seq
                    end = initial + (seq + 1) * self.max_seq
                    self.data.extend([(
                                       np.append([config.START], uid[start: end]),
                                       np.append([config.START], exercise[start: end]),
                                       np.append([config.START], concept0[start: end]),
                                       np.append([config.START], concept1[start: end]),
                                       np.append([config.START], concept2[start: end]),
                                       np.append([config.START], correctness[start: end]))])
            else:
                self.data.extend([(
                                    np.append([config.START], uid),
                                    np.append([config.START], exercise),
                                   np.append([config.START], concept0),
                                    np.append([config.START], concept1),
                                    np.append([config.START], concept2),
                                   np.append([config.START], correctness))])

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        raw_uid,raw_content_ids, raw_concept0s,raw_concept1s,raw_concept2s,raw_correctness = self.data[idx]
        seq_len = len(raw_content_ids)

        input_uid_ids = np.zeros(self.max_seq, dtype=np.int64)
        input_content_ids = np.zeros(self.max_seq, dtype=np.int64)
        input_concept0s = np.zeros(self.max_seq, dtype=np.int64)
        input_concept1s = np.zeros(self.max_seq, dtype=np.int64)
        input_concept2s = np.zeros(self.max_seq, dtype=np.int64)
        input_correctness = np.zeros(self.max_seq, dtype=np.int64)


        label = np.zeros(self.max_seq, dtype=np.int64)

        if seq_len == self.max_seq + 1:
            input_uid_ids[:] = raw_uid[1:]
            input_content_ids[:] = raw_content_ids[1:]
            input_concept0s[:] = raw_concept0s[1:]
            input_concept1s[:] = raw_concept1s[1:]
            input_concept2s[:] = raw_concept2s[1:]
            input_correctness[:] = raw_correctness[:-1]

            label[:] = raw_correctness[1:] - 2
        else:
            input_uid_ids[-(seq_len - 1):] = raw_uid[1:]
            input_content_ids[-(seq_len - 1):] = raw_content_ids[1:]
            input_concept0s[-(seq_len - 1):] = raw_concept0s[1:]
            input_concept1s[-(seq_len - 1):] = raw_concept1s[1:]
            input_concept2s[-(seq_len - 1):] = raw_concept2s[1:]
            input_correctness[-(seq_len - 1):] = raw_correctness[:-1]

            label[-(seq_len - 1):] = raw_correctness[1:] - 2

        _input = {
                  "userid": input_uid_ids.astype(np.int64),
                  "probid": input_content_ids.astype(np.int64),
                  "concept0": input_concept0s.astype(np.int64),
                  "concept1": input_concept1s.astype(np.int64),
                  "concept2": input_concept2s.astype(np.int64),
                  "judgestatus": input_correctness.astype(np.int64)
                 }
        return _input, label
