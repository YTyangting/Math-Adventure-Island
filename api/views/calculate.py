# 实现简单的加减乘除括号等运算
# Calculator

def calculator(expression):
    print(expression)
    import re
    # 操作字典,目前只支持加减乘除
    operatorDict ={
        '+': lambda a, b: float(a)+float(b),
        '-': lambda a, b: float(a)-float(b),
        '*': lambda a, b: float(a)*float(b),
        '/': lambda a, b: float(a)/float(b),
        '^': lambda a, b: float(a)**float(b),   
    

    }
    # 计算去括号后表达式的值
    def calBrackets(expre):
        for i in operatorDict:
            expre = expre.replace(i, 's'+i+'s')
        l = expre.split('s')  # 表达式转化为数字运算符列表
        for i in l:
            if '%' in i:
                str1 = i.replace('%', '')
                l[l.index(i)] = str(float(str1)/100)  # 百分数转化为小数
        # 将-和数字组合在一起

        l2, i = [], 0
        while i < len(l):
            # 处理负数
            if l[i] == '':  # 负号开头或者负号与其他运算符连在一起,splite后会为'',例如 -5*-2  ['','-','5','*','','-','2']
                l2.append(l[i+1]+l[i+2])   # 将符号和数字合一起  -2
                i += 2
            else:
                l2.append(l[i])
            i += 1
        # l2为新数字运算符列表(处理符号后,例['-1', '+', '*', '-3'])
        # 运算乘除
        i = 1
        while i < len(l2):  # 计算乘除
            if l2[i] in ['*', '/','^']:
                # 将符号左右以及符号三个元素替换为运算结果,必须是个列表, list[m:n] :切片取值连续,不包括n
                l2[i-1:i+2] = [operatorDict[l2[i]](l2[i-1], l2[i+1])]  # 运算
            else:
                i += 2
        # 运算加减,直接按顺序计算替换
        while len(l2) > 1:
            l2[0:3] = [operatorDict[l2[1]](l2[0], l2[2])]
        return str(l2[0])
    # 去除空格
    expression = expression.replace(' ', '')
    # 正则匹配表达式是否包含括号    [^\(\)] : 匹配不是( 或者) 的内容,即非括号内容
    check = re.search('\([^\(\)]+\)', expression)  # 返回匹配到的内容,带括号,只返回一个

    # 去掉括号
    while check:
        checkValue = check.group()
        # 将匹配到的括号表达式替换成值,括号去掉使用函数求值
        expression = expression.replace(checkValue, calBrackets(checkValue[1:-1]))
        check = re.search('\([^\(\)]*\)', expression)
    else:
        return calBrackets(expression)
def accurate(test):
    if '[' in test and ']' in test:
        test=test.replace('[', '(')
        test=test.replace(']', ')')
    result = calculator(test)
    return result