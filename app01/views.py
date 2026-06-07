from django.shortcuts import render, HttpResponse, redirect
from app01.utils.random_code import random_code
from django.contrib import auth
# from rest_framework import viewsets
from app01.models import Problems, ProblemsTest, ProblemsRecommendation, Problems2Concepts, UserInfo, Users2Concepts, \
    TestReport, ShareData
from app01.utils.pagination import Pagination
import random
from django.db.models import Max

# Create your views here.


def login(request):
    return render(request, 'login.html')


def get_random_code(request):
    # fp = open(r'D:\pyProject\Pycharm\DeepLearning\blog_local\app01\utils\new_img.png', 'rb')
    # data = fp.read()
    # fp.close()
    data, valid_code = random_code()
    # 把验证码写入session, 以便前端校验
    request.session['valid_code'] = valid_code
    return HttpResponse(data)


def logout(request):
    # 注销操作
    auth.logout(request)
    return redirect('/')


def problem(request, nid):
    username = request.user.username
    if not username:
        return redirect('/')
    user = UserInfo.objects.get(username=username)
    # html_name = r'my_tag/prob/' + nid + '.html'
    # 根据nid获取题目
    prob = Problems.objects.get(nid=nid)
    if not prob:  # 不存在这道题
        return redirect('/problemset/')  # 前面加个/就是直接从根目录重定向了
    # 根据题目nid获取相应的知识点
    #problem_concepts = Problems2Concepts.objects.filter(problem_id=nid)
    #html_name = f"my_tag/prob/{prob.category}_{prob.id}.html"


    # if not os.path.exists(html_name):  # 不存在这个html
    #     return redirect('dl_index/')

    # ===== 根据GET参数不同, 上一题下一题范围就应该不同(整个题库里还是只在推荐题目里) ===== #

    url_from = request.GET.get('from', None)
    prob_list = []
    now_prob_index = 0
    if not url_from:
        return redirect('/dl_index/')  # 这个重定向有问题以后再考虑吧
    if url_from == 'problemset':
        prob_list = list(Problems.objects.all())
        now_prob_index = prob_list.index(prob)
    elif url_from == 'recommend':
        # 因为通过ProblemsRecommendation得到的不是prob的object,
        # 不知道如何通过外键直接获取相应的object
        prob_cond_list = list(ProblemsRecommendation.objects.filter(user=user))
        for prob_cond in prob_cond_list:
            prob_list.append(prob_cond.problem)
        now_prob_index = prob_list.index(prob)
    else:
        return redirect('/dl_index/')
    # ===== 根据GET参数不同, 上一题下一题范围就应该不同(整个题库里还是只在推荐题目里) ===== #
    max_index = len(prob_list) - 1
    prev_prob = ''
    next_prob = ''
    prev_html_name = '#'
    next_html_name = '#'
    if now_prob_index != 0:
        prev_prob = prob_list[now_prob_index - 1]
        # 这两个是a标签的跳转url, 不是{% include html_name %}
        prev_html_name = f"problemset/{prev_prob.nid}?from={url_from}#problem_position"
    if now_prob_index != max_index:
        next_prob = prob_list[now_prob_index + 1]
        next_html_name = f"problemset/{next_prob.nid}?from={url_from}#problem_position"

    # 传入题目的nid方便ProblemExecuteBaseView写入做题记录表
    prob_nid_list = [nid]  # list形式, 方便前端统一
    desc = prob.desc
    id = prob.id
    return render(request, 'problem.html', locals())


def dl_index(request):
    username = request.user.username
    if not username:
        return redirect('/')
    user = UserInfo.objects.get(username=username)

    prob_query = ProblemsRecommendation.objects.filter(user_id=user)
    count = len(prob_query)

    query_params = request.GET.copy()
    pager = Pagination(
            current_page=request.GET.get('page'),
            all_count=count,
            base_url=request.path_info,
            query_params=query_params,
            per_page=5,
            pager_page_count=7
        )
    # print(pager.start, pager.end, pager.page_html())

    prob_query = prob_query[pager.start:pager.end]
    return render(request, 'dl_index.html', locals())


def problemset(request):
    return render(request, 'problemset.html', locals())
def newtest(request):
    return render(request, 'newtest.html', locals())

