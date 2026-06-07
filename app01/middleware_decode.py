from django.utils.deprecation import MiddlewareMixin
import json


# 解析post请求的数据
class Md1(MiddlewareMixin):
    # 请求中间件, 请求到达路由前拦截
    # 别忘了在settings.py里注册MIDDLEWARE
    def process_request(self, request):
        # django自带的admin请求不是json格式的, 这样一转换会报错, 所以这里加上只修改application/json条件
        # print(request.content_type) 。 可以直接拿到，不用走Meta了
        if request.method == 'POST' and request.META.get('CONTENT_TYPE') == 'application/json':
            # data = request.POST  # QueryDict, 如果不是json格式就放在这里的
            # 请求体, json格式的数据存储在这里面, 而且这是一个二进制的json
            data = request.body
            # 把二进制json重新解码为utf8格式, 并且通过json.loads转为字典
            #dict_data = json.loads(data, encoding='utf8')
            dict_data = json.loads(data)
            # 把数据绑定到request.data上
            request.data = dict_data

    # 响应中间件, 返还页面前拦截
    def process_response(self, request, response):
        return response
