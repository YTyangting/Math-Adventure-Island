import json
import re

from django.shortcuts import redirect

from app01.models import Problems, UserInfo, ProblemRecords, Users2Concepts, Concepts, Problems2Concepts, ShareData
from django.views import View
from django.http import JsonResponse

from django.utils import timezone
from datetime import datetime

from django.db.models import Max
import requests


class ReportBaseView(View):
    def test_concept_radar_charts_option(self, concepts_score, show_concept_count=18):
        # https://echarts.apache.org/examples/zh/editor.html?c=radar
        # concepts_score: [(1,2,'name'), ...]  (u2c.current_score, u2c.last_score, concept_name)
        # concepts_score里不知道为什么只有17个知识点, 此处判断一下
        show_concept_count = min(len(concepts_score), show_concept_count)
        title = ''  # '知识点变化图'
        legend_data = ['current', 'last']
        radar_indicator = [
            {'name': concepts_score[i][2], 'max': 1} for i in range(show_concept_count)
        ]
        series_name = 'last vs current'
        series_data = [
            # 每个legend_data元素值展示show_concept_count个
            {
                'value': [f'{concepts_score[j][i]:.2f}' for j in range(show_concept_count)],
                'name': legend_data[i]
            } for i in range(len(legend_data))
        ]

        chart_option = {
            'title': {
                'text': title
            },
            'tooltip': {
                # https://echarts.apache.org/examples/zh/editor.html?c=radar-multiple
                'trigger': 'axis',
            },
            'legend': {
                'orient': 'vertical',
                'x': 'left',  # 可设定图例在左、右、居中
                'y': 'top',  # 可设定图例在上、下、居中
                'padding': [20, 0, 0, 5],  # 可设定图例[距上方距离，距右方距离，距下方距离，距左方距离]
                'data': legend_data
            },
            'radar': {
                # shape: 'circle',
                'indicator': radar_indicator
            },
            'series': [
                {
                    'name': series_name,
                    'type': 'radar',
                    'data': series_data
                }
            ]
        }
        return chart_option

    def user_prob_pie_charts_option(self, prob_counts):
        # https://echarts.apache.org/examples/zh/editor.html?c=pie-nest
        # 下面这种极坐标图也可以, ABC就是['简单', '中等', '困难'], 外侧就是已做/未做简单题等等
        # https://echarts.apache.org/examples/zh/editor.html?c=bar-polar-stack-radial
        # prob_counts = [('简单', '中等', '困难'), 已做('简单', '中等', '困难')]
        legend_data = ['简单', '中等', '困难']
        series_inner_name = '题目类型'
        series_inner_data = [
            {'value': prob_counts[0][i], 'name': legend_data[i]} for i in range(len(legend_data))
            # {'value': prob_counts[0][2], 'name': legend_data[2], 'selected': True}
        ]
        series_outer_name = '用户做题'
        series_outer_data = [
            {'value': prob_counts[1][0], 'name': '已做简单题'},
            {'value': prob_counts[0][0] - prob_counts[1][0], 'name': '未做简单题'},
            {'value': prob_counts[1][1], 'name': '已做中等题'},
            {'value': prob_counts[0][1] - prob_counts[1][1], 'name': '未做中等题'},
            {'value': prob_counts[1][2], 'name': '已做困难题'},
            {'value': prob_counts[0][2] - prob_counts[1][2], 'name': '未做困难题'},
        ]

        chart_option = {
            'tooltip': {
                'trigger': 'item',
                'formatter': '{a} <br/>{b}: {c} ({d}%)'
            },
            'legend': {
                'data': legend_data
            },
            'series': [
                {
                    'name': series_inner_name,
                    'type': 'pie',
                    'selectedMode': 'single',
                    'radius': [0, '30%'],
                    'label': {
                        'position': 'inner',
                        'fontSize': 14
                    },
                    'labelLine': {
                        'show': False
                    },
                    'data': series_inner_data
                },
                {
                    'name': series_outer_name,
                    'type': 'pie',
                    'radius': ['45%', '60%'],
                    'labelLine': {
                        'length': 30
                    },
                    'label': {
                        'formatter': '{a|{a}}{abg|}\n{hr|}\n  {b|{b}：}{c}  {per|{d}%}  ',
                        'backgroundColor': '#F6F8FC',
                        'borderColor': '#8C8D8E',
                        'borderWidth': 1,
                        'borderRadius': 4,
                        'rich': {
                            'a': {
                                'color': '#6E7079',
                                'lineHeight': 22,
                                'align': 'center'
                            },
                            'hr': {
                                'borderColor': '#8C8D8E',
                                'width': '100%',
                                'borderWidth': 1,
                                'height': 0
                            },
                            'b': {
                                'color': '#4C5058',
                                'fontSize': 14,
                                'fontWeight': 'bold',
                                'lineHeight': 33
                            },
                            'per': {
                                'color': '#fff',
                                'backgroundColor': '#4C5058',
                                'padding': [3, 4],
                                'borderRadius': 4
                            }
                        }
                    },
                    'data': series_outer_data
                }
            ]
        }
        return chart_option

    def test_concept_pie_charts_option(self, concepts_score):
        # https://echarts.apache.org/examples/zh/editor.html?c=pie-legend
        # concepts_score: [(1,2,'name'), ...]
        series_itemStyle_borderRadius = len(concepts_score)
        legend_data = [concepts_score[i][2] for i in range(series_itemStyle_borderRadius)]
        series_name = '知识点'
        series_radius = '80%'  # 饼图的饼占元素大小
        series_data = [
            {'value': f'{concepts_score[i][0]:.2f}',
             'name': concepts_score[i][2]} for i in range(series_itemStyle_borderRadius)
        ]
        """"'toolbox': {
                        'show': True,
                        'feature': {
                            'mark': {'show': True},
                            'dataView': {'show': True, 'readOnly': False},
                            'restore': {'show': True},
                            'saveAsImage': {'show': True}
                        }
                    },"""
        chart_option = {
            'tooltip': {
                'trigger': 'item',
                'formatter': '{a}: {b}<br/>掌握情况: {c} (0-1) <br/>总体占比: {d}%'
            },
            'legend': {
                'type': 'scroll',
                'orient': 'vertical',
                'left': 0,
                'top': 20,
                'bottom': 20,
                'data': legend_data
            },
            'series': [
                {
                    'name': series_name,
                    'type': 'pie',
                    'radius': series_radius,
                    'emphasis': {
                        'itemStyle': {
                            'shadowBlur': 10,
                            'shadowOffsetX': 0,
                            'shadowColor': 'rgba(0, 0, 0, 0.5)'
                        }
                    },
                    'data': series_data
                }
            ]
        }
        return chart_option

    def user_concept_line_charts_option(self, u2cs_list, show_count=8):
        # https://echarts.apache.org/examples/zh/editor.html?c=area-stack
        # u2cs_list里有18个元素, 即18个知识点的按时间逆序的QuerySet
        # u2cs_list[0]是某个知识点的QuerySet
        title_text = ''  # '知识点掌握情况变化'
        legend_data = []
        # .strftime("%Y-%m-%d %H:%M:%S")是datetime类的格式化输出
        # 因为是日期逆序, 所以应该逆序索引show_count-i-1
        xAxis_data = [u2cs_list[0][show_count - i - 1].add_date.strftime("%m-%d %H:%M") for i in range(show_count)]
        # xAxis_data = [i for i in range(show_count)]
        series = [
            {
                'name': u2cs_list[j][0].concept.name,  # 获取当前concept的名字
                # 'name': j,  # 获取当前concept的名字
                'type': 'line',
                'stack': 'Total',
                'areaStyle': {},
                'emphasis': {
                    'focus': 'series'
                },
                # 'data': [i for i in range(show_count)]
                # 因为是日期逆序, 所以应该逆序索引show_count-i-1
                # 从每个QuerySet里按索引读取相应值
                'data': [f'{u2cs_list[j][show_count - i - 1].current_score:.2f}' for i in range(show_count)]
            } for j in range(len(u2cs_list))  # 一共构造len(u2cs_list)长度的字典(这么多根折线)
        ]

        chart_option = {
            'title': {
                'text': title_text,
                'left': 'center'
            },
            'tooltip': {
                'trigger': 'axis',
                'axisPointer': {
                    'type': 'cross',
                    'label': {
                        'backgroundColor': '#6a7985'
                    }
                }
            },
            'legend': {
                'data': legend_data
            },
            'grid': {
                'left': '3%',
                'right': '4%',
                'bottom': '3%',
                'containLabel': True
            },
            'xAxis': [
                {
                    'type': 'category',
                    'boundaryGap': False,
                    'data': xAxis_data
                }
            ],
            'yAxis': [
                {
                    'type': 'value'
                }
            ],
            'series': series
        }
        return chart_option

    def user_prob_polar_charts_option(self, prob_counts):
        # https://echarts.apache.org/examples/zh/editor.html?c=bar-polar-stack-radial
        # prob_counts = [('简单', '中等', '困难'), 已做('简单', '中等', '困难')]
        legend_data = ['简单', '中等', '困难']
        angleAxis_data = ['已做简单题', '未做简单题', '已做中等题',
                          '未做中等题', '已做困难题', '未做困难题']
        series_data = [
            # 每一个元素对应angleAxis_data的一个取值
            [prob_counts[1][0], prob_counts[0][0] - prob_counts[1][0], 0, 0, 0, 0],
            [0, 0, prob_counts[1][1], prob_counts[0][1] - prob_counts[1][1], 0, 0],
            [0, 0, 0, 0, prob_counts[1][2], prob_counts[0][2] - prob_counts[1][2]],
        ]
        series = [
            {
                'type': 'bar',
                # '已做简单题', '未做简单题'
                'data': series_data[i],
                'coordinateSystem': 'polar',
                'name': legend_data[i],
                'stack': 'a',
                'emphasis': {
                    'focus': 'series'
                }
            } for i in range(len(legend_data))
        ]

        chart_option = {
            'tooltip': {
                'trigger': 'item',
                # 'formatter': '{a} <br/>{b} : {c} ({d}%)',
                'formatter': '{b} : {c}'
            },
            'legend': {
                'show': True,
                'data': legend_data
            },
            'angleAxis': {
                'type': 'category',
                'data': angleAxis_data
            },
            'radiusAxis': {},
            'polar': {},
            'series': series
        }
        return chart_option

    def get_user_prob_polar_charts_data(self, user, concept_nid):
        # 根据concept_nid获取所有相关题目
        # 注意此处.values('problem_id')而不是.values('problem__id'),
        # 前者是获取当前table存储的problem的nid字段, 后者是problem的id字段
        p2cs_dict = Problems2Concepts.objects.filter(concept__nid=int(concept_nid)).values('problem_id')
        problems_nid = []
        for p2c in p2cs_dict:
            problems_nid.append(int(p2c['problem_id']))
        # print(problems_nid)
        # 获取当前知识点对应题目的难度分布图(0, '简单'),(1, '中等'),(2, '提高')
        ## 首先获得QuerySet, 然后再对QuerySet进行filter
        concept_problems = Problems.objects.filter(nid__in=problems_nid)
        # print(concept_problems)
        prob_0_count = concept_problems.filter(difficulty=0).count()
        prob_1_count = concept_problems.filter(difficulty=1).count()
        prob_2_count = concept_problems.filter(difficulty=2).count()
        # 获取用户已做对题目的难度分布图
        # 做对一次后续不在记录, 所以不用去除重复值
        concept_prs = ProblemRecords.objects.filter(user=user, score=1, problem__nid__in=problems_nid)
        # print(concept_prs)
        user_prob_0_count = concept_prs.filter(problem__difficulty=0).count()
        user_prob_1_count = concept_prs.filter(problem__difficulty=1).count()
        user_prob_2_count = concept_prs.filter(problem__difficulty=2).count()

        ### 应该是做题记录有问题(其实是一道题可以多次test), 筛选出来还多了, 所以此处在多余时就简单的重置一下
        if user_prob_0_count > prob_0_count:
            user_prob_0_count = prob_0_count
        if user_prob_1_count > prob_1_count:
            user_prob_1_count = prob_1_count
        if user_prob_2_count > prob_2_count:
            user_prob_2_count = prob_2_count
        # print(prob_0_count, prob_1_count, prob_2_count)
        # print(user_prob_0_count, user_prob_1_count, user_prob_2_count)

        prob_counts = [
            (prob_0_count, prob_1_count, prob_2_count),
            (user_prob_0_count, user_prob_1_count, user_prob_2_count)
        ]
        return prob_counts


