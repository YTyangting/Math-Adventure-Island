from http import HTTPStatus
import dashscope
from dashscope import Generation
from dashscope.api_entities.dashscope_response import Role

dashscope.api_key = 'sk-b12c8ca990e3492386ae6ffdfa857fdc'  # 设置API_KEY

"""
    def get_answer(question, answer, stuans)
    
    函数说明:
    提供问题、正确答案、学生答案三个参数，获取模型对学生答案的纠正、分析和一道同类型的题目
    
    输入:
    question str:问题题干，根据序号在题干字典original_text中获取
    answer str:正确答案，根据序号在答案字典equation中获取
    stuans str:学生答案，每次循环时手动输入
    
    返回:
    str:模型对学生答案的纠正、分析和一道同类型的题目
    
    示例:
    详见底部main函数
    

"""


def conversation_with_messages(original_text, equation, stu_answer):
    messages = [{'role': Role.SYSTEM, 'content': 'You are a helpful assistant.'}]
    # 循环实现多轮会话
    while True:
        # print("\n第{}个问题:{}".format(i + 1, original_text[i]))
        # prompt = (("你是一名教师，现在告诉你问题、问题的正确回答以及学生的回答，这是问题:根据下列问题列出方程(不需要计算出最终结果){}  这是问题的正确回答:{}").format(
        # original_text[i],equation[i])+ "这是学生的回答:"+input(
        # "\n请输入你的答案:"))+"请你根据问题的正确回答，判断学生的回答是否正确并加以分析、纠正。最后出一个同样类型的题目供学生练习"
        prompt = (
                "你是一名教师，现在告诉你问题、问题的正确回答以及学生的回答，公式不要通过LaTeX语法输出，*表示乘号，/表示除号，+表示加号，-表示减号，=表示等号。这是问题:根据下列问题列出方程(不需要计算出最终结果){}  这是问题的正确回答:{}  这是学生的回答:{}".format(
                    original_text, equation, stu_answer)
                + "请你根据问题的正确回答，判断学生的回答是否正确并加以分析、纠正")

        promt=("你是一名教师，现在告诉你问题、问题的正确回答以及学生的回答，公式不要通过LaTeX语法输出，并且*表示乘号，/表示除号，+表示加号，-表示减号，=表示等号。这是问题:根据下列问题列出方程(不需要计算出最终结果){}  这是问题的正确回答:{}  这是学生的回答:{}".format(
                    original_text, equation, stu_answer)
                + "通过学生回答情况给出一个同样类型的题目供学生练习")

        # 添加新一轮会话用户的问题
        messages.append({'role': Role.USER, 'content': prompt})
        messages_1=[{'role': Role.USER, 'content': promt}]

        response = Generation.call(
            Generation.Models.qwen_turbo,  # 选择响应的模型
            messages=messages,
            result_format='message',  # set the result to be "message" format.
        )
        response_1 = Generation.call(
            Generation.Models.qwen_turbo,  # 选择响应的模型
            messages=messages_1,
            result_format='message',  # set the result to be "message" format.
        )
        if response.status_code == HTTPStatus.OK and response_1.status_code == HTTPStatus.OK:
            # print(response.output.choices[0].message.content)
            content = response.output.choices[0].message.content
            content_1 = response_1.output.choices[0].message.content
            # 把模型的输出添加到messages中
            messages.append({'role': response.output.choices[0]['message']['role'],
                             'content': response.output.choices[0]['message']['content']})
            messages_1.append({'role': response_1.output.choices[0]['message']['role'],
                             'content': response_1.output.choices[0]['message']['content']})

            return content,content_1
        else:
            print('Request id: %s, Status code: %s, error code: %s, error message: %s' % (
                response.request_id, response.status_code,
                response.code, response.message
            ))
            exit()
        i = i + 1


def conversation_with_messages_a(original_text, equation, stu_answer):
    messages = [{'role': Role.SYSTEM, 'content': 'You are a helpful assistant.'}]
    # 循环实现多轮会话
    while True:
        # print("\n第{}个问题:{}".format(i + 1, original_text[i]))
        # prompt = (("你是一名教师，现在告诉你问题、问题的正确回答以及学生的回答，这是问题:根据下列问题列出方程(不需要计算出最终结果){}  这是问题的正确回答:{}").format(
        # original_text[i],equation[i])+ "这是学生的回答:"+input(
        # "\n请输入你的答案:"))+"请你根据问题的正确回答，判断学生的回答是否正确并加以分析、纠正。最后出一个同样类型的题目供学生练习"
        prompt = (
                "你是一名教师，现在告诉你问题、问题的正确回答以及学生的回答，这是问题:根据下列问题列出方程(不需要计算出最终结果){}  这是问题的正确回答:{}  这是学生的回答:{}".format(
                    original_text, equation, stu_answer)
                + "请你根据问题的正确回答，判断学生的回答是否正确并加以分析、纠正。最后给出一个同样类型的题目供学生练习并给出方程，并且公式不要通过LaTeX语法输出")
        # 添加新一轮会话用户的问题
        messages.append({'role': Role.USER, 'content': prompt})
        response = Generation.call(
            Generation.Models.qwen_turbo,  # 选择响应的模型
            messages=messages,
            result_format='message',  # set the result to be "message" format.
        )
        if response.status_code == HTTPStatus.OK:
            # print(response.output.choices[0].message.content)
            content = response.output.choices[0].message.content
            # 把模型的输出添加到messages中
            messages.append({'role': response.output.choices[0]['message']['role'],
                             'content': response.output.choices[0]['message']['content']})
            return content
        else:
            print('Request id: %s, Status code: %s, error code: %s, error message: %s' % (
                response.request_id, response.status_code,
                response.code, response.message
            ))
            exit()
        i = i + 1


def get_answer(question, answer, stuans):
    return conversation_with_messages(question, answer, stuans)