def test(request):
    username = request.user.username
    if not username:
        return redirect("/login/")
    user = UserInfo.objects.get(username=username)
    max_test_prob_count = 15  # 最多测试题目数量

    test_type = request.GET.get('type', None)
    test_prob_nid_list = []
    if test_type == 'weakness' or test_type == 'improve':
        # 获取当前用户掌握最差的知识点对应的简单题/中等题的problem的nid
        # 获取当前用户掌握最差的知识点对应的中等题/困难题的problem的nid
        select_concepts = get_concepts(user=user, test_type=test_type)
        # ===== 不同题目对应概念可能有重复, 所以这里根据概念得到的test_prob_nid_list可能重复===== #
        # ===== 重复就导致test_prob_nid_list与prob_query长度不一样, 只需要依照prob_query长度即可===== #
        p2cs = []
        if select_concepts:
            p2cs = Problems2Concepts.objects.filter(concept__in=select_concepts)

        for p2c in p2cs:
            test_prob_nid_list.append(p2c.problem.nid)
       #  # [3307, 3371, 3371, 3391, ...]
    else:  # test_type == 'common'
        # 获取测试表所有problem的nid
        test_prob_nid_dict = ProblemsTest.objects.filter(testCategory=1).values('problem_id')
        # print(test_prob_nid_list)  # [{'problem_id': 3283}, ...]
        for prob_nid in test_prob_nid_dict:
            test_prob_nid_list.append(prob_nid['problem_id'])

    count = len(test_prob_nid_list)
    # print(test_prob_nid_list)
    # print(len(test_prob_nid_list))
    # 根据test表里problem的nid取出相应的题目
    prob_query = []
    if test_prob_nid_list:
        diff = [0, 1, 2]
        # if test_type == 'weakness':
        #     diff = [0, 1]  # 补弱推荐相应知识点简单题/中等题
        # elif test_type == 'improve':
        #     diff = [1, 2]  # 提高推荐相应知识点中等题/困难提
        prob_query = Problems.objects.filter(nid__in=test_prob_nid_list, difficulty__in=diff)
        prob_query = Problems.objects.filter(nid__in=test_prob_nid_list)
    # print(prob_query)
    # print(len(prob_query))
    # 这里又给count赋值成prob_query长度,
    # =====(原因见上面p2cs)是因为不知道为什么len(test_prob_nid_list)和len(prob_query)长度不同===== #
    if len(prob_query) > max_test_prob_count:
        # 如果查询的题目长度超过15题, 则随机采样15道题目
        prob_index_list = random.sample(range(0, len(prob_query)), max_test_prob_count)
        sample_prob_query_list = []
        for i in prob_index_list:
            sample_prob_query_list.append(prob_query[i])
        prob_query = sample_prob_query_list
    count = len(prob_query)

    test_prob_dict_list = []  # 记录下标、数据等
    index_list = []  # 只记录下标用于界面右侧题号展示
    # prob_nid_list其实等价于上面的test_prob_nid_list, 但我懒得改了
    prob_nid_list = []  # 传入题目的nid方便ProblemExecuteBaseView写入做题记录表

    for i in range(count):
        # 根据题目nid获取相应的知识点
        problem_concepts = Problems2Concepts.objects.filter(problem_id=prob_query[i].nid)
        test_prob_dict = {'index': i,
                          'prob': prob_query[i],
                          'problem_concepts': problem_concepts}  # 记录每道题目知识点
        test_prob_dict_list.append(test_prob_dict)
        index_list.append(i)
        prob_nid_list.append(prob_query[i].nid)
    # print(test_prob_dict_list[0])
    return render(request, 'test.html', locals())


def get_concepts(user=None, test_type='weakness'):
    last_users2concept = []
    last_users2concept_date = Users2Concepts.objects.filter(user=user).aggregate(Max('add_date'))
    if last_users2concept_date:  # 如果有记录, 就把当前concept在数据库中最近的记录值获取到
        last_users2concept = Users2Concepts.objects.filter(user=user, add_date=last_users2concept_date['add_date__max'])
    print(last_users2concept)
    concept_score = []  # 知识点掌握score列表
    concepts = []  # 知识点列表
    for users2concept in last_users2concept:

        concept_score.append(users2concept.current_score)
        concepts.append(users2concept.concept)
    if len(concept_score) == 0:
        return None
    elif len(concept_score) <= 3:
        return concepts  # 不足三个知识点, 就全部返回
    else:
        if test_type == 'weakness':
            find_f = max
            fill_value = float('-inf')
        elif test_type == 'improve':
            find_f = min
            fill_value = float('inf')
        else:
            return None
        # 找到前三个最大/小值, score在0-1之间
        max1 = find_f(concept_score)  # 最大值
        max1_idx = concept_score.index(max1)  # 最大值索引
        concept_score[max1_idx] = fill_value
        max2 = find_f(concept_score)  # 最大值
        max2_idx = concept_score.index(max2)  # 最大值索引
        concept_score[max2_idx] = fill_value
        max3 = find_f(concept_score)  # 最大值
        max3_idx = concept_score.index(max3)  # 最大值索引
        return concepts[max1_idx], concepts[max2_idx], concepts[max3_idx]


