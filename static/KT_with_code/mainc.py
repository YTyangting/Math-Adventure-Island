import gc
import os
import configc as config
from datasetc import DKTDataset
from modelc import LANA
import pandas as pd
from tqdm import tqdm
from prob_data import *
import numpy as np
import torch
from torch import nn
from torch import optim
from torch.utils.data import DataLoader
from torch.autograd import Variable

import matplotlib.pyplot as plt
import sklearn
from sklearn.metrics import roc_auc_score
import argparse


import os

save_los=[]
save_auc=[]

os.environ["CUDA_VISIBLE_DEVICES"] = "2,1,0"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# parser = argparse.ArgumentParser(description="Sample Data Preprocess Script")
# parser.add_argument('-t', '--train_csv', type=str, required=True,
#                     help="Filepath of train.csv")
# args = parser.parse_args()

def load_dataset():
    train_df = pd.read_pickle("newnewnew.train")
    val_df = pd.read_pickle("newnewnew.valid")
    # train_df = pd.read_pickle("%s.train"%(args.train_csv))
    # val_df = pd.read_pickle("%s.valid"%(args.train_csv))
    train_dataset = DKTDataset(train_df.values, max_seq=config.MAX_SEQ,
                               min_seq=config.MIN_SEQ, overlap_seq=config.OVERLAP_SEQ)
    val_dataset = DKTDataset(val_df.values, max_seq=config.MAX_SEQ,
                             min_seq=config.MIN_SEQ, overlap_seq=config.OVERLAP_SEQ)
    train_loader = DataLoader(train_dataset,
                              batch_size=config.BATCH_SIZE,
                              num_workers=6,
                              shuffle=True,
                              pin_memory=True)
    val_loader = DataLoader(val_dataset,
                            batch_size=config.BATCH_SIZE,
                            num_workers=6,
                            shuffle=False,
                            pin_memory=True)
    del train_dataset,val_dataset
    return train_loader,val_loader

train_set,val_set=load_dataset()


def train_one_epoch(num,lr):
    #1111111111111
    #optimizer=torch.optim.Adam(filter(lambda p: p.requires_grad, Model.parameters()), lr = lr)
    optimizer = torch.optim.Adam(model.parameters(),lr=lr)
    criterion=nn.BCEWithLogitsLoss().cuda()
    sum_loss=0
    for batch in tqdm(train_set):
        optimizer.zero_grad()
        input,target=batch[0],batch[1].cuda()
        target_mask = (input["probid"] != config.PAD).cuda()
        target = torch.masked_select(target, target_mask).cuda()
        output,_=model(input)
        loss=criterion(output.float().cuda(), target.float())
        sum_loss+=loss.item()
        loss.backward()
        optimizer.step()
    print("Epoch %d: BCE loss=%f"%(num,sum_loss/len(train_set)))
    save_los.append(float(sum_loss/len(train_set)))


def test(num):
    sum_auc = 0
    model.eval()
    for batch in tqdm(val_set):
        input, target = batch[0], batch[1]
        target_mask = (input["probid"] != config.PAD)
        target = torch.masked_select(target, target_mask)
        output, _  = model(input)
        auc = roc_auc_score(target.cpu(), output.detach().float().cpu())
        sum_auc+=auc
    #print(output)
    print("Epoch %d: ROC auc=%f" % (num, sum_auc / len(val_set)))
    save_auc.append(sum_auc/len(val_set))
    return sum_auc / len(val_set)


def save_model(epoch,auc):
    pth="./saved_model/epoch%d_auc%f_best"%(epoch,auc)
    torch.save(model,pth)
    print("Model saved to %s"%(pth))
    return pth

def train(model,epoch_num,lr,save=True,pth=""):
    print("Start Training")
    model.train()
    if pth != "":
        model=torch.load(pth)
    best_auc = 0
    for i in range(1, epoch_num + 1):
        train_one_epoch(i, lr)
        auc=test(i)
        if save and auc>best_auc:
            if pth!="":
                os.remove(pth)
            pth=save_model(i,auc)
            best_auc=auc
    return pth

def load_code():
    for fid,pid in prob_list:
        if os.path.exists(r"code/(%d,%d).txt"%(fid,pid)):
            f=open(r"code/(%d,%d).txt"%(fid,pid))
            code=f.read()
        else:
            print(r"code/(%d,%d).txt  does not exist!"%(fid,pid))


if __name__ == "__main__":
    ARGS = {"d_model": config.MODEL_DIMS,
            'n_head': config.N_HEADS,
            'n_encoder': config.NUM_ENCODER,
            'n_decoder': config.NUM_DECODER,
            'dim_feedforward': config.FEEDFORWARD_DIMS,
            'dropout': config.DROPOUT,
            'max_seq': config.MAX_SEQ,
            'n_exercises': config.TOTAL_EID,
            'n_probfield': config.TOTAL_FID,
            'n_resp': config.TOTAL_RESP,
            'n_concepts': config.TOTAL_PART,
            'n_state': config.STATE_DIMS
            }
    print(torch.cuda.is_available())
    print(torch.cuda.device_count())
    model=LANA(**ARGS).cuda()
    train(model, 50, 1e-4)
    #train(Model, 30, 3e-5)
    #load_code()
    num_=np.array([i for i in range(50)])
    plt.plot(num_,save_auc,num_,save_los)
    plt.show()
    print('done')
