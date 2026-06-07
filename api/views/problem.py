from app01.models import Problems, UserInfo, TestRecord, ProblemRecords, Users2Concepts, Concepts, \
    ProblemsRecommendation, TestReport, Problems2Concepts, ProblemsTest
from django.views import View
from django.http import JsonResponse
import os
import random

from django.utils import timezone
from datetime import datetime
from api.views.calculate import accurate
from app01.views import get_concepts
from api.views.tongyiAPI import get_answer
# from predict import predict
from django.db.models import Max, Count
from MathProblems.MathProblems.KTmodel import kt_predict

class ProblemsetView(View):
    def get(self, request):
        # 返回给前端信息
        res = {
            'code': 404,
            'msg': "请求失败!",
            'data': None,  # 返回查询数据
            'total': 0
        }
        username = request.user.username
        if not username:
            res['msg'] = "请先登录!"
            return res
        # print(request.GET)  # {'query': [''], 'pagenum': ['1'], 'pagesize': ['2']}  # 虽然这里面看起来value像是list, 但变成dict后就是值
        queryInfo = request.GET.copy()
        # print(queryInfo)
        query = queryInfo['query']
        page_start = (int(queryInfo['pagenum']) - 1) * int(queryInfo['pagesize'])
        page_end = int(queryInfo['pagenum']) * int(queryInfo['pagesize'])

        prob_query = Problems.objects.all()
        count = len(prob_query)
        if count == 0:  # 没有数据, 相当于请求失败
            return JsonResponse(res)
        if not query:  # 无条件, 返回全部数据
            prob_query = prob_query[page_start:page_end]
            data_list = self.get_data_list(username, prob_query)
        else:  # 根据条件筛选数据
            cond_prob_query = Problems.objects.filter(title__icontains=query).all()
            # 筛选查询完之后也是要分页并且重新计算count的
            count = len(cond_prob_query)
            if count == 0:  # 没有数据, 返回空
                data_list = None
            else:
                cond_prob_query = cond_prob_query[page_start:page_end]
                data_list = self.get_data_list(username, cond_prob_query)

        res['data'] = data_list
        res['code'] = 200
        res['total'] = count
        res['msg'] = "请求成功!"
        return JsonResponse(res)

    def get_data_list(self, username, prob_query):
        """
        data_dict = {'id': 'problem/1_1011#problem_position',
                             'state': '1',  # 0未通过 1以通过 2尝试过
                             'name': '数字匹配（已更新并重测）',
                             'pass_rate': '45.6%',
                             'knowledge': ['知识点1', '知识点2', '知识点3'],
                             'difficulty': '0'  # 0简单 1中等 2困难
                             }
        """
        user = UserInfo.objects.get(username=username)
        data_list = []
        for prob in prob_query:
            # 为防止dict覆盖问题, 每次都new一个新的dict
            data_dict = {}
            # data_dict['id']的url后面加了个GET请求参数from=problemset
            # 以便上一题下一题功能给出适当的题目(整个题库里还是只在推荐题目里)
            # ===========这里f'/problem/...'中problem前面多加一个/就是从根目录跳转,=========== #
            # ===========f'problem/...'就是从当前目录跳转=========== #
            data_dict['id'] = f'/problemset/{prob.nid}?from=problemset#problem_position'
            # ==========做题情况: 0 未开始  1 已通过  2 尝试过========== #
            state = 0
            pr_pass = ProblemRecords.objects.filter(user=user, problem=prob, score=1)
            if len(pr_pass) > 0:  # 如果有通过记录
                state = 1
            else:
                pr_pass = ProblemRecords.objects.filter(user=user, problem=prob)
                if len(pr_pass) > 0:  # 如果有做过记录
                    state = 2
            data_dict['state'] = state  # random.randint(0, 2)
            data_dict['name'] = prob.id
            if prob.submit_count == 0:  # 避免除0
                data_dict['pass_rate'] = '0'
            else:
                pass_rate = prob.pass_count / prob.submit_count * 100
                if pass_rate == 0:
                    data_dict['pass_rate'] = '0'
                else:
                    data_dict['pass_rate'] = f'{pass_rate:.2f}%'  # .0f就是没有小数位
            # ==========知识点========== #
            p2cs_name = Problems2Concepts.objects.filter(problem=prob).values('concept__name')
            # print(p2cs_name)  # <QuerySet [{'concept__name': '数学'}, {'concept__name': '类'}, {'concept__name': '程序基本结构'}]>
            concepts_name_list = []
            for p2c_name in p2cs_name:
                concepts_name_list.append(p2c_name['concept__name'])
            data_dict['knowledge'] = concepts_name_list  # ['知识点1', '知识点2', '知识点3']
            data_dict['difficulty'] = random.randint(0, 2)
            data_list.append(data_dict)
        return data_list


class ProblemUploadBaseView(View):
    def get_upload_res(self, request, upload_type=None):
        # 返回给前端信息
        res = {
            'code': 404,
            'msg': "没有上传文件!",
            'data': None,  # 返回上传url
        }
        # 在auth.login(request, user)中是用request.user = user
        # 把user加入request中的, 所以此处应该也是用成员变量方式获取
        username = request.user.username
        if not username:
            res['msg'] = "请先登录!"
            return res
        # 以manage.py文件为基础, ./即为项目根目录
        root_path = './media/problem_upload/'
        # print(request.FILES)  # <MultiValueDict: {'file': [<InMemoryUploadedFile: badges.png (image/png)>]}>
        # 获取上传的文件,如果没有文件,则默认为None;
        File = request.FILES.get("file", None)
        if upload_type == 'test':
            Time = request.POST.get("time", None)
            root_path = './media/test_problem_upload/'
        if File is None:
            return res
        else:
            # mkdir 只能创建一级文件夹，如果父文件夹不存在则报错，所以此处先创建一次父目录
            if not os.path.exists(root_path):
                os.mkdir(root_path)
            prob_code_path = os.path.join(root_path, username)
            if not os.path.exists(prob_code_path):
                os.mkdir(prob_code_path)
            if upload_type == 'test':
                prob_code_path = os.path.join(prob_code_path, Time)
                # 打开特定的文件进行二进制的写操作;
                # mkdir 只能创建一级文件夹，如果父文件夹不存在 则报错
                if not os.path.exists(prob_code_path):
                    os.mkdir(prob_code_path)
            file_path = os.path.join(prob_code_path, File.name)
            with open(file_path, 'wb+') as f:
                # 分块写入文件, 避免文件太大卡顿
                for chunk in File.chunks():
                    f.write(chunk)
            res['code'] = 200
            res['msg'] = "上传成功!"
            # 其实直接写入数据库就好, 然后调用DL模型处理, 返回结果即可
            # res['data'] = {'file_root_path': prob_code_path, 'file_name': File.name}
            res['data'] = {'file_path': file_path}
            return res


