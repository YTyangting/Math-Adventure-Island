# from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractUser


# from django.utils.html import format_html
# from django.db.models.signals import pre_delete  # 删除文件
# from django.dispatch.dispatcher import receiver  # 删除文件


# 用户表
class UserInfo(AbstractUser):
    nid = models.AutoField(primary_key=True)
    nick_name = models.CharField(max_length=16, verbose_name='昵称', null=True, blank=True)
    avatar_url = models.URLField(verbose_name='用户头像', help_text='可能是其他平台的头像', null=True, blank=True)
    tel = models.CharField(verbose_name='手机号', max_length=12, null=True, blank=True)
    score = models.FloatField(default=0, verbose_name='用户能力')  # 能力
    a_unique_id = models.CharField(verbose_name='id', help_text='其他平台的唯一登录id', max_length=64, null=True,
                                   blank=True)

    # 可以不用要这两个字段, 直接Users2Concepts里查询, 然后用max得出来也可以
    # 省的用户知识点掌握情况变了还要修改这两个值
    # 最后想想还是增加这两个字段, 方便查询展示, 同一个表两个字段外键不能相同, 只能弄成普通的了
    max_concept_id = models.IntegerField(verbose_name='用户掌握最好知识点id', null=True, blank=True)
    min_concept_id = models.IntegerField(verbose_name='用户掌握最差知识点id', null=True, blank=True)

    sign_choice = (
        (0, '用户名注册'),
        (1, 'QQ注册'),
        (2, 'gitee注册'),
        (3, '手机号注册'),
        (4, '邮箱注册'),
    )
    sign_status = models.IntegerField(default=0, choices=sign_choice, verbose_name='注册方式')
    account_status_choice = (
        (0, '账号正常'),
        (1, '账号异常'),
        (2, '账号被封禁'),
    )
    account_status = models.IntegerField(default=0, choices=account_status_choice, verbose_name='账号状态')

    # =====因为没有这两张表, 外键关联报错:isinstance() arg 2 must be a type or tuple of types===== #
    # =====http://www.136.la/shida/show-202630.html===== #
    # avatar = models.ForeignKey(
    #     to='Avatars',
    #     to_field='nid',
    #     on_delete=models.SET_NULL,
    #     verbose_name='用户头像',
    #     null=True,
    #     blank=True,
    # )
    # collects = models.ManyToManyField(
    #     to='Articles',
    #     verbose_name='收藏的文章',
    #     blank=True
    # )

    class Meta:
        verbose_name_plural = '用户'


