# # PIL
# # pip install pillow
#
# from PIL import Image, ImageDraw, ImageFont
# import string
# import random
# from io import BytesIO
#
#
# # 随机颜色
# def random_color():
#     r, g, b = random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
#     return r, g, b
#
#
# # 获取0-9数字和26个大小写字母
# str_all = string.digits + string.ascii_letters
#
#
# def random_code():
#     valid_code = ''  # 记录验证码, 方便后端校验
#     code_length = 4  # 验证码长度
#     width = 200  # 验证码图片宽度
#     height = 40  # 验证码图片高度
#     point_num = 80
#     line_num = 5
#
#     # 生成一个200×40的白色背景图片
#     img = Image.new('RGB', (width, height), color=(255, 255, 255))
#     # 生成一个和图片同大小的画布
#     draw = ImageDraw.Draw(img)
#     # 生成字体对象
#     font = ImageFont.truetype(font='./font/MexicanTequila.ttf', size=32)
#
#     # 绘制文字  文字位置(左上角为0,0点)  文字内容  颜色RGB  字体
#     for i in range(code_length):  # 每隔一定距离绘制一个文字
#         random_char = random.choice(str_all)
#         draw.text((i*30+20, 10), random_char, (0, 0, 0), font=font)
#         valid_code += random_char  # 把验证码拼接起来发给后端验证
#     # print(valid_code)
#
#     # 随机生成点
#     for i in range(point_num):
#         x, y = random.randint(0, width), random.randint(0, height)
#         draw.point((x, y), fill=random_color())
#
#     # 随机生成线
#     for i in range(line_num):
#         x1, y1 = random.randint(0, width), random.randint(0, height)
#         x2, y2 = random.randint(0, width), random.randint(0, height)
#         draw.line((x1, y1, x2, y2), fill=random_color())
#
#     # 创建一个内存句柄
#     f = BytesIO()
#     # 将图片保存到内存句柄中
#     img.save(f, 'PNG')
#     # img.save('new_img.png', 'PNG')
#     # 读取内存句柄
#     data = f.getvalue()
#
#
# if __name__ == '__main__':
#     random_code()