class ProblemUploadView(ProblemUploadBaseView):
    def post(self, request):
        res = self.get_upload_res(request)
        return JsonResponse(res)
    # def post(self, request):
    #     # 返回给前端信息
    #     res = {
    #         'code': 404,
    #         'msg': "没有上传文件!",
    #         'data': None,  # 返回上传url
    #     }
    #     # 在auth.login(request, user)中是用request.user = user
    #     # 把user加入request中的, 所以此处应该也是用成员变量方式获取
    #     username = request.user.username
    #     if not username:
    #         res['msg'] = "请先登录!"
    #         return JsonResponse(res)
    #     # print(request.FILES)  # <MultiValueDict: {'file': [<InMemoryUploadedFile: badges.png (image/png)>]}>
    #     # 获取上传的文件,如果没有文件,则默认为None;
    #     File = request.FILES.get("file", None)
    #     # 以manage.py文件为基础, ./即为项目根目录
    #     # mkdir 只能创建一级文件夹，如果父文件夹不存在则报错，所以此处先创建一次父目录
    #     root_path = './media/test_problem_upload/'
    #     if File is None:
    #         return JsonResponse(res)
    #     else:
    #         if not os.path.exists(root_path):
    #             os.mkdir(root_path)
    #         prob_code_path = os.path.join(root_path, username)
    #         # 打开特定的文件进行二进制的写操作;
    #         if not os.path.exists(prob_code_path):
    #             os.mkdir(prob_code_path)
    #         file_path = os.path.join(prob_code_path, File.name)
    #         with open(file_path, 'wb+') as f:
    #             # 分块写入文件, 避免文件太大卡顿
    #             for chunk in File.chunks():
    #                 f.write(chunk)
    #         res['code'] = 200
    #         res['msg'] = "上传成功!"
    #         # 其实直接写入数据库就好, 然后调用DL模型处理, 返回结果即可
    #         res['data'] = {'file_path': file_path}
    #         return JsonResponse(res)


class TestProblemUploadView(ProblemUploadBaseView):
    def post(self, request):
        res = self.get_upload_res(request, upload_type='test')
        return JsonResponse(res)
    # def post(self, request):
    #     # 返回给前端信息
    #     res = {
    #         'code': 404,
    #         'msg': "没有上传文件!",
    #         'data': None,  # 返回上传url
    #     }
    #     # 在auth.login(request, user)中是用request.user = user
    #     # 把user加入request中的, 所以此处应该也是用成员变量方式获取
    #     username = request.user.username
    #     if not username:
    #         res['msg'] = "请先登录!"
    #         return JsonResponse(res)
    #     # print(request.FILES)  # <MultiValueDict: {'file': [<InMemoryUploadedFile: badges.png (image/png)>]}>
    #     # 获取上传的文件,如果没有文件,则默认为None;
    #     File = request.FILES.get("file", None)
    #     Time = request.POST.get("time", None)
    #     # 以manage.py文件为基础, ./即为项目根目录
    #     # mkdir 只能创建一级文件夹，如果父文件夹不存在则报错，所以此处先创建一次父目录
    #     root_path = './media/test_problem_upload/'
    #     if File is None:
    #         return JsonResponse(res)
    #     else:
    #         if not os.path.exists(root_path):
    #             os.mkdir(root_path)
    #         prob_code_path = os.path.join(root_path, username)
    #         if not os.path.exists(prob_code_path):
    #             os.mkdir(prob_code_path)
    #         prob_code_path = os.path.join(prob_code_path, Time)
    #         # 打开特定的文件进行二进制的写操作;
    #         # mkdir 只能创建一级文件夹，如果父文件夹不存在 则报错
    #         if not os.path.exists(prob_code_path):
    #             os.mkdir(prob_code_path)
    #         file_path = os.path.join(prob_code_path, File.name)
    #         with open(file_path, 'wb+') as f:
    #             # 分块写入文件, 避免文件太大卡顿
    #             for chunk in File.chunks():
    #                 f.write(chunk)
    #         res['code'] = 200
    #         res['msg'] = "上传成功!"
    #         # 其实直接写入数据库就好, 然后调用DL模型处理, 返回结果即可
    #         # res['data'] = {'file_root_path': prob_code_path, 'file_name': File.name}
    #         res['data'] = {'file_path': file_path}
    #         return JsonResponse(res)


class ProblemExecuteBaseView(View):
    def get_execute_res(self, request, upload_type=None):
        # 返回给前端信息
        res = {
            'code': 404,
            'msg': "执行代码失败!",
            'data': None,  # 返回代码执行信息
        }
        """
        如果前端直接以下面这种方式发送post请求, 由于是application/json格式
        axios.post('/api/testProblemUpload/', formdata).then(res= > {
        会被我自定义的Md1中间件拦截, 把数据放在了request.data里面
        print(request.data)
        所以不用直接发送字典数据, 用form格式数据application/x-www-form-urlencoded
        ===== 用form格式发送的数据, list变成了一个字符串, 所以还是用application/json格式 =====
        """
        username = request.user.username
        if not username:
            res['msg'] = "请先登录!"
            return res
        Time = request.data.get("time", None)  # 用于记录到做题记录里面的
        Path = request.data.get("path", None)
        # 在problem/Test后端代码特意传了prob_nid_list给html页面
        # 在执行代码时再传回来, 就是为了方便写入做题记录表
        prob_nid_list = request.data.get("prob_nid_list", None)
        result_list = []
        score_list = []
        for path in Path:
            if path == 0:
                result_list.append('您没有做这道题')
                score_list.append(0)
            else:
                with os.popen(f"python {path} 2>&1") as p:
                    result = p.read()
                    # 首先去除所有空格, 不用去除换行, html页面不会显示.replace('\n', ' ')
                    result = result.replace(' ', '')
                    # 最后把文件路径去除
                    result = result[result.find('.py') + 5:]
                    result_list.append(result)
                    score_list.append(1)
        res['code'] = 200
        res['msg'] = "提交成功!"
        res['data'] = {'prob_result': result_list}

        # =========== 把结果添加到做题记录和测验表里面 =========== #
        # print(prob_nid_list)
        # 获取用户, 此处不能获取uid赋值, 外键应该是把整个objects赋值过去
        # Cannot assign "1": "TestRecord.user" must be a "UserInfo" instance.
        user = UserInfo.objects.get(username=username)
        # 生成测验记录, 此表先生成, 方便加入到做题记录表里
        test_obj = None
        if upload_type == 'test':
            grade = 0
            for score in score_list:
                grade += score
            test_obj = TestRecord.objects.create(
                user=user,
                score=grade,
                comment='根据score_list, 您某些知识点做的有问题....'
            )
        # 生成做题记录
        for i in range(len(score_list)):
            # 外键必须传入objects, 而不是单个值
            prob = Problems.objects.get(nid=prob_nid_list[i])
            ProblemRecords.objects.create(
                user=user,
                problem=prob,
                score=score_list[i],
                code_path=Path[i],
                test=test_obj,
            )
        # =========== 把结果添加到做题记录和测验表里面 =========== #

        return res


class ProblemExecuteView(ProblemExecuteBaseView):
    def post(self, request):
        res = self.get_execute_res(request)
        return JsonResponse(res)


class TestProblemExecuteView(ProblemExecuteBaseView):
    def post(self, request):
        res = self.get_execute_res(request, upload_type='test')
        return JsonResponse(res)