# 题目表
class Problems(models.Model):
    nid = models.AutoField(primary_key=True)
    category = models.CharField(verbose_name='题目类别', max_length=128, null=True, blank=True)
    id = models.CharField(verbose_name='题目编号', max_length=128, null=True, blank=True)
    category_choice = (
        (0, '简单'),
        (1, '中等'),
        (2, '提高'),
    )
    difficulty = models.IntegerField(verbose_name='题目难度', choices=category_choice, null=True, blank=True)
    # difficulty = models.FloatField(verbose_name='题目难度', null=True, blank=True)
    # concept = models.ManyToManyField(to='Concepts', null=True, blank=True)
    create_date = models.DateTimeField(verbose_name='题目创建时间', auto_now_add=True)
    origin = models.CharField(verbose_name='题目来源', max_length=128, null=True, blank=True)
    pass_count = models.IntegerField(verbose_name='题目通过次数', default=0)  # 通过通过和提交次数计算通过率
    submit_count = models.IntegerField(verbose_name='题目提交次数', default=0)
    title = models.CharField(verbose_name='题目标题', max_length=128, null=True, blank=True)
    desc = models.TextField(verbose_name='题目描述', null=True, blank=True)
    equation = models.TextField(verbose_name='等式', null=True, blank=True)
    segmented_text = models.TextField(verbose_name='语义题目', max_length=128, null=True, blank=True)
    input = models.TextField(verbose_name='题目输入描述', null=True, blank=True)
    output = models.TextField(verbose_name='题目输出描述', null=True, blank=True)
    input_sample = models.TextField(verbose_name='题目输入样例', null=True, blank=True)
    output_sample = models.TextField(verbose_name='题目输出样例', null=True, blank=True)
    html_path = models.CharField(verbose_name='题目对应html路径', max_length=128, null=True, blank=True)
    img_path = models.CharField(verbose_name='题目图片路径', max_length=128, null=True, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = '题目'


# 知识点表
class Concepts(models.Model):
    nid = models.AutoField(primary_key=True)
    name = models.CharField(verbose_name='知识点名称', max_length=128, null=True, blank=True)
    id = models.IntegerField(verbose_name='知识点在csv中的id', null=True, blank=True)
    img_path = models.CharField(verbose_name='知识点图片路径', max_length=128, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = '知识点'


# 做题记录表
class ProblemRecords(models.Model):
    nid = models.AutoField(primary_key=True)
    user = models.ForeignKey(verbose_name='做题用户', to='UserInfo', to_field='nid', on_delete=models.CASCADE)
    problem = models.ForeignKey(verbose_name='题号', to='Problems', to_field='nid', on_delete=models.CASCADE)
    score = models.FloatField(verbose_name='得分', null=True, blank=True)  # 对或错?
    code_path = models.CharField(verbose_name='题目上传代码路径', max_length=128, null=True, blank=True)
    # test字段为null或空表示普通做题
    test = models.ForeignKey(verbose_name='测验表号', to='TestRecord', to_field='nid',
                             on_delete=models.CASCADE, null=True, blank=True)
    # 方便test报告时查询用户最多题目提交次数
    # =========== 对于同一道题目, 一个用户应该有多条做题记录, 其中一条是平时做题test=NULL, 其它的是不同test对应的做题记录 =========== #
    prob_submit_count = models.IntegerField(verbose_name='当前用户提交这道题目次数', default=0)
    create_date = models.DateTimeField(verbose_name='做题时间', auto_now_add=True)

    def __str__(self):
        return f'用户{self.user}做了题目{self.problem}'

    class Meta:
        verbose_name_plural = '做题记录'


# 题目知识点表
class Problems2Concepts(models.Model):
    nid = models.AutoField(primary_key=True)
    problem = models.ForeignKey(verbose_name='题号', to='Problems', to_field='nid', on_delete=models.CASCADE)
    concept = models.ForeignKey(verbose_name='知识点号', to='Concepts', to_field='nid', on_delete=models.CASCADE)

    def __str__(self):
        return f'题目{self.problem}包含知识点{self.concept}'

    class Meta:
        verbose_name_plural = '题目知识点表'


# 用户知识点表
class Users2Concepts(models.Model):
    nid = models.AutoField(primary_key=True)
    user = models.ForeignKey(verbose_name='用户', to='UserInfo', to_field='nid', on_delete=models.CASCADE)
    concept = models.ForeignKey(verbose_name='知识点号', to='Concepts', to_field='nid', on_delete=models.CASCADE)
    current_score = models.FloatField(verbose_name='当前掌握情况', default=0.0)
    # 第一次可能没有上一次掌握情况, 就为None
    last_score = models.FloatField(verbose_name='上一次掌握情况', null=True, blank=True)
    # 方便以后显示出用户知识点随时间变化情况
    # 想要自己填时间, 好像不能用这个auto_now_add=True
    add_date = models.DateTimeField(verbose_name='某次知识点掌握情况时间', null=True, blank=True)

    def __str__(self):
        return f'用户{self.user}对知识点{self.concept}当前掌握程度为{self.current_score}上一次为{self.last_score}'

    class Meta:
        verbose_name_plural = '题目知识点表'


# 测验记录表
class TestRecord(models.Model):
    nid = models.AutoField(primary_key=True)
    user = models.ForeignKey(verbose_name='用户', to='UserInfo', to_field='nid', on_delete=models.CASCADE)
    # 想要自己填时间, 好像不能用这个auto_now_add=True
    test_date = models.DateTimeField(verbose_name='测验时间', null=True, blank=True)
    # 本次测验提交题目数  用于计算正确率
    prob_count = models.IntegerField(verbose_name='用户本次测验提交题目数', default=0)
    # 本次测验通过题目数  用于计算正确率
    prob_pass_count = models.IntegerField(verbose_name='用户本次测验通过题目数', default=0)
    # 这个就是正确率啊
    score = models.FloatField(verbose_name='测验得分', null=True, blank=True)
    category_choice = (
        # ============为了解决有些用户只是在test界面提交, 而没有点最终交卷, 测试记录无效问题============ #
        (1, '有效测验记录'),  # 如果是最终交卷生成的TestRecord, 则为有效测验记录, 以后查询测验记录都需要有效的
        (2, '无效测验记录'),  # 如果是每次提交生成的TestRecord, 则为无效测验记录
    )
    category = models.IntegerField(verbose_name='题目类型', choices=category_choice, null=True, blank=True)
    # =========== 这四个值都应该存为做题记录的题目提交次数字段 =========== #
    # # 本次测验提交最多题目次数
    # prob_submit_max_count = models.IntegerField(verbose_name='用户本次测验提交最多题目次数', default=0)
    # # 本次测验提交最多题目id
    # prob_submit_max_count_id = models.IntegerField(verbose_name='用户本次测验提交最多题目id', default=0)
    # # 本次测验提交最少题目次数
    # prob_submit_min_count = models.IntegerField(verbose_name='用户本次测验提交最少题目次数', default=0)
    # # 本次测验提交最少题目id
    # prob_submit_min_count_id = models.IntegerField(verbose_name='用户本次测验提交最少题目id', default=0)

    comment = models.TextField(verbose_name='测验评价', null=True, blank=True)

    def __str__(self):
        return f'用户{self.user}的测验记录'

    class Meta:
        verbose_name_plural = '测验记录表'


# 推荐题目表
class ProblemsRecommendation(models.Model):
    nid = models.AutoField(primary_key=True)
    user = models.ForeignKey(verbose_name='用户', to='UserInfo', to_field='nid', on_delete=models.CASCADE)
    problem = models.ForeignKey(verbose_name='题号', to='Problems', to_field='nid', on_delete=models.CASCADE)
    category_choice = (
        (1, '提高'),
        (2, '补弱'),
    )
    category = models.IntegerField(verbose_name='题目类型', choices=category_choice, null=True, blank=True)
    img_path = models.CharField(verbose_name='推荐题目图片路径', max_length=128, null=True, blank=True)
    origin_choice = (
        (1, 'report'),  # 从report获得的推荐
        (2, 'test'),  # test界面测验交卷后写入的推荐(其实这两个应该是同一个, 先分开写吧)
    )
    origin = models.IntegerField(verbose_name='题目类型', choices=category_choice, null=True, blank=True)

    def __str__(self):
        return f'用户{self.user}的推荐题目'

    class Meta:
        verbose_name_plural = '推荐题目表'


# 测验题目表
class ProblemsTest(models.Model):
    nid = models.AutoField(primary_key=True)
    # user为null表明所有用户共享同一个测验题目
    user = models.ForeignKey(verbose_name='用户', to='UserInfo', to_field='nid', on_delete=models.CASCADE, null=True,
                             blank=True)
    problem = models.ForeignKey(verbose_name='题号', to='Problems', to_field='nid', on_delete=models.CASCADE)
    category_choice = (
        (1, '提高'),
        (2, '补弱'),
    )
    category = models.IntegerField(verbose_name='题目类型', choices=category_choice, null=True, blank=True)

    testCategory_choice = (
        (1, '普通测验'),  # null的也算普通测验
        (2, '模拟考试'),
    )
    testCategory = models.IntegerField(verbose_name='测验类型', choices=testCategory_choice, null=True, blank=True)

    simulationNum_choice = (
        (1, '模拟试卷1'),  # null的也算普通测验
        (2, '模拟试卷2'),
        (3, '模拟试卷3'),
    )
    simulationNum = models.IntegerField(verbose_name='模拟试卷序号', choices=simulationNum_choice, null=True,
                                        blank=True)

    def __str__(self):
        return f'用户{self.user}的测验题目'

    class Meta:
        verbose_name_plural = '测试题目表'


# 用户总体报告表
class Report(models.Model):
    nid = models.AutoField(primary_key=True)
    user = models.ForeignKey(verbose_name='用户', to='UserInfo', to_field='nid', on_delete=models.CASCADE)
    create_date = models.DateTimeField(verbose_name='报告生成时间', auto_now_add=True)
    description = models.TextField(verbose_name='报告文字信息', null=True, blank=True)
    data = models.TextField(verbose_name='生成报告图所用数据字典格式', null=True, blank=True)

    def __str__(self):
        return f'用户{self.user}的报告'

    class Meta:
        verbose_name_plural = '报告表'


# 测试报告表
class TestReport(models.Model):
    nid = models.AutoField(primary_key=True)
    user = models.ForeignKey(verbose_name='用户', to='UserInfo', to_field='nid', on_delete=models.CASCADE)
    test_date = models.DateTimeField(verbose_name='测试报告生成时间', null=True, blank=True)
    test = models.ForeignKey(verbose_name='测试记录', to='TestRecord', to_field='nid', on_delete=models.CASCADE)
    # 第一次测验没有就为None
    last_test_pass_rate = models.FloatField(verbose_name='上一次测验正确率', null=True, blank=True)
    # 这两条直接从test_record获取即可
    # current_test_pass_rate = models.FloatField(verbose_name='当前测验正确率', default=0.0)
    # current_test_prob_count = models.IntegerField(verbose_name='当前测验题目数', default=0)
    # 为空表示没有做对的题目
    current_max_submit_prob = models.CharField(verbose_name='本次测验提交次数最多题目title', max_length=128, null=True,
                                               blank=True)
    current_min_submit_prob = models.CharField(verbose_name='本次测验提交次数最少题目title', max_length=128, null=True,
                                               blank=True)
    current_max_submit_prob_count = models.IntegerField(verbose_name='本次测验提交次数最多题目次数', null=True,
                                                        blank=True)
    current_min_submit_prob_count = models.IntegerField(verbose_name='本次测验提交次数最少题目次数', null=True,
                                                        blank=True)
    last_max_concept = models.CharField(verbose_name='上一次测验用户掌握最好知识点name', max_length=128, null=True,
                                        blank=True)
    last_min_concept = models.CharField(verbose_name='上一次测验用户掌握最差知识点name', max_length=128, null=True,
                                        blank=True)
    current_improve_concept = models.CharField(verbose_name='这一次测验用户提升知识点name', max_length=128, null=True,
                                               blank=True)
    current_drop_concept = models.CharField(verbose_name='这一次测验用户下降知识点name', max_length=128, null=True,
                                            blank=True)
    description = models.TextField(verbose_name='报告文字信息', null=True, blank=True)
    data = models.TextField(verbose_name='生成报告图所用数据字典格式', null=True, blank=True)

    def __str__(self):
        return f'用户{self.user}的测试报告'

    class Meta:
        verbose_name_plural = '测试报告表'


# 用户总体报告表
class ShareData(models.Model):
    """
    用这个表存放一些信息, 方便读取处理
    """
    nid = models.AutoField(primary_key=True)
    user = models.ForeignKey(verbose_name='用户', to='UserInfo', to_field='nid', on_delete=models.CASCADE)
    dataSimulationProbNid = models.TextField(verbose_name='模拟测试的问题nid记录', null=True, blank=True)
