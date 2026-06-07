from statistics import mode
import numpy as np
from torch import batch_norm, tensor
import mainc as m
import pandas as pd
# 在django项目里这个目录直接import有问题
import configc as config
# import static.KT_with_code.configc as config
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
import csv
import matplotlib as plt
# 在django项目里这个目录直接import有问题
from prob_data import *
# from static.KT_with_code.prob_data import *
import os

p = os.path.dirname(os.path.realpath(__file__)) + '/saved_model/epoch10_auc0.770735_best'
model = torch.load(p)
# Model = pl.Trainer
# 评估模式 而不是训练模型
model.eval()


def analyse(user_id, seq_of_prob, previous_correctness, n, concept_ability):
    num_concept = [0 for i in range(19)]
    prob_done = {}  # (fid,pid):[right,num_try]
    seq_of_prob = seq_of_prob[0:n - 1]
    for idx, prob in enumerate(seq_of_prob):
        c1, c2, c3 = _get_concept(prob)
        num_concept[c1] += 1
        if c2 != c1:
            num_concept[c2] += 1
        if c3 != c2 and c3 != c1:
            num_concept[c3] += 1

        if prob in prob_done:
            prob_done[prob][1] += 1
            if previous_correctness[idx] == 1:
                prob_done[prob][0] = True
        else:
            prob_done[prob] = [False, 1]
            if previous_correctness[idx] == 1:
                prob_done[prob][0] = True

    num_correct = 0
    max_try_num = 0
    min_try_num = n
    for prob in prob_done:
        if prob_done[prob][0] == True:
            num_correct += 1
        if prob_done[prob][1] > max_try_num:
            max_try_num = prob_done[prob][1]
            max_try_prob = prob
        elif prob_done[prob][1] < min_try_num:
            min_try_num = prob_done[prob][1]
            min_try_prob = prob

    best = 0
    worst = 1
    for c in concept_ability:
        if concept_ability[c] < worst:
            worst = concept_ability[c]
            worst_c = c
        if concept_ability[c] > best:
            best = concept_ability[c]
            best_c = c

    a_str = []
    a_str.append("你总共做了%d道编程练习题" % (len(prob_done)))
    if num_correct > 0:
        a_str.append("你通过了其中的%d道题目" % (num_correct))
    else:
        a_str.append("你没有答对任何题目")
    if max_try_num != min_try_num and max_try_num != 0 and min_try_num != n:
        a_str.append("你提交次数最多的题目是(%d,%d)" % (max_try_prob[0], max_try_prob[1]))
        a_str.append("总共提交了%d次才通过" % (max_try_num))
        a_str.append("你提交次数最少的题目是(%d,%d)" % (min_try_prob[0], min_try_prob[1]))
        a_str.append(("提交了%d次就通过了" % (min_try_num)))
    if best != worst:
        a_str.append(("你对" + concept_name[int(best_c)] + "的掌握情况比较好"))
        a_str.append(((concept_name[int(worst_c)]) + "相关的知识还需加强"))
    return a_str, worst_c


def predict(user_id, seq_of_prob, previous_correctness, n):
    '''

    :param user_id:                     type:int              id of the student
    :param seq_of_prob:                 type:list             N problems [prob1,prob2...prob_n] where prob_i=(prob_fieldid,prob_id)
    :param previous_correctness:        type:list             N-1 responses(0 or 1) representing correctness of prob1 to prob_n-1
    :param n:                           type:int              num of problems(n>10)
    :return:                            type:dict             analysis result
    '''
    # 断言   不符合则返回False
    assert (len(seq_of_prob) == n)
    assert (len(previous_correctness) == n - 1)  # ？？？

    # 获取输入题目所相关的知识点
    known_concepts_seq = get_known_concepts(seq_of_prob)

    # 构造学生输入序列
    input = _change_to_tensor_input(user_id, seq_of_prob, previous_correctness, n)
    predict, concept_ability_ = model(input)
    concept_ability_ = torch.sigmoid(concept_ability_[n - 1])
    concept_ability = {}
    for i in range(1, 18):
        concept_ability[str(i)] = concept_ability_[i - 1].item()

    strs, worst_c = analyse(user_id, seq_of_prob, previous_correctness, n, concept_ability)
    recommend_probs = get_recommend_probs(worst_c, 5, seq_of_prob)
    concept_proportion = get_concept_proportion(seq_of_prob)
    output = {"concept": concept_ability, "analyze": strs, "recommend_probs": recommend_probs,
              "concept_proportion": concept_proportion}

    return output


