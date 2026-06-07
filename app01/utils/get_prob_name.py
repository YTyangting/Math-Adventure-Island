import pandas as pd

# from bs4 import BeautifulSoup

import os
import json
import glob
import re


def get_prob_dict(url_file_path):
    # =====读取本地html元素===== #
    # soup = BeautifulSoup(open(url_file_path, encoding='utf-8'), features='html.parser')  # features值可为lxml
    #
    # prob_title = ''
    #
    # # =====通过BeautifulSoup的方法获取最外层div的每个子元素===== #
    # for child in soup.div.children:
    #     if child == '\n':  # 去除换行元素
    #         continue
    #     prob_title = child.string.strip().replace('\n', '')
    #     break
    #
    # return prob_title
    return None


def get_prob_name(root_path=None, prob_id=None):
    if root_path:
        probs_root_path = root_path
    else:
        probs_root_path = r'./templates/my_tag/prob'  # 路径都是相对于manage.py来说的

    if prob_id:
        prob_id = prob_id + '.html'
        probs_path = glob.glob(os.path.join(probs_root_path, prob_id))
        if not probs_path:
            return None
    else:
        probs_path = glob.glob(os.path.join(probs_root_path, '*.html'))

    pattern = re.compile(r'([-\d]+)_(\d+)')  # 正则表达, 把_两边的数字提取出来
    # probs_dict_list = []
    # prob_id_list = []
    # prob_title_list = []
    prob_id_title_lists = []
    for path in probs_path:
        prob_id_title_list = []
        id_type, id_num = pattern.search(path).groups()
        key = id_type + '_' + id_num
        title = get_prob_dict(path)
        prob_id_title_list.append(key)
        prob_id_title_list.append(title)
        prob_id_title_lists.append(prob_id_title_list)
        # prob_dict = {key: title}
        # prob_id_list.append(key)
        # prob_title_list.append(title)
        # probs_dict_list.append(prob_dict)
    # return prob_id_list, prob_title_list, probs_dict_list
    return prob_id_title_lists


# 通过json文件获取题目文本信息
def get_prob_content_dict_list(json_file_path):
    with open(json_file_path, 'r', encoding='utf-8') as jsFile:
        jsObj = json.load(jsFile, strict=False)
    return jsObj


# 根据json文件名, 组成{type: content}字典
def get_prob_dict_with_json(root_path=None):
    if not root_path:
        root_path = r'./templates/my_tag/prob_json'  # 路径都是相对于manage.py来说的
    json_file_path = glob.glob(os.path.join(root_path, '*.json'))
    prob_dict = {}
    prob_type_list = []
    pattern = re.compile(r'([-\d]+).')  # 正则表达, 把.前面的数字提取出来
    for path in json_file_path:
        prob_type = int(pattern.search(path).groups()[0])
        prob_type_list.append(prob_type)
        prob_dict[prob_type] = get_prob_content_dict_list(path)  # 把相同类别的题目放在字典同一个key下面
    return prob_type_list, prob_dict


# 根据相应的条件{'category': None, 'id': None}获取dataframe相应值
def get_diff_with_csv(cond=None, root_path=None, csv_file_name=None, col_name=None):
    if not root_path:
        root_path = r'./templates/my_tag/prob_json'  # 路径都是相对于manage.py来说的
    if not csv_file_name:
        csv_file_name = 'diff.csv'
    if not col_name:
        col_name = ["category", "id", "diff"]
    diff = pd.read_csv(os.path.join(root_path, csv_file_name), names=col_name)
    # print(diff.head())
    if cond:  # cond = {'category': None, 'id': None}这样的字典形式
        difficulty = diff[(diff['category'] == cond['category']) & (diff['id'] == cond['id'])]['diff']
        # print(difficulty.values)
        if difficulty.values:  # 可能diff.csv没有这道题目的难度, 就返回None
            return difficulty.values[0]
        else:
            return None
    return diff


# 根据cond='name'条件, 返回所有知识点名称
# 或者根据相应的条件{'id': None}获取dataframe相应知识点名称
def get_concepts_with_csv(cond=None, root_path=None, csv_file_name=None, col_name=None):
    if not root_path:
        root_path = r'./templates/my_tag/prob'  # 路径都是相对于manage.py来说的
    if not csv_file_name:
        csv_file_name = 'concepts.csv'
    if not col_name:
        col_name = ['id', 'name']
    concepts = pd.read_csv(os.path.join(root_path, csv_file_name), names=col_name)
    if type(cond) == dict:  # cond = {'id': None}这样的字典形式
        if cond.get('id', None):
            concept = concepts[(concepts['id'] == cond['id'])]['name']
            if concept.values:  # 可能diff.csv没有这道题目的难度, 就返回None
                return concept.values[0]
            else:
                return None
        else:
            return None
    if type(cond) == str:
        if cond == 'name':
            return concepts['name']
        elif cond == 'id':
            return concepts['id']
        else:
            return concepts['name'], concepts['id']
    return


# 根据相应的条件{'category': None, 'id': None}获取dataframe相应知识点在csv中id
def get_problems_concepts_with_csv(cond=None, root_path=None, csv_file_name=None, col_name=None):
    if not root_path:
        root_path = r'./templates/my_tag/prob'  # 路径都是相对于manage.py来说的
    if not csv_file_name:
        csv_file_name = 'problems.csv'
    if not col_name:
        col_name = ['category', 'id', 'cid1', 'cid2', 'cid3']
    problems = pd.read_csv(os.path.join(root_path, csv_file_name), names=col_name)
    # print(cond)
    # print(problems['category'][0])
    # print(problems['id'][0])
    if type(cond) == dict:  # cond = {'category': None, 'id': None}这样的字典形式
        concepts = problems[(problems['category'] == cond['category'])
                            & (problems['id'] == cond['id'])]
        if len(concepts) != 0:
            concepts_id = concepts[['cid1', 'cid2', 'cid3']]
            return list(concepts_id.iloc[0])
        else:
            return None
    return problems


def is_problem_has_html_file(category, pid, root_path=None):
    if not root_path:
        root_path = r'./templates/my_tag/prob'  # 路径都是相对于manage.py来说的
    probs_path = glob.glob(os.path.join(root_path, '*.html'))
    prob_name = f'{category}_{pid}.html'
    for prob_path in probs_path:
        html_name = os.path.basename(prob_path)
        if html_name == prob_name:
            return True
    return False