def welcome(request):
    return render(request, 'welcome.html', locals())


def report(request):
    """
    这里report首先获取最近的测试报告表, 根据测试报告表获取测试记录表数据
    因为一次测验完成, 一定会同时生成测试记录和测试报告的
    ================这里有个问题, 如果我不提交试卷,   ##### 算是解决了, 给testrecord表加了个字段, 判断当前测验记录有效还是无效
                    应该有判断删除生成的临时测试数据才对
                    (这些数据是因为只要提交就会生成testrecord)===========
    :param request:
    :return:
    """
    # =======此处构造prob_word_data是因为VUE插值不能很好的现实HTML元素, Django的可以======= #
    # ======另一种办法就是后端传值, 前端构造相应的word, 不过很麻烦======= #
    username = request.user.username
    if not username:
        return redirect("/login/")
    user = UserInfo.objects.get(username=username)

    # =======获取当前用户最近测试报告======= #
    # =======测试报告表只会记录有效测验记录, 所以这里就不用判断category=1了======= #
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
    if last_test_pass_rate is None:  # 第一次测验
        top_str_pass_html = f'<span>{username}</span>您好！这是您的第一次测试，您一共提交了<span>{test_prob_count}</span>道编程题目' \
                            f'，其中一共通过了其中的<span>{test_pass_prob_count}</span>道题目，正确率为<span>{test_pass_rate:.2f}</span>。'
    else:
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
        # 此处不用get改用filter, 害怕重名题目
        prob = Problems.objects.filter(id=max_submit_prob)
        prob = prob[0]
        top_str_prob_html = ''
        if max_submit_prob_count <= 3:  # 提交次数小于三次
            top_str_prob_html = f'此次的测试过程中，您只通过了一道题目：<span>' \
                                f'<a href="/problem/{prob.nid}?from=problemset#problem_position">' \
                                f'{prob.id}</a></span>，' \
                                f'总共提交了<span>{max_submit_prob_count}</span>次就通过了。'
        else:  # 提交次数大于三次
            top_str_prob_html = f'此次的测试过程中，您只通过了一道题目：<span>' \
                            f'<a href="/problem/{prob.nid}?from=problemset#problem_position">' \
                            f'{prob.id}</a></span>，' \
                            f'总共提交了<span>{max_submit_prob_count}</span>次才通过。'
    # 通过两题及以上
    else:
        # 此处不用get改用filter, 害怕重名题目
        prob_max = Problems.objects.filter(id=max_submit_prob)
        prob_max = prob_max[0]
        prob_min = Problems.objects.filter(id=min_submit_prob)
        prob_min = prob_min[0]
        top_str_prob_html = f'此次的测试过程中，您提交次数最多的题目是<span>' \
                            f'<a href="/problem/{prob_max.nid}?from=problemset#problem_position">' \
                            f'{prob_max.id}</a></span>，' \
                            f'总共提交了<span>{max_submit_prob_count}</span>次才通过。相比之下，您提交次数最少的' \
                            f'题目是<span>' \
                            f'<a href="/problem/{prob_min.nid}?from=problemset#problem_position">' \
                            f'{prob_min.id}</a></span>，' \
                            f'总共提交了<span>{min_submit_prob_count}</span>次就通过了。'
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
    top_str_concept_html = f'本智能数学教育平台一共<span>{5}</span>个知识点{max_concept_str}经过这一次的测试，{improve_concept_str}' \
                           f'{improve_drop_str}希望此次练习对您以后的学习有所帮助。'
    prob_word_data = f'<p>{top_str_pass_html}</p>' \
                     f'<p>{top_str_prob_html}</p>' \
                     f'<p>{top_str_concept_html}</p>'

    # =======构造推荐题目a标签======= #
    # 因为直接构造的带有a标签的HTML, VUE插值不容易支持, 所以不在api的report写, 在此处写
    # weakness_a_html_list = app01_view_test_get_corr_prob_html(user, test_type='weakness', max_test_prob_count=6)
    # improve_a_html_list = app01_view_test_get_corr_prob_html(user, test_type='improve', max_test_prob_count=6)
    weakness_a_html_list = get_corr_prob_html_from_database(user, test_type='weakness', max_test_prob_count=6)
    improve_a_html_list = get_corr_prob_html_from_database(user, test_type='improve', max_test_prob_count=6)

    # =======获取测试报告模拟试卷预估得分======= #
    simulation_score = current_report.description
    # =======获取测试报告模拟试卷题目数======= #
    p2ts_count = len(ProblemsTest.objects.filter(testCategory=2))

    return render(request, 'report.html', locals())