def get_known_concepts(seq_of_prob):
    known_concepts_bool = [False for i in range(19)]
    known_concepts = []
    for prob in seq_of_prob:
        concept0, concept1, concept2 = _get_concept(prob)
        known_concepts_bool[concept0] = True
        known_concepts_bool[concept1] = True
        known_concepts_bool[concept2] = True
    for i in range(18):
        if known_concepts_bool[i]:
            known_concepts.append(i)
    return known_concepts


def get_recommend_probs(concept, num, prob_seq):
    result = []
    concept = int(concept)
    for prob in our_probs:
        if concept in _get_concept(prob) and prob not in prob_seq:
            result.append(str(prob[0]) + '_' + str(prob[1]))
            if len(result) == num:
                return result
    return result


def get_concept_proportion(prob_seq):
    concepts = [0 for i in range(19)]
    for prob in prob_seq:
        c1, c2, c3 = _get_concept(prob)
        concepts[c1] += 1
        concepts[c2] += 1
        concepts[c3] += 1
    num = len(prob_seq) * 3
    for i in range(1, 19):
        concepts[i] = concepts[i] / num

    return concepts


def _change_probid(prob):
    fid, pid = prob
    if (fid, pid) in repeat_dict:
        fid, pid = repeat_dict[(fid, pid)]
    return prob_list.index((fid, pid))


def _get_concept(prob):
    fid, pid = prob
    if (fid, pid) in repeat_dict:
        fid, pid = repeat_dict[(fid, pid)]
    return concept_dict[(fid, pid)]


def _change_to_tensor_input(user_id, seq_of_prob, previous_correctness, n):
    '''

    :param user_id:   type:int              id of the student
    :param seq_of_prob: type:list           N problems [prob1,prob2...prob_n] where prob_i=(prob_fieldid,prob_id)
    :param previous_correctness:            N-1 responses(0 or 1) representing correctness of prob1 to prob_n-1
    :param n:                               num of problems(n>10)
    :return: input for the Model
    '''
    assert (len(seq_of_prob) == n)
    assert (len(previous_correctness) == n - 1)
    assert (n >= 10)

    input_uid_ids = np.zeros(config.MAX_SEQ, dtype=np.int64)
    input_content_ids = np.zeros(config.MAX_SEQ, dtype=np.int64)
    input_concept0s = np.zeros(config.MAX_SEQ, dtype=np.int64)
    input_concept1s = np.zeros(config.MAX_SEQ, dtype=np.int64)
    input_concept2s = np.zeros(config.MAX_SEQ, dtype=np.int64)
    input_correctness = np.zeros(config.MAX_SEQ, dtype=np.int64)

    begin_idx = 0
    if n >= 70:  # bigger than max_seq
        begin_idx = n % 70
        input_correctness[0] = 1
        for i in range(70):
            input_uid_ids[i] = user_id
            input_content_ids[i] = _change_probid(seq_of_prob[i + begin_idx]) + 2
            input_concept0s[i] = _get_concept(seq_of_prob[i + begin_idx])[0] + 1
            input_concept1s[i] = _get_concept(seq_of_prob[i + begin_idx])[1] + 1
            input_concept2s[i] = _get_concept(seq_of_prob[i + begin_idx])[2] + 1
            if i < 69:
                input_correctness[i + 1] = previous_correctness[i] + 2

    else:
        begin_idx = 70 - n
        input_correctness[begin_idx] = 1
        for i in range(begin_idx, 70):
            input_uid_ids[i] = user_id
            input_content_ids[i] = _change_probid(seq_of_prob[i - begin_idx]) + 2
            input_concept0s[i] = _get_concept(seq_of_prob[i - begin_idx])[0] + 1
            input_concept1s[i] = _get_concept(seq_of_prob[i - begin_idx])[1] + 1
            input_concept2s[i] = _get_concept(seq_of_prob[i - begin_idx])[2] + 1
            if i < 69:
                input_correctness[i + 1] = previous_correctness[i - begin_idx] + 2

    _input = {
        "userid": tensor([input_uid_ids.astype(np.int64)]),
        "probid": tensor([input_content_ids.astype(np.int64)]),
        "concept0": tensor([input_concept0s.astype(np.int64)]),
        "concept1": tensor([input_concept1s.astype(np.int64)]),
        "concept2": tensor([input_concept2s.astype(np.int64)]),
        "judgestatus": tensor([input_correctness.astype(np.int64)])
    }
    return _input


def to_pair(p):
    return ((int)(p[0]), (int)(p[1]))


if __name__ == '__main__':
    uid = 15
    # 题号
    probs = [(1, 1001) for i in range(9)] + [(1, 1007) for i in range(4)]
    resp = [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1]
    c = predict(uid, probs, resp, 13)
    print(c)
