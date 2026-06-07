import json
import mysql.connector
import pandas as pd
# 连接到MySQL数据库
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='123456',
    database='kt'
)
cursor = conn.cursor()


# 读取 JSON 文件
data = pd.read_json("combined_data.json", orient='records', lines=True)

# 假设JSON结构如下：[{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]
df=[]
df1=[]
for i in range(len(data)):
    if data["classification"][i]=="class1":
        df.append(109)
        df1.append(1)
    elif data["classification"][i]=="class2":
        df.append(110)
        df1.append(2)
    elif data["classification"][i]=="class3":
        df.append(111)
        df1.append(3)
    elif data["classification"][i]=="class4":
        df.append(112)
        df1.append(4)
    else:
        df.append(113)
        df1.append(5)

# cursor.execute('''DROP TABLE IF EXISTS `app01_problems2concepts`;
# CREATE TABLE `app01_problems2concepts`  (
#   `nid` int NOT NULL AUTO_INCREMENT,
#   `concept_id` int NOT NULL,
#   `problem_id` int NULL DEFAULT NULL,
#   PRIMARY KEY (`nid`) USING BTREE
# )''')

# cursor.execute('''
# CREATE TABLE IF not EXIT `app01_problems `  (
#   `nid` int NOT NULL AUTO_INCREMENT,
#   `category` int NULL DEFAULT NULL,
#   `id` int NULL DEFAULT NULL,
#   `difficulty` int NULL DEFAULT NULL,
#   `create_date` datetime(6) NOT NULL,
#   `origin` TEXT NULL DEFAULT NULL,
#   `pass_count` int NOT NULL,
#   `submit_count` int NOT NULL,
#   `desc` TEXT NULL,
#   `equation` TEXT NULL,
#   `segmented_text` TEXT NULL,
#   PRIMARY KEY (`nid`) ''')
# user_id={}
# cursor.execute('SELECT id FROM app01_problems')
# user_id["id"]=[ row[0] for row in cursor.fetchall()]
# cursor.execute('SELECT nid FROM app01_problems')
# user_id["nid"] = [row[0] for row in cursor.fetchall()]
# print(user_id["nid"] )
# for i in range(len(data)):
#     for j in range(len(user_id["id"])):
#         if int(data['id'][i])==int(user_id["id"][j]):
#             sql = "INSERT INTO temp (concept_id,prombles_id) VALUES ( %s,%s)"
#             val = (int(df[i]), int(user_id["nid"][j]))
#             cursor.execute(sql, val)

# for i in range(len(data)):
#    sql = "INSERT INTO app01_problem (category,id,desc,equation,segmented_text) VALUES (%s,%s,%s,%s,%s)"
#    val = (int(df1[i]),int(data['id'][i]),data['original_text'][i],data['equation'][i],data['segmented_text'][i])
#    cursor.execute(sql, val)
#
# user_id={}
# cursor.execute('SELECT nid FROM app01_problems')
# user_id["nid"] = [row[0] for row in cursor.fetchall()]
# for i in range(len(data)):
#             sql = "INSERT INTO app01_problems2concepts (concept_id,problem_id) VALUES ( %s,%s)"
#             val = (int(df[i]), int(user_id["nid"][i]))
#             cursor.execute(sql, val)
#

for i in range(len(data)):
    cursor.execute("UPDATE app01_problems SET category = %s WHERE id = %s", (str(df1[i]), str(data['id'][i])))


# 提交事务e
conn.commit()

# 关闭连接
cursor.close()
conn.close()