def get_corr_prob_html_from_database(user, test_type='weakness',max_test_prob_count=6):
    """
    从推荐题目数据库里获取相应的提高补弱题目
    :param user: 用户
    :param test_type: 题目类型 补弱/提高
    :param max_test_prob_count: 最多要几道题目(可能没有这么多题)
    :return:
    """
    category = None
    if test_type == 'weakness':
        category = 2
    elif test_type == 'improve':
        category = 1
    p2rs = ProblemsRecommendation.objects.filter(user=user, category=category)

    prob_query = []
    if len(p2rs) > max_test_prob_count:
        # 如果查询的题目长度超过6题, 则随机采样6道题目
        prob_index_list = random.sample(range(0, len(p2rs)), max_test_prob_count)
        for i in prob_index_list:
            prob_query.append(p2rs[i].problem)
    else:  # 如果小于等于6道, 则全部获取
        for p2r in p2rs:
            prob_query.append(p2r.problem)
    count = len(prob_query)
    a_html_list = []  # 记录下标、数据等
    # prob_nid_list = []  # 传入题目的nid方便ProblemExecuteBaseView写入做题记录表
    for i in range(count):
        html = f'<a href="/problem/{prob_query[i].nid}?from=recommend#problem_position">' \
               f'{i + 1}.  {prob_query[i].id}</a>'
        a_html_list.append(html)
        # prob_nid_list.append(prob_query[i].nid)
    return a_html_list


def app01_view_test_get_corr_prob_html(user, test_type='weakness',max_test_prob_count=6):
        """
        ============此函数与test很多重合, 到时候要把他们俩融合在一起============
        首先获取掌握最好最差的三个知识点
        最后根据补        然后根据题目知识点对应表获取相应的题目
弱提高推荐相应难度的题目
        :param user: 用户Object
        :param test_type: 获取题目类型  weakness | improve
        :param max_test_prob_count: 获取题目数
        :return:
        """
        test_prob_nid_list = []
        if test_type == 'weakness' or test_type == 'improve':
            # 获取当前用户掌握最差的知识点对应的简单题/中等题的problem的nid
            # 获取当前用户掌握最差的知识点对应的中等题/困难题的problem的nid
            select_concepts = get_concepts(user=user, test_type=test_type)
            # ===== 不同题目对应概念可能有重复, 所以这里根据概念得到的test_prob_nid_list可能重复===== #
            # ===== 重复就导致test_prob_nid_list与prob_query长度不一样, 只需要依照prob_query长度即可===== #
            p2cs = []
            if select_concepts:
                p2cs = Problems2Concepts.objects.filter(concept__in=select_concepts)
            for p2c in p2cs:
                test_prob_nid_list.append(p2c.problem.nid)
            # print(test_prob_nid_list)  # [3307, 3371, 3371, 3391, ...]
        else:
            return test_prob_nid_list

        count = len(test_prob_nid_list)
        # 根据test表里problem的nid取出相应的题目
        prob_query = []
        if test_prob_nid_list:
            diff = [0, 1, 2]
            if test_type == 'weakness':
                diff = [0, 1]  # 补弱推荐相应知识点简单题/中等题
            elif test_type == 'improve':
                diff = [1, 2]  # 提高推荐相应知识点中等题/困难提
            prob_query = Problems.objects.filter(nid__in=test_prob_nid_list, difficulty__in=diff)
        # 这里又给count赋值成prob_query长度,
        # =====(原因见上面p2cs)是因为不知道为什么len(test_prob_nid_list)和len(prob_query)长度不同===== #
        if len(prob_query) > max_test_prob_count:
            # 如果查询的题目长度超过15题, 则随机采样15道题目
            prob_index_list = random.sample(range(0, len(prob_query)), max_test_prob_count)
            sample_prob_query_list = []
            for i in prob_index_list:
                sample_prob_query_list.append(prob_query[i])
            prob_query = sample_prob_query_list
        count = len(prob_query)

        # ========== 把report推荐题目写入推荐题目表, 方便在app01.view.py里problem函数查询上一题下一题
        # 按理来说test和report推荐题目是一样的, 现在KT模型还有问题, 我就先自己写成不同的了
        category = None
        if test_type == 'weakness':
            category = 2
        elif test_type == 'improve':
            category = 1

        # 删除之前推荐的题目  # ==========此处删除别忘了加上条件category=category, 推荐补弱那么删除的就是补弱题, 不应该删除提高相关的
        ProblemsRecommendation.objects.filter(user=user, category=category).delete()
        for prob in prob_query:
            # print(prob)
            ProblemsRecommendation.objects.create(
                user=user,
                problem=prob,
                category=category,
            )

        a_html_list = []  # 记录下标、数据等
        # prob_nid_list = []  # 传入题目的nid方便ProblemExecuteBaseView写入做题记录表
        for i in range(count):
            html = f'<a href="/problem/{prob_query[i].nid}?from=report_recommend#problem_position">' \
                   f'{i+1}.  {prob_query[i].id}</a>'
            a_html_list.append(html)
            # prob_nid_list.append(prob_query[i].nid)
        return a_html_list