class ReportView(ReportBaseView):
    # 为什么要移到此处api来使用, 不用django的模板语法,
    # 因为传入的concept name有问题, 多了&#x27;
    def get(self, request):
        # 返回给前端信息
        res = {
            'code': 404,
            'msg': "请求失败!",
            'data': None,  # 返回查询数据
        }
        data = self.get_report_info(request)
        res['data'] = data
        res['code'] = 200
        res['msg'] = "请求成功!"
        return JsonResponse(res)

    def get_report_info(self, request):
            # 把下面这些都写成函数分块, 按照前端传参需要获取相应值
            data = {
                'user_prob_pie_charts_option': None,
                'test_concept_radar_charts_option': None,
                'test_concept_pie_charts_option': None,
                'user_concept_line_charts_option': None,
                'user_prob_polar_charts_option': None,
                'prob_word_data': None,
                'center_word_data': None,
                'bottom_word_data': None,
            }
            # =======后面可以和problemset一样弄成api接口, 初始化时赋值======= #
            username = request.user.username
            if not username:
                return redirect("/login/")
            user = UserInfo.objects.get(username=username)

            """
            # =======获取当前用户最近测试报告======= #
            current_report_date = TestReport.objects.filter(user=user).aggregate(Max('test_date'))
            current_report = None
            if current_report_date:
                current_report = TestReport.objects.get(user=user, test_date=current_report_date['test_date__max'])
            if not current_report_date:  # 没有测试报告, 直接到欢迎界面
                return redirect('/welcome')
            
            
            # ===获取文字信息=== #
            # 获取测试题目数, 通过题目数, 正确率, 上一次测验正确率
            current_test = current_report.test
            
            test_prob_count = current_test.prob_count
            test_pass_prob_count = current_test.prob_pass_count
            test_pass_rate = 0
            if test_prob_count != 0:
                test_pass_rate = test_pass_prob_count / test_prob_count
            last_test_pass_rate = current_report.last_test_pass_rate
            # 提交最多最少题目, 提交几次通过
            # 这里面有些值可能为None, 就不显示了
            max_submit_prob = current_report.current_max_submit_prob
            min_submit_prob = current_report.current_min_submit_prob
            max_submit_prob_count = current_report.current_max_submit_prob_count
            min_submit_prob_count = current_report.current_min_submit_prob_count
            # 知识点相关数据 上一次测试掌握最好最坏知识点, 本次提升下降知识点
            last_max_concept = current_report.last_max_concept
            last_min_concept = current_report.last_min_concept
            current_improve_concept = current_report.current_improve_concept
            current_drop_concept = current_report.current_drop_concept
            
            # ===构造说明信息=== #
            # 构造测试通过率相关信息
            improve_pass_rate = test_pass_rate - last_test_pass_rate
            if improve_pass_rate > 0:
                improve_pass_str = f'提高了{improve_pass_rate:.2f}'
            elif improve_pass_rate == 0:
                improve_pass_str = '没有改变'
            else:
                improve_pass_str = f'降低了{-improve_pass_rate:.2f}'
            top_str_pass_html = f'<span>{username}</span>您好！这次的测试，您一共提交了<span>{test_prob_count}</span>道编程题目' \
                                f'，其中一共通过了其中的<span>{test_pass_prob_count}</span>道题目，正确率为<span>{test_pass_rate:.2f}</span>，' \
                                f'相比于上一次的练习记录正确率<span>{last_test_pass_rate:.2f}</span>，<span>{improve_pass_str}</span>。'
            # 构造测试提交题目数相关信息
            # 在problem.py里, 本次测试没有通过题目则max_submit_prob=min_submit_prob=None
            if not max_submit_prob or not min_submit_prob:
                top_str_prob_html = '<span>您此次测验一题都没通过！</span>'
            # 通过一题max_submit_prob==min_submit_prob
            elif max_submit_prob == min_submit_prob:
                top_str_prob_html = f'此次的测试过程中，您提交次数最多的题目是<span>{max_submit_prob}</span>，' \
                                    f'总共提交了<span>{max_submit_prob_count}</span>次才通过。'
            # 通过两题及以上
            else:
                top_str_prob_html = f'此次的测试过程中，您提交次数最多的题目是<span>{max_submit_prob}</span>，' \
                                    f'总共提交了<span>{max_submit_prob_count}</span>次才通过。相比之下，您提交次数最少的' \
                                    f'题目是<span>{min_submit_prob}</span>，总共提交了<span>{min_submit_prob_count}</span>次就通过了。'
            # 构造掌握知识点相关信息
            max_concept_str = '，'
            if last_max_concept:  # 如果有最好的掌握知识点
                max_concept_str += f'在上一次测试过程中，您对知识点<span>{last_max_concept}</span>的掌握情况最好'
                if last_min_concept:  # 同时有最差的掌握知识点
                    max_concept_str += f'，但对知识点<span>{last_min_concept}</span>的掌握仍有所欠缺。'
                else:  # 同时没有最差的掌握知识点
                    max_concept_str += '。'
            else:  # 如果没有最好的掌握知识点
                if last_min_concept:  # 同时有最差的掌握知识点
                    max_concept_str += f'在上一次测试过程中，您对知识点<span>{last_max_concept}</span>的掌握情况有所欠缺。'
            improve_concept_str = ''
            improve_drop_str = ''
            if current_improve_concept:  # 如果有知识点有提升
                improve_concept_str = f'您在<span>{current_improve_concept}</span>这些知识点的掌握情况上有所<span>提升</span>，'
            if current_drop_concept:  # 如果有知识点有下降
                improve_drop_str = f'您在<span>{current_drop_concept}</span>这些知识点的掌握情况上有所<span>下降</span>，'
            top_str_concept_html = f'本门课程一共<span>{18}</span>个知识点{max_concept_str}经过这一次的测试，{improve_concept_str}' \
                                   f'{improve_drop_str}希望此次练习对您以后的学习有所帮助。'
            data['prob_word_data'] = f'<p>{top_str_pass_html}</p>' \
                                   f'<p>{top_str_prob_html}</p>' \
                                   f'<p>{top_str_concept_html}</p>'
            """

            # =======获取Echarts图表数据======= #
            # ===获取当前用户知识点掌握情况与上一次比较变化=== #
            # 同一次知识点掌握情况写入时间相同, 所以根据时间获取就可以了
            current_u2c_date = Users2Concepts.objects.filter(user=user).aggregate(Max('add_date'))
            current_u2cs = None
            if current_u2c_date:
                current_u2cs = Users2Concepts.objects.filter(user=user, add_date=current_u2c_date['add_date__max'])
            if not current_u2cs:  # 没有掌握情况, 直接到欢迎界面
                return redirect('/welcome')
            concepts_score = []
            for u2c in current_u2cs:
                concept_name = u2c.concept.name
                # concept_name = concept_name.strip().replace('&#x27;', '')
                # concept_name = f'{concept_name}'
                # print(concept_name)
                # print(type(concept_name))
                if u2c.last_score is None:  # =====last_score没有默认值, 第一次为Null, 下面画图会出问题, 此处修正一下===== #
                    u2c.last_score = 0
                concepts_score.append((u2c.current_score, u2c.last_score, concept_name))
            # print(concepts_score)
            # 按照list中元组第一个元素逆序排序, 会同时修改concepts_score列表
            concepts_score.sort(key=lambda x: -x[0])
            # print(concepts_score)
            # [(1,2,'name'), ...]
            data['test_concept_radar_charts_option'] = self.test_concept_radar_charts_option(concepts_score)
            # print(data['test_concept_radar_charts_option'])

            # ===获取当前用户已做题目分布图=== #
            # 获取题目的难度分布图(0, '简单'),(1, '中等'),(2, '提高')
            prob_0_count = Problems.objects.filter(difficulty=0).count()
            prob_1_count = Problems.objects.filter(difficulty=1).count()
            prob_2_count = Problems.objects.filter(difficulty=2).count()
            # 获取用户已做对题目的难度分布图
            # 做对一次后续不在记录, 所以不用去除重复值
            user_prob_0_count = ProblemRecords.objects.filter(user=user, score=1, problem__difficulty=0).count()
            user_prob_1_count = ProblemRecords.objects.filter(user=user, score=1, problem__difficulty=1).count()
            user_prob_2_count = ProblemRecords.objects.filter(user=user, score=1, problem__difficulty=2).count()

            prob_counts = [
                (prob_0_count, prob_1_count, prob_2_count),
                (user_prob_0_count, user_prob_1_count, user_prob_2_count)
            ]
            # 已做题目分布饼图的两种形式
            data['user_prob_pie_charts_option'] = self.user_prob_pie_charts_option(prob_counts)

            # 已做题目根据知识点分布图
            concept = Concepts.objects.all()[0]
            prob_counts = self.get_user_prob_polar_charts_data(user, concept.nid)
            data['user_prob_polar_charts_option'] = self.user_prob_polar_charts_option(prob_counts)

            # print(prob_0_count, user_prob_0_count)
            # print(prob_1_count, user_prob_1_count)
            # print(prob_2_count, user_prob_2_count)

            # ===获取当前用户知识点掌握情况占比图=== #
            data['test_concept_pie_charts_option'] = self.test_concept_pie_charts_option(concepts_score)

            # ===获取当前用户知识点掌握情况随时间变化图=== #
            concepts = Concepts.objects.all()
            u2cs_list = []
            show_count = 12  # 获取12次的知识点变化情况(一共是12*18个知识点)
            # print(concepts)
            # https://blog.csdn.net/weixin_42038955/article/details/115797352
            start_date = datetime(2022, 1, 1, 0, 0, 0)
            # RuntimeWarning: DateTimeField Users2Concepts.add_date received a naive datetime (2022-01-01 00:00:00) while time zone support is active.
            #   RuntimeWarning)  https://www.codenong.com/21038881/
            start_date = timezone.make_aware(start_date, timezone.get_current_timezone())
            min_u2c = show_count
            for concept in concepts:
                # 按照时间逆序排序  add_date__gt=start_date表示时间大于这个时间的
                u2cs = Users2Concepts.objects.filter(user=user, concept=concept, add_date__gt=start_date).order_by('-add_date')[:show_count]
                # 知识点掌握情况是同时写入的, 所以一般不用担心每个u2cs长度问题
                if len(u2cs) == 0:  # 有一个知识点没被KT输出掌握情况, 过滤掉
                    continue  # 不过滤的话, 最后一个QuerySet为空, 遍历有问题
                if len(u2cs) < min_u2c:  # 多余的判断逻辑, 之前第18个知识点一直没有写入, 导致其不够12条记录, 与其他的不一样
                    min_u2c = len(u2cs)
                u2cs_list.append(u2cs)
            # print(u2cs_list)
            # 最后再给show_count重新赋值, 避免当前用户的u2cs记录不足show_count个, 后面报错
            show_count = min(len(u2cs_list[0]), min_u2c)
            data['user_concept_line_charts_option'] = self.user_concept_line_charts_option(u2cs_list, show_count=show_count)

            # =======构造推荐题目======= #
            # 因为直接构造的带有a标签的HTML, VUE插值不容易支持, 在app01.view的report里写, 用Django的模板语法

            return data


