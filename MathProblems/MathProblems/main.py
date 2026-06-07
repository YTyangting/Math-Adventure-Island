import numpy as np
import pandas as pd
import jieba
import plotly.express as px
import matplotlib.pyplot as plt
from KTmodel import predict, diagnose

path1 = "./train23k.json"
path2 = "./test23k.json"
path3 = "./valid23k.json"

data = pd.read_json("train23k.json", orient='records')
data2 = pd.read_json("test23k.json", orient='records')
data3 = pd.read_json("valid23k.json", orient='records')
data = pd.concat([data, data2, data3])


def simplify_equation(equation):
    equation = equation.replace("[", "(").replace("]", ")").replace("{", "(").replace("}", ")")
    equation = equation.replace('%', '/100').replace("^", "**")
    return equation


def calculate_from_string(equation):
    equation = simplify_equation(equation)
    # 移除等号左侧的变量赋值部分，只保留表达式
    expression = equation.split('=')[1]
    # 计算表达式的值
    result = eval(expression)
    return result


def simplify(expr):
    n = len(expr)
    output = ''
    flag = True
    for i in range(2, n):
        if flag and (expr[i].isdigit() or expr[i] == '.' or expr[i] == '%'):
            output = output + 'n'
            flag = False
        if not (expr[i].isdigit() or expr[i] == '.' or expr[i] == '%'):
            if expr[i] == '[' or expr[i] == '{':
                output = output + '('
            elif expr[i] == ']' or expr[i] == '}':
                output = output + ')'
            elif expr[i] == '-':
                output = output + '+'
            elif expr[i] == '/':
                output = output + '*'
            else:
                output = output + expr[i]
            flag = True
    return output


def calc_difficulty(equation):
    difficulty = 0

    def eval(x):
        if x == '+':
            return 2
        elif x == '-':
            return 3
        elif x == '*':
            return 5
        elif x == '/':
            return 7
        elif x == '(':
            return 8
        elif x == '%':
            return 5
        elif x == '^':
            return 6
        else:
            return 0

    for op in equation:
        difficulty += eval(op)
    return difficulty


def classify_equation(equation):
    class1 = ["+", "-", "(", ")"]
    class2 = ["+", "-", "(", ")", "*", "/"]
    class3 = ["+", "-", "(", ")", "*", "/", "%", "^"]
    if all(op in class1 for op in equation if op != "n"):
        return "class1"
    elif all(op in class2 for op in equation if op != "n"):
        return "class2"
    elif all(op in class3 for op in equation if op != "n"):
        return "class3"
    else:
        return "other"






data['post_expression'] = data['equation'].apply(simplify)
data["difficulty"] = data['equation'].apply(calc_difficulty)
data["classification"] = data['post_expression'].apply(classify_equation)

classification_counts = data['classification'].value_counts()
# Plotting the pie chart
plt.figure(figsize=(8, 8))
plt.pie(classification_counts, labels=classification_counts.index, autopct='%1.1f%%', startangle=140, colors=['skyblue', 'lightgreen', 'salmon'])
plt.title('Distribution of Equation Classifications')
plt.axis('equal')
plt.show()
exit()

# Plotting the histogram
plt.figure(figsize=(10, 6))
plt.hist(data['difficulty'], bins=300, color='skyblue', edgecolor='black')
plt.title('Distribution of Question Difficulties')
plt.xlabel('Difficulty')
plt.ylabel('Frequency')
plt.grid(axis='y', alpha=0.75)
plt.show()


