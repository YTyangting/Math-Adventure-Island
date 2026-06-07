"""knowledge_trace URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve

from app01 import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.login),
    path('login/', views.login),
    path('login/random_code/', views.get_random_code),
    path('logout/', views.logout),

    # 路由分发, 将所有以api开头的请求分发到api这个urls.py中
    # 所有以api开头的请求都分发到api.urls里去
    re_path(r'^api/', include('api.urls')),

    # 用户上传文件路由配置
    re_path(r'media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),

    # 获取所有以problem开头的请求, 同时接受名称为nid的参数, 类型为'数字(\d+)'
    re_path(r'problemset/(?P<nid>\d+)', views.problem),

    path('dl_index/', views.dl_index),
    path('problemset/', views.problemset),
    path('test/', views.test),
    path('newtest/', views.newtest),
    path('welcome/', views.welcome),
    path('report/', views.report),
    path('simulation/', views.simulation),
]