class AceProblemExecuteView(View):
    def python_post(self, request):
        # 返回给前端信息
        res = {
            'code': 404,
            'msg': "执行代码失败!",
            'data': None,  # 返回代码执行结果
        }
        username = request.user.username
        if not username:
            res['msg'] = "请先登录!"
            return res
        Time = request.data.get("time", None)
        PythonStr = request.data.get("python_str", None)

        root_path = './media/test_problem_upload/'
        if not os.path.exists(root_path):
            os.mkdir(root_path)
        prob_code_path = os.path.join(root_path, username)
        if not os.path.exists(prob_code_path):
            os.mkdir(prob_code_path)
        file_path = os.path.join(prob_code_path, 'problrem.py')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(PythonStr)
        with os.popen(f"python {file_path} 2>&1") as p:
            result = p.read()
        res['code'] = 200
        res['msg'] = "执行代码成功!"
        res['data'] = result
        return JsonResponse(res)

    def get_file_path(self, username):
        # ============linux系统g++编译运行命令和windows不同, 而且文件路径也不同============ #
        # 首先获取当前文件所在路径
        current_path = os.path.abspath(os.path.dirname(__file__))
        # 获取myProject，也就是项目的根路径
        proj_root_path = current_path[:current_path.find("knowledge_trace") + len("knowledge_trace")]
        file_absolute_path = '/media/test_problem_upload/'
        # 不知道为什么下面这句os.path.join失效了
        # file_root_path = os.path.join(proj_root_path, file_absolute_path)
        file_root_path = proj_root_path+file_absolute_path

        if not os.path.exists(file_root_path):
            os.mkdir(file_root_path)
        prob_code_path = os.path.join(file_root_path, username)
        if not os.path.exists(prob_code_path):
            os.mkdir(prob_code_path)
        return proj_root_path, prob_code_path

    def execute_code(self, proj_root_path, prob_code_path, prob_count, Submit_Execute, cppStr_list, prob_nid_list):
        prob_result_list = []  # 返回结果list
        prob_pass_count = 0  # 通过题目数
        prob_score = []  # 题目做对与否

        for i in range(prob_count):
            result = {}  # pass, test_sample, user_out, ture_out
            # =========如果是最终交卷, 已经有结果了, 就不用执行下面语句了, 加快运行速度========= #
            if Submit_Execute == 'final_submit':
                # 之前提交结果存储在cppStr_list中, 没有提交的值为0, 所以把result['pass']放在if里直接赋值
                if cppStr_list[i] == 'AC':
                    result['pass'] = 'AC'
                    prob_pass_count += 1  # 这个有问题   ----   每次执行都会修正prob_pass_count, 最后就不用修改了
                    prob_score.append(1)
                else:
                    result['pass'] = 'CE'
                    prob_score.append(0)
                prob_result_list.append(result)
                # 跳过下面要执行的代码
                continue

            # =========如果不是最终交卷, 则需要执行代码判断正误, 且修改相应题目提交信息========= #
            prob = Problems.objects.get(nid=prob_nid_list[i])
            #problem_name = f'{prob.category}_{prob.id}'
            eq=prob.equation
            eql = eq[2:]
            true_out = accurate(eql)
            # prob_cate_id.append((int(prob.category), int(prob.id)))
            # write ace code to file 把用户在ace输入的代码写入./media/test_problem_upload/problrem.cpp
            # with open(os.path.join(prob_code_path, 'problem.cpp'), 'w', encoding='utf-8') as f:
            #    f.write(str(cppStr_list[i]))

            try:
                str1,flg=cppStr_list[i].split('\n')
                str2=str1[2:]
                result['msg'] = ""
                try:
                    out=accurate(str2)

                    if not ((flg.split(".")[0]).isdigit() or flg.isdigit() or  (flg.split('-')[-1]).split(".")[-1].isdigit()):
                        result['msg'] = result['msg'] + "解题答案格式有误\n"
                        prob_score.append(0)
                    else:
                        if float(out) !=float(flg):
                            prob_score.append(0)
                            result['msg'] = result['msg'] + "解题过程与答案不符\n"
                            result['pass'] = 'CE'
                            prob_score.append(0)

                        elif out == true_out :
                            result['pass'] = 'AC'
                            prob_pass_count += 1
                            prob_score.append(1)
                            result['msg']="成功解题!\n"
                        else:
                            result['pass'] = 'CE'
                            prob_score.append(0)
                            result['msg']="还需继续努力！\n"
                        result['user_out'] = out
                        result['true_out'] = true_out
                        result['user_out_detail'] = str1
                        result['true_out_detail'] = eq
                except:
                    prob_score.append(0)
                    result['msg'] = "解题过程格式有误\n"
            except:
                prob_score.append(0)
                result['msg'] = "输入格式有误\n"
            prob_result_list.append(result)
            return prob_result_list, prob_pass_count, prob_score
        return prob_result_list, prob_pass_count, prob_score

            # run code  运行代码，并且以./templates/my_tag/prob/judge/in/{problem_name}.in文件作为输入
            #result_in_root_path = proj_root_path + f'/templates/my_tag/prob/judge/in/{problem_name}.in'
            #cmd = f'cd {prob_code_path} && g++ problem.cpp -o problem 2>&1 && problem.exe < {result_in_root_path}'
            # with os.popen(cmd) as p:
            #     user_out = p.read()
            # get truth result  得到真实结果，./templates/my_tag/prob/judge/out/{problem_name}.out
            # result_out_root_path = proj_root_path + f'/templates/my_tag/prob/judge/out/{problem_name}.out'
            # with open(result_out_root_path, "r", encoding='UTF-8') as f:
            #     true_out = f.read()
            #     true_out = true_out.strip().replace('\n', '')

                # result = f'test_sample is \n{test_sample},\nuser_out is {user_out}, but expect out is {true_out}'
                # https://www.pianshen.com/article/6146632940/   innerHTML识别标签，innerText不识别标签
                # result = result.replace('\n', '<br/>')  # 插入<br/>在html换行https://bbs.csdn.net/topics/390763753
            # 读取测试样例, 仿照leetcode输出




    def write_test_record(self, Prob_Test, Submit_Execute, Time, user, prob_count, prob_pass_count):
        test_record = None
        if Prob_Test == 'test':
            # 这就有个问题就是test_records的prob_count和prob_pass_count有问题
            # 所以修改一下prob_count和prob_pass_count
            # 用新的prob_count_不影响修改做题记录的判断
            prob_count_ = prob_count
            prob_pass_count_ = prob_pass_count
            print("+++++++++++=="+"Prob_Test")
            # ============为了解决有些用户只是在test界面提交, 而没有点最终交卷, 测试记录无效问题============ #
            test_record_category = 1  # 有效测验记录
            if Submit_Execute == 'test_submit':
                test_record_category = 2  # =========无效测验记录========= #
                prob_count_ = -1  # 避免除0
                prob_pass_count_ = 0
                # if prob_count_ == 0:
                #     prob_count_ = -1  # 避免除0
            # 用get找不到匹配项会报错ProblemRecords matching query does not exist
            # Time如果是str类型, 报错expected string or bytes-like object
            # 下面根据Time查找test_records来修改就是为了提交按钮设计的, 每次提交试卷后就是新测验了
            if prob_count_ == 0:
                prob_pass_count_ = 0
                prob_count_ = -1  # 避免除0
            test_records = TestRecord.objects.filter(user=user, test_date=Time)
            if len(test_records) == 0:  # 第一次点击提交, 新建一条测验记录
                test_record = TestRecord.objects.create(
                    user=user,
                    test_date=Time,
                    prob_count=prob_count_,
                    prob_pass_count=prob_pass_count_,  # 可以用prob_score来计算得到
                    score=prob_pass_count_ / prob_count_,
                    category=test_record_category,  # 增加这条, 解决提交时无效测试记录问题
                    comment='你做得好啊!',
                )
            else:  # 以后就是修改这次测验记录
                test_record = test_records[0]  # filter得到的是一个QuerySet, 取第一个元素
                TestRecord.objects.filter(nid=test_record.nid).update(
                    prob_count=prob_count_,
                    test_date=Time,
                    prob_pass_count=prob_pass_count_,  # 可以用prob_score来计算得到
                    score=prob_pass_count_ / prob_count_,
                    category=test_record_category,  # 增加这条, 解决提交时无效测试记录问题
                )
        return test_record

    def write_prob_record_submitCount(self, Prob_Test, Submit_Execute,
                                      user, test_record, prob_count, prob_nid_list, prob_score):
        for i in range(prob_count):
            prob = Problems.objects.get(nid=prob_nid_list[i])
            if Prob_Test == 'test':  # 如果是测试, 就应该从当前测验的test=test_record里找做题记录
                ##### 时间逆序, 下面取prob_records[0]就是最新的一条数据了
                prob_records = ProblemRecords.objects.filter(user=user, problem_id=prob_nid_list[i], test=test_record).order_by('-create_date')
            else:  #如果是普通做题, 就应该从test=None的记录里去找做题记录
                #用get找不到匹配项会报错ProblemRecords matching query does not exist
                #时间逆序, 下面取prob_records[0]就是最新的一条数据了
                prob_records = ProblemRecords.objects.filter(user=user, problem_id=prob_nid_list[i], test=None).order_by('-create_date')
            if len(prob_records) == 0:  # 如果没有这道题目的做题记录, 新建一个做题记录
                ProblemRecords.objects.create(
                    user=user,
                    problem_id=prob_nid_list[i],
                    score=prob_score[i],
                    code_path=None,
                    test=test_record,
                    prob_submit_count=1,
                )
                Problems.objects.filter(nid=prob_nid_list[i]).update(submit_count=prob.submit_count + 1)
                if prob_score[i] == 1:
                    # ============修改当前Problem的通过次数, 当前用户当前测验/做题界面通过这个Problem后不在增加============ #
                    Problems.objects.filter(nid=prob_nid_list[i]).update(pass_count=prob.pass_count + 1)
            else:  # 如果有这道题目的做题记录, 则提交次数+1
                ## 时间逆序, 取prob_records[0]就是最新的一条数据了, 如果最新一次做对了, 就不新建做题记录了
                prob_record = prob_records[0]  # filter得到的是一个QuerySet, 取第一个元素
                if prob_record.score == 1:  # 之前已经做对了，之后的就不用记录了
                    continue
                # 如果是最终测验, 并且有做题记录, 这次不记录
                # 提交试卷主要是生成真正的做题记录, 同时把没提交的试题记录下
                if Submit_Execute == 'final_submit':
                    continue

                ##### prob_submit_count = prob_record.prob_submit_count + 1
                ##### 由于KT模型输入做题记录限制问题, 每次提交都应该创建一条新记录, 直到当前用户做对这道题为止 #####
                ProblemRecords.objects.create(
                    user=user,
                    problem_id=prob_nid_list[i],
                    score=prob_score[i],
                    code_path=None,
                    test=test_record,
                    prob_submit_count=1,
                )

                # score = prob_score[i]
                # ============Problems的修改不能放在上面if prob_record.score == 1:这============ #
                # 因为只要做对了, 就会一直判断上面语句,
                # 而这里在做对后就不执行了, 只会加一次
                if prob_score[i] == 1:
                    # ============修改当前Problem的通过次数, 当前用户当前测验/做题界面通过这个Problem后不在增加============ #
                    Problems.objects.filter(nid=prob_nid_list[i]).update(pass_count=prob.pass_count + 1)
                # ============修改当前Problem的提交次数, 当前用户当前测验/做题界面通过这个Problem后不再增加提交次数============ #
                Problems.objects.filter(nid=prob_nid_list[i]).update(submit_count=prob.submit_count + 1)

    def get_kt_model_input(self, user):
        # uid probs resp len(probs)
        uid = user.nid

        probs_q = []
        probs_c = []
        resp = []
        # ================这里有问题, 应该是输入test题目记录还是所有题目记录呢？================ #
        # if Prob_Test == 'test':  # 如果是测试, 就应该从当前测验的test=test_record里找做题记录
        #     probRecords = ProblemRecords.objects.filter(user=user, test=test_record)
        # elif Prob_Test == 'prob':  # 如果是普通做题, 可以全部也可以从test=None的记录里去找做题记录
        #     probRecords = ProblemRecords.objects.filter(user=user, test=None)
        # 直接读取当前用户全部做题记录, 由于模型限制了输入题目数量, 所以以时间升序排序, 取最后面70道题目
        probRecords = ProblemRecords.objects.filter(user=user).order_by('create_date')
        if len(probRecords) >= 70:  # 至少要有70条数据, 才能取后70条
            probRecords = probRecords[len(probRecords) - 70:]  # 取最后70条数据
        # 根据提交数构造输入KT模型的问题、得分list
        for probRecord in probRecords:
            if probRecord.prob_submit_count <= 0:  # 提交数异常, 跳过此数据
                continue
            prob_submit_count = probRecord.prob_submit_count
            for i in range(prob_submit_count):
                probs_c.append((int(probRecord.problem.category) ))
                probs_q.append((int(probRecord.problem.id)))
                if i != prob_submit_count - 1:  # 前面提交都是做错的
                    resp.append(0)
                    continue
                # 走到下面语句, 就说明是最后一次提交了
                if probRecord.score == 1:  # 如果是做对的
                    resp.append(1)
                else:
                    resp.append(0)
        # print(probs)
        # print(resp)

        # 输入69道做题记录, 不然输入太多有问题, 而且由于是时间升序, 取最后69道题目
        # =====其实这里还是有问题的, 我根据做题记录构造probs时, 没有按照时间顺序, 而是把同一个题目的不同提交放在了一起===== #
        # =====后面要改的话, 就需要每提交一次, 就生成一条做题记录,
        # 而且不能重复(不过create记录前需要判断之前这道题做对没, 做对了就不用添加了)===== #
        probs_q = probs_q[-69:]  # 此处再次处理一下, 免得超过70
        probs_c = probs_c[-69:]
        #probs.append((1, 1007))  # 后面再加一个预测做对与否的题目(假题目)
        resp = resp[-69:]

        # =====获取上一次用户知识点掌握情况===== #
        concepts_count = Concepts.objects.all().count()
        u2cs = [0 for _ in range(concepts_count)]
        last_concept_date = Users2Concepts.objects.filter(user=user).aggregate(Max('add_date'))
        if last_concept_date:  # 如果有记录, 就把当前concept在数据库中最近的记录值获取到
            # 把此处get改成filter, 免得点快了生成同样值老报错get() returned more than one Users2Concepts -- it returned 2!
            last_concepts = Users2Concepts.objects.filter(user=user,
                                                         add_date=last_concept_date['add_date__max'])
            for i, last_concept in enumerate(last_concepts):
                u2cs[i] = last_concept.current_score
        return uid, probs_q,probs_c, resp, u2cs

    def get_kt_model_predict_problem_input(self, user, prob_num_per_concept=2):
        """
        从每个概念中选择prob_num_per_concept数量的题目, 给模型预测以得到试卷评分预测
        :param user: 用户
        :param prob_num_per_concept: 每个概念获取题目数
        :return: 待预测试卷题目
        """
        concepts = Concepts.objects.all()
        probs = []
        # 清除之前得到的模拟卷试题
        ProblemsTest.objects.filter(testCategory=2).delete()
        for concept in concepts:
            p2cs = Problems2Concepts.objects.filter(concept=concept)
            select_prob_index_list = random.sample(range(0, len(p2cs)), prob_num_per_concept)
            for index in select_prob_index_list:
                probs.append((int(p2cs[index].problem.category), int(p2cs[index].problem.id)))
                # 把模拟试卷题目添加到ProblemsTest表里
                ProblemsTest.objects.create(
                    user=user,
                    problem=p2cs[index].problem,
                    testCategory=2,
                )
        return probs

    def write_user_to_concepts(self, Time, user, kt_output_concept_dict):
        current_user_to_concept_list = []  # 方便TestReport表创建
        # concept_id = list(map(int, kt_output_concept_dict.keys()))  # str转成int
        concept_id = [i+1 for i in range(5)]
        concept_score = list(kt_output_concept_dict)
        for i in range(len(concept_id)):
            concept = Concepts.objects.get(id=concept_id[i])
            # 查询当前concept在数据库中最近的记录(其实主要是不好查询第二大值, 就在这里查询一次已存在的最近的, 相当于当前的第二最大值)
            #  {'add_date__max': datetime.datetime(2022, 6, 9, 5, 56, 31, 514000, tzinfo=<UTC>)}
            last_score = None
            last_concept_date = Users2Concepts.objects.filter(user=user, concept=concept).aggregate(Max('add_date'))
            if last_concept_date:  # 如果有记录, 就把当前concept在数据库中最近的记录值获取到
                # 把此处get改成filter, 免得点快了生成同样值老报错get() returned more than one Users2Concepts -- it returned 2!
                last_concept = Users2Concepts.objects.filter(user=user, concept=concept,
                                                             add_date=last_concept_date['add_date__max'])
                if last_concept:
                    last_concept = last_concept[0]  # 有相同值直接取第一个元素即可
                    # 把最近记录的current_score当作这一次知识点知识点掌握记录的last_score
                    last_score = last_concept.current_score

            # =========避免连点提交试卷重复创建知识点, 此处先清除一下可能的相应的知识点========= #
            Users2Concepts.objects.filter(user=user, concept=concept, add_date=Time).delete()
            user_to_concept = Users2Concepts.objects.create(
                user=user,
                concept=concept,
                # 记录了时间就不用写last_score了,
                # 没有时间的话就要查询得到Users2Concepts把current_score赋值给last_score
                last_score=last_score,
                current_score=concept_score[i],
                add_date=Time,
            )
            current_user_to_concept_list.append(user_to_concept)
        return current_user_to_concept_list

    # 提高和补弱分开写入, 但是dl_index界面展示时先是全部提高, 然后再是全部补弱或者反过来, 观感不好
    def test_write_reco_prob_order(self, user, test_type='weakness', max_test_prob_count=6):
        """
        ============此函数与test很多重合, 到时候要把他们俩融合在一起============
        首先获取掌握最好最差的三个知识点
        然后根据题目知识点对应表获取相应的题目
        最后根据补弱提高推荐相应难度的题目
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

        # 删除之前推荐的题目
        # ==========此处删除别忘了加上条件category=category, 推荐补弱那么删除的就是补弱题, 不应该删除提高相关的========== #
        # ==========后面可以考虑把提高补弱写入数据库整合在一起, 不然太麻烦了========== #
        ProblemsRecommendation.objects.filter(user=user, category=category).delete()
        for prob in prob_query:
            # print(prob)
            ProblemsRecommendation.objects.create(
                user=user,
                problem=prob,
                category=category,
                # origin=1,
            )

    # 解决上面的dl_index界面展示观感不好问题(提高补弱扎堆), 同时乱序写入数据库
    def test_write_reco_prob_no_order(self, user, max_test_prob_count=6):
        """
        ============此函数与test很多重合, 到时候要把他们俩融合在一起============
        首先获取掌握最好最差的三个知识点
        然后根据题目知识点对应表获取相应的题目
        最后根据补弱提高推荐相应难度的题目
        :param user: 用户Object
        :param max_test_prob_count: 获取题目数
        :return:
        """
        test_type_weakness = 'weakness'
        test_type_improve = 'improve'
        test_weakness_prob_nid_list = []
        test_improve_prob_nid_list = []
        # 获取当前用户掌握最差的知识点对应的简单题/中等题的problem的nid
        select_weakness_concepts = get_concepts(user=user, test_type=test_type_weakness)
        # 获取当前用户掌握最差的知识点对应的中等题/困难题的problem的nid
        select_improve_concepts = get_concepts(user=user, test_type=test_type_improve)

        # ===== 不同题目对应概念可能有重复, 所以这里根据概念得到的test_prob_nid_list可能重复===== #
        # ===== 重复就导致test_prob_nid_list与prob_query长度不一样, 只需要依照prob_query长度即可===== #
        p2cs_weakness = []
        if select_weakness_concepts:
            p2cs_weakness = Problems2Concepts.objects.filter(concept__in=select_weakness_concepts)
            for p2c in p2cs_weakness:
                test_weakness_prob_nid_list.append(p2c.problem.nid)

        p2cs_improve = []
        if select_improve_concepts:
            p2cs_improve = Problems2Concepts.objects.filter(concept__in=select_improve_concepts)
            for p2c in p2cs_improve:
                test_improve_prob_nid_list.append(p2c.problem.nid)


        count_weakness = len(test_weakness_prob_nid_list)
        count_improve = len(test_improve_prob_nid_list)
        # 根据test表里problem的nid取出相应的题目
        prob_query_weakness = []
        prob_query_improve = []
        if test_weakness_prob_nid_list:
            diff = [0, 1]  # 补弱推荐相应知识点简单题/中等题
            prob_query_weakness = Problems.objects.filter(nid__in=test_weakness_prob_nid_list, difficulty__in=diff)
        if test_improve_prob_nid_list:
            diff = [1, 2]  # 提高推荐相应知识点中等题/困难提
            prob_query_improve = Problems.objects.filter(nid__in=test_improve_prob_nid_list, difficulty__in=diff)
        # 这里又给count赋值成prob_query长度,
        # =====(原因见上面p2cs)是因为不知道为什么len(test_prob_nid_list)和len(prob_query)长度不同===== #
        if len(prob_query_weakness) > max_test_prob_count:
            # 如果查询的题目长度超过15题, 则随机采样15道题目
            prob_index_list = random.sample(range(0, len(prob_query_weakness)), max_test_prob_count)
            sample_prob_query_list = []
            for i in prob_index_list:
                sample_prob_query_list.append(prob_query_weakness[i])
            prob_query_weakness = sample_prob_query_list
        if len(prob_query_improve) > max_test_prob_count:
            # 如果查询的题目长度超过15题, 则随机采样15道题目
            prob_index_list = random.sample(range(0, len(prob_query_improve)), max_test_prob_count)
            sample_prob_query_list = []
            for i in prob_index_list:
                sample_prob_query_list.append(prob_query_improve[i])
            prob_query_improve = sample_prob_query_list
        count_weakness = len(prob_query_weakness)
        count_improve = len(prob_query_improve)

        # ========== 把report推荐题目写入推荐题目表, 方便在app01.view.py里problem函数查询上一题下一题
        # 按理来说test和report推荐题目是一样的, 现在KT模型还有问题, 我就先自己写成不同的了
        category_weakness = 2
        category_improve = 1

        # 删除之前推荐的题目
        # ==========此处删除别忘了加上条件category=category, 推荐补弱那么删除的就是补弱题, 不应该删除提高相关的========== #
        # ==========后面可以考虑把提高补弱写入数据库整合在一起, 不然太麻烦了========== #
        # #########==========一起写入就是删除所有类别推荐题目==========######### #
        # ProblemsRecommendation.objects.filter(user=user, category=category).delete()
        ProblemsRecommendation.objects.filter(user=user).delete()

        #### ===============关于如何乱序合并两个list以后还可以再更改=============== ####
        count = min(count_weakness, count_improve)
        # ===============一个类别一题间序插入=============== #
        for i in range(count):
            # print(prob)
            ProblemsRecommendation.objects.create(
                user=user,
                problem=prob_query_weakness[i],
                category=category_weakness,
                # origin=1,
            )
            ProblemsRecommendation.objects.create(
                user=user,
                problem=prob_query_improve[i],
                category=category_improve,
                # origin=1,
            )
        # if count == count_weakness: # 补弱题目少, 还需把剩余提高题目插入
        for i in range(count_improve - count):  # 由于range负数为空, 就不用上面的if判断了
            ProblemsRecommendation.objects.create(
                user=user,
                problem=prob_query_improve[i+count],
                category=category_improve,
                # origin=1,
            )
        # else:  # 补弱题目多, 还需把剩余补弱题目插入
        for i in range(count_weakness - count):  # 由于range负数为空, 就不用上面的if判断了
            ProblemsRecommendation.objects.create(
                user=user,
                problem=prob_query_weakness[i+count],
                category=category_weakness,
                # origin=1,
            )

    def write_test_report(self, Submit_Execute, Time, user, test_record, current_user_to_concept_list, simulation_score):
        if Submit_Execute == 'final_submit':  # 交卷才能生成测试报告
            # 交卷后一定有testRecord记录
            # ===========获取上一次测验记录(date第二大值, 倒序的第二个元素, index=1)=========== #
            last_test_pass_rate = None
            # ============TestRecord的category=1表示寻找的是有效测验记录, 测试报告里只记录有效测验============ #
            order_test_record = TestRecord.objects.filter(user=user, category=1).order_by('-test_date')  # 负号倒序
            if len(order_test_record) >= 2:  # 至少有两条记录 # 可能没有上一次测验记录
                last_test_pass_rate = order_test_record[1].score
            # ===========获取这次test中提交最多与最少的测试记录, 升序排序=========== #
            current_max_submit_prob = None
            current_min_submit_prob = None
            current_max_submit_prob_count = 0
            current_min_submit_prob_count = 0
            # 获取当前测试所有答对题目
            ##### 由于KT模型输入限制, 现在每次提交都生成做题记录了, 所以此处求current_max/min_submit_prob方法就不同了：
            ##### https://zhidao.baidu.com/question/873215033570168732.html
            ##### https://blog.csdn.net/weixin_45124380/article/details/124594703
            ##### prob_group_count = ProblemRecords.objects.filter(test=test_record)\
            #####     .values("problem").annotate(count=Count("prob_submit_count"))
            ##### print(prob_group_count) # [{'problem': 3283, 'count': 4}, {'problem': 3290, 'count': 1}, ...]
            order_prob_record = ProblemRecords.objects.filter(test=test_record, score=1).order_by('prob_submit_count')
            ##### 每道题score=1的答题记录只会有一条, 所以还是可以根据这个判断test的答题情况
            if len(order_prob_record) == 0:  # 全部答错或者没有答过题, 测验交卷后, 一定有答题
                pass  # 全部为None或0
            if len(order_prob_record) == 1:  # 只答对一题, max == min
                min_prob_record = order_prob_record[0]
                ##### 只有一题做对, 就对这道题目分组统计获取值
                prob_group_count = ProblemRecords.objects.filter(test=test_record, problem=min_prob_record.problem)\
                    .values("problem").annotate(count=Count("prob_submit_count"))
                ##### print(prob_group_count) # <QuerySet [{'problem': 3283, 'count': 1}]>
                ##### prob_group_count1 = ProblemRecords.objects.filter(test=test_record, problem=min_prob_record.problem) \
                #####     .annotate(count=Count("prob_submit_count"))  # <QuerySet [<ProblemRecords: 用户admin做了题目OO1-3 日期类Date>]>
                ##### print(prob_group_count1)
                current_min_submit_prob = min_prob_record.problem.title
                ##### current_min_submit_prob_count = min_prob_record.prob_submit_count
                current_min_submit_prob_count = prob_group_count[0]['count']
                current_max_submit_prob = current_min_submit_prob
                current_max_submit_prob_count = current_min_submit_prob_count
            elif len(order_prob_record) >= 2:  # 至少答对两题
                ##### 首先获取所有做对的题目
                problem_list = []
                for prob_record in order_prob_record:
                    problem_list.append(prob_record.problem)
                ##### 根据这些做对的题目来分组统计, 获取相应的题目标题和prob_submit_count的计数
                prob_group_count = ProblemRecords.objects.filter(test=test_record, problem__in=problem_list) \
                    .values("problem__title").annotate(count=Count("prob_submit_count"))
                ##### print(prob_group_count)
                ##### <QuerySet [{'problem__title': 'OO1-3 日期类Date', 'count': 4},
                # {'problem__title': 'A9-4  数组中第二大的数', 'count': 3},
                # {'problem__title': '硕哥的最短路', 'count': 3},
                ##### {'problem__title': '硕哥的电路图', 'count': 7}]>
                ########## 需要给prob_group_count按照'count'逆序排序 ##########
                prob_group_count = list(prob_group_count)
                prob_group_count.sort(key=lambda x: -x['count'])
                ##### min_prob_record = order_prob_record[0]
                ##### max_prob_record = order_prob_record[len(order_prob_record)-1]
                min_prob_record = prob_group_count[len(prob_group_count)-1]
                max_prob_record = prob_group_count[0]
                ##### current_min_submit_prob = min_prob_record.problem.title
                ##### current_min_submit_prob_count = min_prob_record.prob_submit_count
                ##### current_max_submit_prob = max_prob_record.problem.title
                ##### current_max_submit_prob_count = max_prob_record.prob_submit_count
                current_min_submit_prob = min_prob_record['problem__title']
                current_min_submit_prob_count = min_prob_record['count']
                current_max_submit_prob = max_prob_record['problem__title']
                current_max_submit_prob_count = max_prob_record['count']
            # ===========根据写入掌握情况时记录的current_user_to_concept_list获取用户掌握情况=========== #
            # 这个是测验交卷后写入的, 一定有值
            last_max_concept = -100
            last_max_concept_name = None
            last_min_concept = 100
            last_min_concept_name = None
            # max_improve = -100
            # max_improve_concept_id = None
            # max_drop = 100  # 其实就是提升最小的, 负值表示下降
            # max_drop_concept_id = None
            improve_concept_name = ''  # 不记录最大最小值, 而是记录下降提升的所有值
            drop_concept_name = ''
            for user_to_concept in current_user_to_concept_list:
                if user_to_concept.last_score is None:  # 第一次测验没有上一次记录, 就不用管了
                    continue
                if user_to_concept.last_score > last_max_concept:
                    last_max_concept_name = user_to_concept.concept.name
                    last_max_concept = user_to_concept.last_score
                if user_to_concept.last_score < last_min_concept:
                    last_min_concept_name = user_to_concept.concept.name
                    last_min_concept = user_to_concept.last_score
                # if (user_to_concept.current_score - user_to_concept.last_score)\
                #         > max_improve:
                #     max_improve_concept_id = user_to_concept.concept.name
                #     max_improve = user_to_concept.current_score - user_to_concept.last_score
                # if (user_to_concept.current_score - user_to_concept.last_score)\
                #         < max_drop:
                #     max_drop_concept_id = user_to_concept.concept.name
                #     max_drop = user_to_concept.current_score - user_to_concept.last_score
                if (user_to_concept.current_score - user_to_concept.last_score) > 0:
                    improve_concept_name += user_to_concept.concept.name + '、'
                # 不要等于0没变化的
                if (user_to_concept.current_score - user_to_concept.last_score) < 0:
                    drop_concept_name += user_to_concept.concept.name + '、'
            # for循环结束后如果name不为空, 则移除最后一个多余','
            if improve_concept_name:
                improve_concept_name = improve_concept_name[:-1]
            if drop_concept_name:
                drop_concept_name = drop_concept_name[:-1]
            TestReport.objects.create(
                user=user,
                test_date=Time,
                test=test_record,
                last_test_pass_rate=last_test_pass_rate,
                current_max_submit_prob=current_max_submit_prob,
                current_min_submit_prob=current_min_submit_prob,
                current_max_submit_prob_count=current_max_submit_prob_count,
                current_min_submit_prob_count=current_min_submit_prob_count,
                last_max_concept=last_max_concept_name,
                last_min_concept=last_min_concept_name,
                current_improve_concept=improve_concept_name,
                current_drop_concept=drop_concept_name,
                description=simulation_score,  # 用这个字段记录模拟测验得分
            )

    def post(self, request):
        # 返回给前端信息
        res = {
            'code': 404,
            'msg': "执行代码失败!",
            'data': {},  # 返回代码执行结果
        }
        username = request.user.username
        if not username:
            res['msg'] = "请先登录!"
            return res
        # ============获取当前用户信息============ #
        user = UserInfo.objects.get(username=username)

        Prob_Test = request.data.get("prob_test", None)
        Submit_Execute = request.data.get("submit_execute", None)
        cppStr_list = request.data.get("cppStr_list", None)
        prob_nid_list = request.data.get("prob_nid_list", None)
        Time = request.data.get("time", None)

        # DateTimeField TestRecord.create_date received a naive datetime (2022-06-09 03:57:32.568000) while time zone support is active.
        # 把13位时间戳转化成真正的时间日期格式  # django.core.exceptions.ValidationError:值有一个错误的日期格式
        Time = datetime.utcfromtimestamp(Time / 1000.0)
        # 警告RuntimeWarning: DateTimeField ModelName.field_name received a naive
        # datetime while time zone support is active  https://www.codenong.com/21038881/
        Time = timezone.make_aware(Time, timezone.get_current_timezone())

        # 构建写入文件路径
        proj_root_path, prob_code_path = self.get_file_path(username)

        # 执行ace代码, 获取结果
        print(prob_nid_list)
        prob_count = len(prob_nid_list)  # 做题数目
        prob_result_list, prob_pass_count, prob_score = self.execute_code(proj_root_path, prob_code_path, prob_count, Submit_Execute, cppStr_list, prob_nid_list)


        res['code'] = 200
        res['msg'] = "执行代码成功！"
        res['data'] = prob_result_list
        print(prob_result_list)
        # 如果是执行代码, 不用写入数据库, 直接返回
        if Submit_Execute == 'execute':
            return JsonResponse(res)

        # ============测验记录写入数据库============ #
        test_record = self.write_test_record(Prob_Test, Submit_Execute, Time, user, prob_count, prob_pass_count)

        # ============做题记录写入数据库, 同时修改Problem提交通过次数============ #
        self.write_prob_record_submitCount(Prob_Test, Submit_Execute, user, test_record,
                                           prob_count, prob_nid_list, prob_score)

        # 如果是测试时提交代码, 通过上面代码修改做题记录提交次数
        # 同时只修改做题记录提交次数, 不用调用KT模型
        # 这就有个问题就是test_records的prob_count和prob_pass_count有问题
        if Submit_Execute == 'test_submit':
            return JsonResponse(res)

        # ============获取用户做题记录, 构造KT模型输入============ #
        uid, probs_q,probs_c, resp, u2cs = self.get_kt_model_input(user)
        predict_probs = self.get_kt_model_predict_problem_input(user)
        print( predict_probs )
        # ============做题记录不足十道, 此下的都不用进行了============ #
        if len(probs_q) < 10:
            res['code'] = 404
            res['msg'] = '您还没有做够十道题!'
            return JsonResponse(res)
        # ============调用KT模型得到用户掌握情况============ #
        # print(probs)
        # print(len(probs))
        # print(resp)
        # print(len(resp))
        kt_output,kt_concept = kt_predict(probs_q, probs_c, resp)
        #kt_concept = kt_predict(probs_q, probs_c, resp)
        # KT_model_root_path = r'/home/tym/KT_Demo/'  # KT模型根目录
        # python_path = r'/home/tym/anaconda3/envs/tymEnv/bin/python3.7'  # 执行KT模型的python解释器路径
        # write_input_path = r'/home/lyz/tym_KT_Demo/kt_input'  # 输入写入路径
        # # 创建输入写入文件夹
        # if not os.path.exists(write_input_path):
        #     os.mkdir(write_input_path)
        # 写入输入KT模型数据
        # input_dict = {'uid':uid, 'probs':probs, 'resp':resp, 'probs_count':len(probs)}
        # with open(os.path.join(write_input_path, 'problem.txt'), 'w', encoding='utf-8') as f:
        #     f.write(str(input_dict))
        # # 写入输入KT模型预测题目数据
        # predict_probs_dict = {'predict_probs': predict_probs}
        # with open(os.path.join(write_input_path, 'predict_probs.txt'), 'w', encoding='utf-8') as f:
        #     f.write(str(predict_probs_dict))
        # 构建KT模型执行命令, 执行KT模型获得输出结果
        # cmd = f'cd {KT_model_root_path} && {python_path} predict.py'
        # with os.popen(cmd) as p:
        #     kt_output = p.read()
        print(kt_output)
        # print(type(kt_output))
        #kt_output = eval(kt_output)  # 把str类型的dict转换成真正的dict
        # kt_output = predict(uid, probs, resp, len(probs))
        # print(kt_output)
        # print(c)   # c = {'concept':{'1':...}, 'analyze':...,
        #                   'recommend_probs':..., 'concept_proportion':...}
        # """
        # # ## 服务器卡顿就用下面的, 在本机测试
        # # c = {'concept': {'1': 0.15188831090927124, '2': 0.27911025285720825, '3': 0.18293584883213043,
        # #                  '4': 0.4844967722892761, '5': 0.4073598384857178, '6': 0.19851331412792206,
        # #                  '7': 0.3065809905529022, '8': 0.016213631257414818, '9': 0.6485864520072937,
        # #                  '10': 0.031450241804122925, '11': 0.15941238403320312, '12': 0.6116441488265991,
        # #                  '13': 0.29673799872398376, '14': 0.22178688645362854, '15': 0.2272852659225464,
        # #                  '16': 0.516882598400116, '17': 0.3688444495201111},
        # #      'analyze': ['你总共做了15道编程练习题', '你通过了其中的4道题目', '你提交次数最多的题目是(1,1177)',
        # #                  '总共提交了9次才通过', '你提交次数最少的题目是(1,1009)', '提交了4次就通过了',
        # #                  '你对栈,队列的掌握情况比较好', '树相关的知识还需加强'],
        # #      'recommend_probs': ['1_1084', '8_1010', '8_1005', '8_1007', '8_1006'],
        # #      'concept_proportion': [0, 0.11904761904761904, 0.0380952380952381, 0.13333333333333333,
        # #                             0.01904761904761905, 0.047619047619047616, 0.0, 0.0, 0.0,
        # #                             0.0380952380952381, 0.0, 0.047619047619047616, 0.0380952380952381,
        # #                             0.01904761904761905, 0.0, 0.1761904761904762, 0.0, 0.12857142857142856,
        # #                             0.19523809523809524]}
        # # print(c['analyze'])
        # # """
        #
        # # ============掌握情况写入数据库============ #
        current_user_to_concept_list = self.write_user_to_concepts(Time, user, kt_concept)

        # # ============推荐题目写入数据库============ #
        # # 下面两句是有序插入推荐提目表, 导致dl_index界面显示不好看
        # self.test_write_reco_prob_order(user, test_type='weakness', max_test_prob_count=6)
        # # self.test_write_reco_prob_order(user, test_type='improve', max_test_prob_count=6)
        # # 下面这个函数是补弱提高间序插入推荐提目表
        self.test_write_reco_prob_no_order(user, max_test_prob_count=6)
        #
        # # ============测试报告写入数据库============ #
        self.write_test_report(Submit_Execute, Time, user, test_record, current_user_to_concept_list, int(kt_output))

        return JsonResponse(res)


