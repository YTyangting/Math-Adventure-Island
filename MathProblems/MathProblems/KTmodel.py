import torch

CONCEPT_NUM = 5  # 知识点的个数

"""
    predict(q_seq, c_seq, r_seq)  
    
    函数说明：
    根据学生的历史序列预测答对下一道题目的概率。
    
    输入:
    q_seq (list of int): 学生做题记录题号序列   （长度为n，最后一位为要预测的试题）
    c_seq (list of int): 学生做题记录知识点序列 （长度为n，最后一位为要预测的试题对应的知识点）
    r_seq (list of 0/1): 学生做对、做错序列     （长度为n-1，对应前n-1题的表现）
    
    返回:
    float: 返回学生答对最后一道题的概率
    
    示例：
        out = predict([102, 315, 15], [0, 3, 1], [1, 1])
        print(out)  # 0.8129
"""

"""
    diagnose(q_seq, c_seq, r_seq)  
    
    函数说明：
    根据学生的历史序列预测诊断学生在每个知识点的掌握情况
    
    输入:
    q_seq (list of int): 学生做题记录题号序列   （长度为n）
    c_seq (list of int): 学生做题记录知识点序列 （长度为n）
    r_seq (list of 0/1): 学生做对、做错序列     （长度为n，对应前n题的表现）
    
    返回:
    list of float: 返回学生答对最后一道题的概率
    
    示例：
        diagnosis = print(diagnose([102, 103, 104], [1, 2, 3], [1, 0, 1]))
        print(diagnosis)  # [0.7890334129333496, 0.7908498644828796, 0.6354390978813171, 0.7405465841293335, 0.7540338039398193]
    
"""


def create_inference_function():
    cuda_avaliable = torch.cuda.is_available()
    if cuda_avaliable:
        model = torch.load("model_S2_best")
    else:
        model = torch.load("C:/Users/lenovo/Desktop/knowledge_trace_new/knowledge_trace/MathProblems/MathProblems/model_S2_best",map_location=torch.device('cpu'))

    def predict(q_seq, c_seq, r_seq):
        assert len(q_seq) == len(c_seq) and len(q_seq) == len(r_seq) + 1
        nonlocal model
        if len(q_seq) > 200:
            q_seq = q_seq[-200:]
            c_seq = c_seq[-200:]
            r_seq = r_seq[-199:]
        r_seq = r_seq + [-1]
        pad_length = 200 - len(q_seq)

        q_tensor = torch.tensor(q_seq).unsqueeze(0)
        r_tensor = torch.tensor(r_seq).unsqueeze(0)

        if pad_length > 0:
            q_tensor = torch.cat([torch.ones(1, pad_length) * -1, q_tensor.float()], dim=1)
            r_tensor = torch.cat([torch.ones(1, pad_length) * -1, r_tensor.float()], dim=1)

        c_tensor_onehot = torch.zeros((1, 200, 124))
        for i, conept in enumerate(c_seq):
            c_tensor_onehot[0, pad_length + i, conept] = 1

        if cuda_avaliable:
            q_tensor = q_tensor.cuda()
            c_tensor_onehot = c_tensor_onehot.cuda()
            r_tensor = r_tensor.cuda()
        out = model(q_tensor, c_tensor_onehot, r_tensor, domain=-1, use_centroid="target")
        return torch.sigmoid(out[0, -1, 0]).item()

    def diagnose(q_log, c_log, r_log):
        assert len(q_log) == len(c_log) and len(q_log) == len(r_log)
        nonlocal model

        diagnose_result = [0 for i in range(CONCEPT_NUM)]

        for C in range(CONCEPT_NUM):
            q_seq = q_log + [0]
            c_seq = c_log + [C]
            r_seq = r_log
            if len(q_seq) > 200:
                q_seq = q_seq[-200:]
                c_seq = c_seq[-200:]
                r_seq = r_seq[-199:]
            r_seq = r_seq + [-1]
            pad_length = 200 - len(q_seq)

            q_tensor = torch.tensor(q_seq).unsqueeze(0)
            r_tensor = torch.tensor(r_seq).unsqueeze(0)

            if pad_length > 0:
                q_tensor = torch.cat([torch.ones(1, pad_length) * -1, q_tensor.float()], dim=1)
                r_tensor = torch.cat([torch.ones(1, pad_length) * -1, r_tensor.float()], dim=1)

            c_tensor_onehot = torch.zeros((1, 200, 124))
            for i, conept in enumerate(c_seq):
                c_tensor_onehot[0, pad_length + i, conept] = 1

            if cuda_avaliable:
                q_tensor = q_tensor.cuda()
                c_tensor_onehot = c_tensor_onehot.cuda()
                r_tensor = r_tensor.cuda()
            out = model(q_tensor, c_tensor_onehot, r_tensor, domain=-1, use_centroid="target")
            diagnose_result[C] = torch.sigmoid(out[0, -1, 0]).item()
        return diagnose_result

    return predict, diagnose


# 创建推理函数实例

def kt_predict(q_log, c_log, r_log):
    predict, diagnose = create_inference_function()
    out = predict(q_log, c_log, r_log[:-1] )
    dig=diagnose(q_log, c_log, r_log)
    return out,dig
    #return dig
