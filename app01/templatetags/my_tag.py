import json

import requests
from django import template

register = template.Library()


# @register.filter
# def add1(item):
#     return int(item) + 1


# 接受参数menu_name, 并返回一个页面my_tag/headers.html
# 别忘了在要使用该自定义标签的html页面头部导入{% load my_tag %}
@register.inclusion_tag('my_tag/headers.html')
def banner(menu_name, article=None):
    # menu_name, nid参数, 就是在html页面引入{% banner 'article' nid %}时右边参数(空格隔开)
    # nid默认为None, 不需要用到的地方就不用传这个参数
    img_list = [
        '/media/article_img/blog_fengyu.jpg'
        # '/media/article_img/17933.jpg',
        # '/media/article_img/7.jpg',
        # '/media/article_img/6.jpg',
        # '/media/article_img/5.jpg',
        # '/media/article_img/4.jpg',
        # 'http://www.fengfengzhidao.com/media/site_bg/31.jpg',
        # 'http://www.fengfengzhidao.com/media/site_bg/%E5%AE%87%E5%AE%99.png',
        # 'http://www.fengfengzhidao.com/media/site_bg/%E9%A3%9E%E6%9C%BA.png',
        # 'http://www.fengfengzhidao.com/media/site_bg/%E7%BB%BF%E8%89%B2.png',
    ]
    # print(menu_name, article)
    # article不为空时, 是文章详情页的banner
    if article:
        # 获取文章封面
        # article.cover.url是文章封面表的FileField字段,
        # 通过.url方法获取路径, 在settings.py里配置了MEDIA_URL,
        # 所以会自动加上MEDIA_URL值作为前缀
        cover = article.cover.url.url
        # 给img_list重新赋值
        img_list = [cover]
        print(cover)
    # 获取古诗替换介绍
    # https://gushi.ci/
    # response = requests.get('https://v1.jinrishici.com/all.json', timeout=5)
    # poem = json.loads(response.text)
    # # print(poem)
    # test_str = poem['content']  # r'介\n绍'
    test_str = ''
    # test_str = test_str.replace(r'\n', '<br/>')
    return {'img_list': img_list, 'test_str': test_str}


@register.inclusion_tag('my_tag/13_1017.html')
def single_problem(menu_name):
    print(menu_name)
    # 注意return menu_name就会报错, 'SafeString' object does not support item assignment
    # return menu_name
    # 应该return字典
    return {'menu_name': menu_name}


@register.filter(name='displayName')
def displayName(value, arg):
    # http://t.zoukankan.com/kuxingseng95-p-9255712.html
    # return apply(eval('value.get_'+arg+'_display'), ())
    # 上面一句的apply就是执行value.get_category_display这个函数,
    # 我在后面直接加括号也可以执行
    # ProblemsRecommendation.get_category_display()可以获取其choice值
    return eval('value.get_'+arg+'_display()')


@register.filter(name='toString')
def to_string(value):
    return f'"{value}"'

# 上一题 下一题
# def generate_p_n(prob):


