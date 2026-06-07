from django import forms
from django.contrib import auth
from app01.models import UserInfo
from django.views import View
from django.http import JsonResponse

# CBV class
# FBV function
# 登录注册字段验证父类


class LoginBaseForm(forms.Form):
    # 三个变量被加到了self.cleaned_data字典里
    # 用来forms.Form类校验使用
    name = forms.CharField(error_messages={'required': '请输入用户名!'})
    pwd = forms.CharField(error_messages={'required': '请输入密码!'})
    code = forms.CharField(error_messages={'required': '请输入验证码!'})

    # 重写init方法
    def __init__(self, *args, **kwargs):
        # 做自己的判断逻辑
        # 获取'request'参数, 如果没有返回None,
        # 并且通过pop把它删去, 以免影响原有Form操作
        # 最后存入类成员变量, 供下面的局部钩子函数使用
        self.request = kwargs.pop('request', None)
        # 调用父类初始化方法
        super().__init__(*args, **kwargs)

    # 局部钩子
    def clean_code(self):
        code = self.cleaned_data.get('code')
        valid_code: str = self.request.session.get('valid_code')
        # print(valid_code.upper(), data)
        if code == '123':  # 跳过验证码校验, 方便测试, 以后删除
            return self.cleaned_data
        if valid_code.upper() != code.upper():  # 不区分大小写
            # 给字段添加一个错误信息
            self.add_error('code', '验证码输入错误!')
        return self.cleaned_data


# 登录的字段验证
class LoginForm(LoginBaseForm):

    # 全局钩子
    def clean(self):
        name = self.cleaned_data.get('name')
        pwd = self.cleaned_data.get('pwd')

        # 校验用户, 错误会返回None
        user = auth.authenticate(username=name, password=pwd)
        # print(user, name, pwd)
        if not user:
            # 失败, 给字段添加一个错误信息
            self.add_error('pwd', '用户名或密码错误!')
            return self.cleaned_data
        # 把用户对象放到cleaned_data中
        self.cleaned_data['user'] = user
        # 此处不能写登陆操作, 因为这里只是校验了一个错误
        return self.cleaned_data


# 注册的字段验证
class SignForm(LoginBaseForm):
    re_pwd = forms.CharField(error_messages={'required': '请输入确认密码!'})

    def clean_name(self):
        name = self.cleaned_data.get('name')
        user_query = UserInfo.objects.filter(username=name)
        if user_query:
            self.add_error('name', '该用户已经被注册了!')
        return self.cleaned_data

    # 全局钩子
    def clean(self):
        pwd = self.cleaned_data.get('pwd')
        re_pwd = self.cleaned_data.get('re_pwd')

        if pwd != re_pwd:
            # 失败, 给字段添加一个错误信息
            self.add_error('re_pwd', '两次密码不一致!')
        return self.cleaned_data


# 登陆失败的可复用代码
def clean_form(form):
    # 验证不通过
    err_dict: dict = form.errors  # 这是一个字典
    # 首先拿到所有错误字段名字,
    # 然后获取错误的第一个字段, 如果name输入了, 那其实拿到的就是pwd
    err_valid = list(err_dict.keys())[0]
    # 拿到第一个错误字段的第一个错误信息
    err_msg = err_dict[err_valid][0]
    # print(err_valid, err_msg)
    return err_valid, err_msg


# CBV
class LoginView(View):
    def post(self, request):
        # 返回给前端信息
        res = {
            'code': 425,
            'msg': "登录成功!",
            'self': None  # 记录哪个字段出错了, 方便前端选中错误项
        }
        # middleware_decode中间件已经处理了post请求, 把数据挂载到request.data了
        # data = request.data

        form = LoginForm(request.data, request=request)
        print("yes")
        if not form.is_valid():
            res['self'], res['msg'] = clean_form(form)
            return JsonResponse(res)

        # 执行登录操作
        # 在LoginForm的全局钩子里, 检验完数据库用户名后,
        # 把用户名放入了self.cleaned_data中
        user = form.cleaned_data.get('user')
        # 登录操作
        auth.login(request, user)
        res['code'] = 0
        return JsonResponse(res)


class SignView(View):
    def post(self, request):
        # 返回给前端信息
        res = {
            'code': 425,
            'msg': "注册成功!",
            'self': None  # 记录哪个字段出错了, 方便前端选中错误项
        }
        form = SignForm(request.data, request=request)
        if not form.is_valid():
            res['self'], res['msg'] = clean_form(form)
            return JsonResponse(res)

        # 注册成功代码
        # print(form.cleaned_data.get('name'))  # 这里好像name重名了, 拿到错误数据
        # print(form.cleaned_data.get('pwd'))
        user = UserInfo.objects.create_user(
            username=request.data.get('name'),
            password=request.data.get('pwd')
        )
        # 注册完成自动登录
        # print(request)
        # print(request.user)
        auth.login(request, user)  # 此句把user属性加入了request
        # print(request)
        # print(request.user)
        res['code'] = 0
        return JsonResponse(res)