class TestRecordsView(View):
    def get(self, request):
        # 返回给前端信息
        res = {
            'code': 404,
            'msg': "获取测试记录失败!",
            'data': None,  # 返回代码执行信息
        }
        username = request.user.username
        if not username:
            res['msg'] = "请先登录!"
            return res
        user = UserInfo.objects.get(username=username)
        get_type = request.GET.get('type', None)
        if get_type == 'count':
            print(user)
            test_record_query = TestRecord.objects.filter(user=user, category=1)
            res['code'] = 200
            res['msg'] = "获取测试记录成功!"
            res['data'] = len(test_record_query)
            return JsonResponse(res)
        return JsonResponse(res)


class IntelAnalyView(View):
    def python_post(self, request):
        # 返回给前端信息
        res = {
            'code': 404,
            'msg': "执行代码失败!",
            'data': None,  # 返回代码执行结果
        }
        username = request.user.username
        if not username:
            res['msg'] = "请先登录!"
            return res
        Time = request.data.get("time", None)
        PythonStr = request.data.get("python_str", None)

        root_path = './media/test_problem_upload/'
        if not os.path.exists(root_path):
            os.mkdir(root_path)
        prob_code_path = os.path.join(root_path, username)
        if not os.path.exists(prob_code_path):
            os.mkdir(prob_code_path)
        file_path = os.path.join(prob_code_path, 'problrem.py')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(PythonStr)
        with os.popen(f"python {file_path} 2>&1") as p:
            result = p.read()
        res['code'] = 200
        res['msg'] = "执行代码成功!"
        res['data'] = result
        return JsonResponse(res)

    def get_file_path(self, username):
        # ============linux系统g++编译运行命令和windows不同, 而且文件路径也不同============ #
        # 首先获取当前文件所在路径
        current_path = os.path.abspath(os.path.dirname(__file__))
        # 获取myProject，也就是项目的根路径
        proj_root_path = current_path[:current_path.find("knowledge_trace") + len("knowledge_trace")]
        file_absolute_path = '/media/test_problem_upload/'
        # 不知道为什么下面这句os.path.join失效了
        # file_root_path = os.path.join(proj_root_path, file_absolute_path)
        file_root_path = proj_root_path+file_absolute_path

        if not os.path.exists(file_root_path):
            os.mkdir(file_root_path)
        prob_code_path = os.path.join(file_root_path, username)
        if not os.path.exists(prob_code_path):
            os.mkdir(prob_code_path)
        return proj_root_path, prob_code_path

    def analyze(self, prob_count, Submit_Execute, cppStr_list, prob_nid_list):
        prob_result_list = []  # 返回结果list
        prob_pass_count = 0  # 通过题目数
        prob_score = []  # 题目做对与否

        for i in range(prob_count):
            result = {}  # pass, test_sample, user_out, ture_out
            # =========如果是最终交卷, 已经有结果了, 就不用执行下面语句了, 加快运行速度========= #
            if Submit_Execute == 'final_submit':
                # 之前提交结果存储在cppStr_list中, 没有提交的值为0, 所以把result['pass']放在if里直接赋值
                if cppStr_list[i] == 'AC':
                    result['pass'] = 'AC'
                    prob_pass_count += 1  # 这个有问题   ----   每次执行都会修正prob_pass_count, 最后就不用修改了
                    prob_score.append(1)
                else:
                    result['pass'] = 'CE'
                    prob_score.append(0)
                prob_result_list.append(result)
                # 跳过下面要执行的代码
                continue

            # =========如果不是最终交卷, 则需要执行代码判断正误, 且修改相应题目提交信息========= #
            prob = Problems.objects.get(nid=prob_nid_list[i])
            #problem_name = f'{prob.category}_{prob.id}'
            eq=prob.equation
            question=prob.desc

            # prob_cate_id.append((int(prob.category), int(prob.id)))
            # write ace code to file 把用户在ace输入的代码写入./media/test_problem_upload/problrem.cpp
            # with open(os.path.join(prob_code_path, 'problem.cpp'), 'w', encoding='utf-8') as f:
            #    f.write(str(cppStr_list[i]))
            out = ""
            out_1=""
            try:
                str1,flg=cppStr_list[i].split('\n')

                try:
                    out,out_1=get_answer(question,eq,str1)
                    result['msg'] = "智能分析加载成功！"
                except:
                    result['msg'] = "智能分析不太聪明！\n"
            except:
                result['msg'] = "输入格式有误\n"
            result['aly']=out
            result['ques'] = out_1
            prob_result_list.append(result)
            return prob_result_list

            # run code  运行代码，并且以./templates/my_tag/prob/judge/in/{problem_name}.in文件作为输入
            #result_in_root_path = proj_root_path + f'/templates/my_tag/prob/judge/in/{problem_name}.in'
            #cmd = f'cd {prob_code_path} && g++ problem.cpp -o problem 2>&1 && problem.exe < {result_in_root_path}'
            # with os.popen(cmd) as p:
            #     user_out = p.read()
            # get truth result  得到真实结果，./templates/my_tag/prob/judge/out/{problem_name}.out
            # result_out_root_path = proj_root_path + f'/templates/my_tag/prob/judge/out/{problem_name}.out'
            # with open(result_out_root_path, "r", encoding='UTF-8') as f:
            #     true_out = f.read()
            #     true_out = true_out.strip().replace('\n', '')

                # result = f'test_sample is \n{test_sample},\nuser_out is {user_out}, but expect out is {true_out}'
                # https://www.pianshen.com/article/6146632940/   innerHTML识别标签，innerText不识别标签
                # result = result.replace('\n', '<br/>')  # 插入<br/>在html换行https://bbs.csdn.net/topics/390763753
            # 读取测试样例, 仿照leetcode输出

    def post(self, request):
        # 返回给前端信息
        res = {
            'code': 404,
            'msg': "执行代码失败!",
            'data': {},  # 返回代码执行结果
        }
        username = request.user.username
        if not username:
            res['msg'] = "请先登录!"
            return res
        # ============获取当前用户信息============ #
        user = UserInfo.objects.get(username=username)


        Submit_Execute = request.data.get("submit_execute", None)
        cppStr_list = request.data.get("cppStr_list", None)
        prob_nid_list = request.data.get("prob_nid_list", None)
        Time = request.data.get("time", None)

        # 把13位时间戳转化成真正的时间日期格式  # django.core.exceptions.ValidationError:值有一个错误的日期格式
        Time = datetime.utcfromtimestamp(Time / 1000.0)
        Time = timezone.make_aware(Time, timezone.get_current_timezone())

        # 构建写入文件路径
        proj_root_path, prob_code_path = self.get_file_path(username)

        # 执行ace代码, 获取结果
        print(prob_nid_list)
        prob_count = len(prob_nid_list)  # 做题数目
        prob_result_list = self.analyze( prob_count, Submit_Execute, cppStr_list, prob_nid_list)


        res['code'] = 200
        res['msg'] = "执行代码成功！"
        res['data'] = prob_result_list
        print(prob_result_list)
        # 如果是执行代码, 不用写入数据库, 直接返回
        if Submit_Execute == 'execute':
            return JsonResponse(res)

        # ============测验记录写入数据库============ #
        # test_record = self.write_test_record(Prob_Test, Submit_Execute, Time, user, prob_count, prob_pass_count)
        #
        # # ============做题记录写入数据库, 同时修改Problem提交通过次数============ #
        # self.write_prob_record_submitCount(Prob_Test, Submit_Execute, user, test_record,
        #                                    prob_count, prob_nid_list, prob_score)

        # 如果是测试时提交代码, 通过上面代码修改做题记录提交次数
        # 同时只修改做题记录提交次数, 不用调用KT模型
        # 这就有个问题就是test_records的prob_count和prob_pass_count有问题
        if Submit_Execute == 'test_submit':
            return JsonResponse(res)



        # # ============测试报告写入数据库============ #
        # self.write_test_report(Submit_Execute, Time, user, test_record, current_user_to_concept_list, int(kt_output['score_pre']))

        return JsonResponse(res)


