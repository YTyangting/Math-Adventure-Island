import random

from django import forms
from django.contrib import auth
from django.views import View
from django.http import JsonResponse
import os

from app01.utils.get_prob_name import get_prob_dict_with_json, get_diff_with_csv, get_concepts_with_csv, \
    get_problems_concepts_with_csv, is_problem_has_html_file
from app01.models import UserInfo, ProblemsTest, Problems, ProblemsRecommendation, Concepts, Problems2Concepts


class AddProblemTable(View):
    def get(self, request):
        # 返回给前端信息
        res = {
            'code': 200,
            'msg': "添加成功!",
        }
        # 在auth.login(request, user)中是用request.user = user
        # 把user加入request中的, 所以此处应该也是用成员变量方式获取
        username = request.user.username

        if not username:
            res['msg'] = "请先登录!"
            return JsonResponse(res)

        if request.GET.get('type', None) == 'problems':
            self.add_problem_table()
            return JsonResponse(res)

        if request.GET.get('type', None) == 'problems_alter':
            self.alter_problem_table()
            return JsonResponse(res)

        if request.GET.get('type', None) == 'problem_test':
            self.add_problem_test_table()
            return JsonResponse(res)

        if request.GET.get('type', None) == 'problems_recommendation':
            self.add_problems_recommendation_table(username)
            return JsonResponse(res)

        if request.GET.get('type', None) == 'concepts':
            self.add_concepts_table()
            return JsonResponse(res)

        if request.GET.get('type', None) == 'problems_concepts':
            self.add_problems_concepts_table()
            return JsonResponse(res)

        if request.GET.get('type', None) == 'all':
            self.add_problem_table()
            self.add_problem_test_table()
            self.add_problems_recommendation_table(username)
            self.add_concepts_table()
            self.add_problems_concepts_table()
            return JsonResponse(res)

        # self.add_problem_table()
        res['code'] = 201
        res['msg'] = '您没有执行任何操作'
        return JsonResponse(res)

    def add_problem_table(self, root_path=None, json_path_name=None, prob_path_name=None):
        if not root_path:
            root_path = r'./templates/my_tag/'  # 路径都是相对于manage.py来说的
        if not json_path_name:
            json_path_name = 'prob_json'
        if not prob_path_name:
            prob_path_name = 'prob'
        prob_type_list, prob_dict = get_prob_dict_with_json(os.path.join(root_path, json_path_name))

        # 读取diff.csv相应值的条件字典
        diff_cond = {'category': None, 'id': None}
        # print(prob_type_list)  # [1, 13, 6, 7, 8, 9]
        # print(prob_dict[1])  # 一个字典list, [{'id': 1000, 'title': '时间类Time', 'desc':, {}, {}]
        # 初始化
        Problems.objects.all().delete()

        for category in prob_type_list:
            # i = 0
            for prob in prob_dict[category]:
                prob_id = prob['id']
                diff_cond['category'] = category
                diff_cond['id'] = prob_id
                # print(diff_cond)
                diff = get_diff_with_csv(cond=diff_cond)
                # csv里没有难度的题目, 应该清洗了
                if not diff:
                    continue
                # 题目没有相应的html文件, 应该清洗了  =======这个判断还有问题
                if not is_problem_has_html_file(category, prob_id):
                    continue
                # 给出难度对应的等级  越小越难, 简单-'0' 中等-'1' 困难-'2', 前端根据数值判断来显示
                if diff < 0.3:
                    diff_int = 2
                elif diff < 0.7:
                    diff_int = 1
                else:
                    diff_int = 0
                # html_file_name = f'{category}_{prob_id}.html'
                # html_path = os.path.join(root_path, prob_path_name, html_file_name)
                Problems.objects.create(category=category,
                                        id=prob['id'],
                                        difficulty=diff_int,
                                        origin='无',
                                        title=prob['title'],
                                        desc=prob['desc'],
                                        input=prob['input'],
                                        output=prob['output'],
                                        html_path=None,
                                        )
                # i += 1
                # if i == 3:
                #     break

        # obj = Problems.objects.create(category=prob_type_list[0],
        #                               id=prob_dict[prob_type_list[0]][0]['id'],
        #                               title=prob_dict[prob_type_list[0]][0]['title'],
        #                               desc=prob_dict[prob_type_list[0]][0]['desc'],
        #                               input=prob_dict[prob_type_list[0]][0]['input'],
        #                               output=prob_dict[prob_type_list[0]][0]['output'],
        #                               )
        # print(obj)

    def add_problem_test_table(self):
        # 初始化
        ProblemsTest.objects.all().delete()

        prob_query = Problems.objects.all()
        if len(prob_query) == 0:
            return None
        test_prob_index_list = random.sample(range(0, len(prob_query)), 15)
        for i in test_prob_index_list:
            category = random.choice([1, 2])  # models里ProblemsTest的choices用1表示补弱2表示提高
            # print(category)
            ProblemsTest.objects.create(category=category,
                                        problem_id=prob_query[i].nid)

    def add_problems_recommendation_table(self, username):
        # 初始化
        ProblemsRecommendation.objects.all().delete()

        user = UserInfo.objects.get(username=username)
        test_prob_query = ProblemsTest.objects.all()
        # 通过外键获取的是对象, 而不是外键nid
        # print(type(test_prob_query[0]))   # <class 'app01.models.ProblemsTest'>
        # print(type(test_prob_query[0].problem))  # <class 'app01.models.Problems'>
        if len(test_prob_query) == 0:
            return None
        for test_prob in test_prob_query:
            category = random.choice([1, 2])  # models里ProblemsTest的choices用1表示补弱2表示提高
            ProblemsRecommendation.objects.create(
                user=user,
                # 通过外键获取的是对象, 而不是外键nid, 所以此处赋值后面有_id
                # 而且用的是测试试题表对象赋值, 若是用Problems对象, 直接.nid
                problem_id=test_prob.problem_id,
                category=category, )

    def add_concepts_table(self):
        # 初始化
        Concepts.objects.all().delete()

        concepts_name, concepts_id = get_concepts_with_csv('name_id')
        for i in range(len(concepts_name)):
            Concepts.objects.create(
                name=concepts_name[i],
                id=concepts_id[i],
            )

    def add_problems_concepts_table(self):
        # 初始化
        Problems2Concepts.objects.all().delete()

        probs = Problems.objects.all()
        cond = {'category': None, 'id': None}
        for prob in probs:
            # ======== 主义题目表里面category和id都是str类型的 ======== #
            cond['category'] = int(prob.category)
            cond['id'] = int(prob.id)
            # 首先通过题目的id和category获取problems.csv里对应的知识点id
            concept_csv_id_list = get_problems_concepts_with_csv(cond=cond)
            # 如果有这个题目知识点关系, 有的题目在csv里没有对应的知识点
            if concept_csv_id_list:
                for concept_csv_id in concept_csv_id_list:
                    # 通过知识点id, 获取concepts.csv里对应的知识点名称
                    concept_name = get_concepts_with_csv({'id': concept_csv_id})
                    # 根据知识点名称获取知识点nid
                    concept = Concepts.objects.get(name=concept_name)
                    Problems2Concepts.objects.create(
                        problem=prob,
                        concept=concept,
                    )

    def alter_problem_table(self):
        prob_list = [(1, 1001), (1, 1002), (1, 1003), (1, 1004), (1, 1005), (1, 1006), (1, 1007), (1, 1008), (1, 1009),
                     (1, 1010),
                     (1, 1011), (1, 1012), (1, 1013), (1, 1014), (1, 1015), (1, 1016), (1, 1017), (1, 1018), (1, 1019),
                     (1, 1020),
                     (1, 1021), (1, 1022), (1, 1023), (1, 1025), (1, 1026), (1, 1028), (1, 1030), (1, 1031), (1, 1032),
                     (1, 1033),
                     (1, 1034), (1, 1035), (1, 1036), (1, 1044), (1, 1045), (1, 1046), (1, 1047), (1, 1062), (1, 1063),
                     (1, 1064),
                     (1, 1065), (1, 1066), (1, 1068), (1, 1070), (1, 1072), (1, 1074), (1, 1075), (1, 1076), (1, 1077),
                     (1, 1081),
                     (1, 1087), (1, 1088), (1, 1089), (1, 1090), (1, 1091), (1, 1092), (1, 1093), (1, 1094), (1, 1095),
                     (1, 1096),
                     (1, 1097), (1, 1098), (1, 1099), (1, 1100), (1, 1101), (1, 1107), (1, 1108), (1, 1114), (1, 1115),
                     (1, 1116),
                     (1, 1117), (1, 1119), (1, 1120), (1, 1121), (1, 1122), (1, 1123), (1, 1126), (1, 1128), (1, 1129),
                     (1, 1131),
                     (1, 1132), (1, 1133), (1, 1134), (1, 1135), (1, 1136), (1, 1137), (1, 1138), (1, 1139), (1, 1140),
                     (1, 1141),
                     (1, 1142), (1, 1143), (1, 1145), (1, 1146), (1, 1147), (1, 1148), (1, 1149), (1, 1150), (1, 1151),
                     (1, 1152),
                     (1, 1153), (1, 1154), (1, 1160), (1, 1168), (1, 1169), (1, 1170), (1, 1171), (1, 1173), (1, 1175),
                     (1, 1176),
                     (1, 1177), (1, 1178), (1, 1179), (1, 1180), (1, 1182), (1, 1183), (1, 1190), (1, 1192), (1, 1193),
                     (1, 1194),
                     (1, 1196), (1, 1197), (1, 1201), (1, 1204), (1, 1207), (1, 1211), (1, 1212), (6, 1000), (6, 1001),
                     (6, 1002),
                     (6, 1005), (6, 1006), (6, 1007), (6, 1008), (6, 1009), (6, 1010), (6, 1011), (6, 1012), (6, 1013),
                     (6, 1014),
                     (6, 1019), (6, 1020), (6, 1021), (6, 1024), (6, 1025), (6, 1026), (6, 1034), (6, 1045), (6, 1046),
                     (6, 1047),
                     (6, 1048), (6, 1049), (6, 1050), (6, 1051), (6, 1052), (6, 1053), (6, 1054), (6, 1055), (6, 1056),
                     (6, 1057),
                     (6, 1058), (6, 1059), (6, 1060), (6, 1061), (6, 1062), (6, 1063), (6, 1064), (6, 1065), (6, 1066),
                     (6, 1067),
                     (6, 1068), (6, 1069), (6, 1070), (6, 1071), (6, 1072), (6, 1073), (6, 1074), (6, 1075), (6, 1076),
                     (6, 1077),
                     (6, 1079), (6, 1084), (6, 1085), (6, 1088), (6, 1089), (6, 1090), (6, 1091), (6, 1092), (6, 1093),
                     (6, 1100),
                     (6, 1101), (6, 1108), (6, 1110), (7, 1000), (7, 1001), (7, 1003), (7, 1004), (7, 1005), (7, 1006),
                     (7, 1007),
                     (7, 1008), (7, 1009), (7, 1011), (7, 1012), (7, 1013), (7, 1014), (7, 1015), (7, 1017), (7, 1018),
                     (7, 1019),
                     (7, 1020), (7, 1041), (7, 1042), (7, 1043), (7, 1044), (7, 1047), (7, 1048), (8, 1000), (8, 1003),
                     (8, 1004),
                     (8, 1005), (8, 1006), (8, 1007), (8, 1008), (8, 1009), (8, 1010), (8, 1011), (8, 1012), (8, 1013),
                     (8, 1015),
                     (8, 1016), (8, 1017), (8, 1018), (8, 1019), (8, 1022), (8, 1023), (8, 1025), (8, 1026), (8, 1027),
                     (8, 1028),
                     (9, 1006), (9, 1008), (9, 1009), (9, 1011), (9, 1012), (9, 1014), (9, 1016), (9, 1018), (9, 1020),
                     (9, 1023),
                     (9, 1024), (9, 1025), (9, 1063), (13, 1000), (13, 1001), (13, 1002), (13, 1003), (13, 1004),
                     (13, 1005), (13, 1006),
                     (13, 1007), (13, 1008), (13, 1009), (13, 1010), (13, 1011), (13, 1012), (13, 1013), (13, 1014),
                     (13, 1015), (13, 1016),
                     (13, 1017), (13, 1018), (13, 1019), (13, 1021), (13, 1027)]
        problems = Problems.objects.all()
        for problem in problems:
            prob = (int(problem.category), int(problem.id))
            if prob not in prob_list:
                Problems.objects.filter(nid=problem.nid).delete()