def simulation(request):
    username = request.user.username
    if not username:
        return redirect("/login/")
    user = UserInfo.objects.get(username=username)

    simulation_type = request.GET.get('type', None)
    test_prob_nid_list = []
    if simulation in ['1', '2', '3']:
        t2cs_prob_nid_dict = ProblemsTest.objects.filter(testCategory=2, simulationNum=int(simulation)).values('problem_id')
        for prob_nid in t2cs_prob_nid_dict:
            test_prob_nid_list.append(prob_nid['problem_id'])
    if len(test_prob_nid_list) == 0:  # 用1、2、3查询不到数据, 则表明不分模拟卷1、2、3直接筛选所有
        t2cs_prob_nid_dict = ProblemsTest.objects.filter(testCategory=2).values(
            'problem_id')
        for prob_nid in t2cs_prob_nid_dict:
            test_prob_nid_list.append(prob_nid['problem_id'])

    count = len(test_prob_nid_list)
    if count == 0:  # 用户没有测验过, 返回欢迎界面, 测验过就一定生成了模拟题
        return redirect("/welcome/")
    # print(test_prob_nid_list)
    # print(len(test_prob_nid_list))
    # 根据test表里problem的nid取出相应的题目
    prob_query = []
    if test_prob_nid_list:
        # prob_query = Problems.objects.filter(nid__in=test_prob_nid_list)  # 不知道为什么用这句话少获取三个problem
        for test_prob_nid in test_prob_nid_list:
            prob_query.append(Problems.objects.get(nid=test_prob_nid))
    count = len(prob_query)

    test_prob_dict_list = []  # 记录下标、数据等
    index_list = []  # 只记录下标用于界面右侧题号展示
    # prob_nid_list其实等价于上面的test_prob_nid_list, 但我懒得改了
    prob_nid_list = []  # 传入题目的nid方便ProblemExecuteBaseView写入做题记录表
    for i in range(count):
        # 根据题目nid获取相应的知识点
        problem_concepts = Problems2Concepts.objects.filter(problem_id=prob_query[i].nid)
        test_prob_dict = {'index': i,
                          'prob': prob_query[i],
                          'html': f"my_tag/prob/{prob_query[i].category}_{prob_query[i].id}.html",
                          'problem_concepts': problem_concepts}  # 记录每道题目知识点
        test_prob_dict_list.append(test_prob_dict)
        index_list.append(i)
        prob_nid_list.append(prob_query[i].nid)

    # 先清除一下
    ShareData.objects.filter(user=user).delete()
    ShareData.objects.create(
        user=user,
        dataSimulationProbNid=str(prob_nid_list),
    )
    # print(test_prob_dict_list[0])
    return render(request, 'simulation.html', locals())