class ReportConceptView(ReportBaseView):
    def get(self, request):
        # 返回给前端信息
        res = {
            'code': 404,
            'msg': "请求失败!",
            'data': None,  # 返回查询数据
        }
        Type = request.GET.get('type', None)
        if Type == 'init':
            options = []
            concepts = Concepts.objects.all()
            for concept in concepts:
                option = {'value': concept.nid, 'label': concept.name}
                options.append(option)
            res['data'] = options
            res['code'] = 200
            res['msg'] = "请求成功!"
            return JsonResponse(res)

        return JsonResponse(res)

    def post(self, request):
        # 返回给前端信息
        res = {
            'code': 404,
            'msg': "请求失败!",
            'data': None,  # 返回查询数据
        }
        username = request.user.username
        if not username:
            return redirect("/login/")
        user = UserInfo.objects.get(username=username)

        # 在app01的middleware_decode.py里拦截了post请求, 把参数放在了data里
        concept_nid = request.data.get('concept_nid', None)

        prob_counts = self.get_user_prob_polar_charts_data(user, concept_nid)

        res['code'] = 200
        res['msg'] = "请求成功!"
        res['data'] = self.user_prob_polar_charts_option(prob_counts)
        return JsonResponse(res)


class ClockCardInfoView(View):
    def get(self, request):
        # 返回给前端信息
        res = {
            'code': 404,
            'msg': "请求失败!",
            'data': None,  # 返回查询数据
        }

        # # =============获取ip与地址信息============= #
        # # https://blog.csdn.net/sxf1061700625/article/details/123526907
        # # 当前 IP：58.240.39.252  来自于：中国 江苏 南京  联通
        # qheaders = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64)", "Connection": "close"}
        # ip_location = requests.get('https://myip.ipip.net', headers=qheaders, verify=False).text
        # ip = re.findall(r'(\d+\.\d+\.\d+\.\d+)', ip_location)
        # ip = ip[0] if ip else 'NO IP'
        # # 把'中国'及前面的字符串切掉, 以及最后的'  联通'切掉, 然后删除省份, 把地址中的城市提取出来
        # location = ip_location[ip_location.find('中国')+3:-5][-2:]
        # # =============获取天气信息============= #
        # # https://www.jianshu.com/p/efbf94a10c4a/
        # weatherJsonUrl = f"http://wthrcdn.etouch.cn/weather_mini?city={location}"  # 将链接定义为一个字符串
        # response = requests.get(weatherJsonUrl, headers=qheaders, verify=False)  # 获取并下载页面，其内容会保存在respons.text成员变量里面
        # response.raise_for_status()  # 这句代码的意思如果请求失败的话就会抛出异常，请求正常就上面也不会做
        # # 将json文件格式导入成python的格式
        # weatherData = json.loads(response.text)
        #
        # weather_dict = dict()
        # weather_dict['high'] = weatherData['data']['forecast'][0]['high']
        # weather_dict['low'] = weatherData['data']['forecast'][0]['low']
        # weather_dict['type'] = weatherData['data']['forecast'][0]['type']
        # # weather_dict['fengxiang'] = weatherData['data']['forecast'][0]['fengxiang']
        # # weather_dict['ganmao'] = weatherData['data']['ganmao']
        # # print(weather_dict)
        #
        #
        # data ={
        #         'whether': weather_dict['type'],
        #         'temperature': f'{weather_dict["high"][3:]}/{weather_dict["low"][3:]}',
        #         'humidity': '67%',
        #         'ip': ip,
        #         'location': location,
        #     }
        data = {
            'whether': '晴天',
            'temperature': '35℃/27℃',
            'humidity': '67%',
            'ip': '172.21.228.127',
            'location': '南京',
        }
        res['data'] = data
        res['code'] = 200
        res['msg'] = "请求成功!"
        return JsonResponse(res)


class SimulationProbNidView(View):
    def get(self, request):
        # 返回给前端信息
        res = {
            'code': 404,
            'msg': "请求失败!",
            'data': None,  # 返回查询数据
        }
        username = request.user.username
        if not username:
            return redirect("/login/")
        user = UserInfo.objects.get(username=username)

        # 获取到一个数据库表Object, 它的dataSimulationProbNid字段存入的是一个list的str, 用eval再变回list
        data = eval(ShareData.objects.get(user=user).dataSimulationProbNid)
        print(data)
        print(type(data))

        res['data'] = data
        res['code'] = 200
        res['msg'] = "请求成功!"
        return JsonResponse(res)