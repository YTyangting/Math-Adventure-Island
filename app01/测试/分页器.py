from urllib.parse import urlencode
import math


class Pagination:

    def __init__(self, current_page, all_count, base_url, query_params, per_page=20, pager_page_count=11):
        """
        current_page: 当前页码
        all_count: 数据库中的总条数
        base_url: 原始URL
        query_params: 保留原搜索条件
        per_page: 一页展示多少条
        paper_page_count: 最多显示多少个页码
        """
        self.all_count = all_count
        self.per_page = per_page

        # 计算一共有多少个页码, ceil会自动向上取整(可以判断余数是否为0, 不为0加1即可)
        self.current_count = math.ceil(all_count / per_page)

        # 1.只能是满足条件的数字, 首先是数字然后大于0小于等于最大页码数
        try:
            self.current_page = int(current_page)
            if not 0 < self.current_page <= self.current_count:
                self.current_page = 1
        except Exception:
            self.current_page = 1

        self.base_url = base_url
        self.query_params = query_params
        self.pager_page_count = pager_page_count

        # 分页的中值
        self.half_page_count = int(self.pager_page_count / 2)
        # 如果可分页页码数小于想展示的分页块数目, 就让想显示页码变成可分页页码
        if self.current_count < self.pager_page_count:
            self.pager_page_count = self.current_count

    def page_html(self):
        # 计算页码的起始和结束(例如在第7页, 页码只展示56789这几个)
        # 分类讨论
        # 正常情况, 如想展示11个, 激活分页左右各5个
        start = self.current_page - self.half_page_count
        end = self.current_page + self.half_page_count
        # 最左侧情况
        if self.current_page <= self.half_page_count:
            start = 1
            # 此处因为已经判断过current_count与pager_page_count了, 所以直接赋值
            end = self.pager_page_count
        # 最右侧情况
        if self.current_page + self.half_page_count >= self.current_count:
            start = self.current_count - self.pager_page_count + 1
            end = self.current_count
        # print(start, end)
        # 生成分页
        page_list = []
        # 生成分页上一页
        if self.current_page != 1:
            self.query_params['page'] = self.current_page - 1
            li = f'<li><a href="{self.base_url}?{self.query_encode}">上一页</a></li>'
            page_list.append(li)

        # 生成分页数字部分
        for i in range(start, end+1):
            self.query_params['page'] = i
            if self.current_page == i:
                li = f'<li class="active"><a href="{self.base_url}?{self.query_encode}">{i}</a></li>'
            else:
                li = f'<li><a href="{self.base_url}?{self.query_encode}">{i}</a></li>'
            page_list.append(li)

        # 生成分页下一页
        if self.current_page != self.current_count:
            self.query_params['page'] = self.current_page + 1
            li = f'<li><a href="{self.base_url}?{self.query_encode}">下一页</a></li>'
            page_list.append(li)
        # print(page_list)
        return ''.join(page_list)

    @property
    def query_encode(self):
        return urlencode(self.query_params)

    @property  # 有这个装饰器调用函数就不用加括号了
    def start(self):  # 每页展示切片起始值
        return (self.current_page - 1) * self.per_page

    @property
    def end(self):  # 每页展示切片结束值
        return self.current_page * self.per_page


if __name__ == '__main__':
    # 测试
    pager = Pagination(
        current_page=1,
        all_count=100,
        base_url='',
        query_params={'tag': 'python'},
        per_page=5,
        pager_page_count=9
    )
    print(pager.page_html())


