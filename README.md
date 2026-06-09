
# 🏝️ 数学冒险岛 - 智慧教育平台系统 (Math Adventure Island)

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Vue.js](https://img.shields.io/badge/Frontend-Vue.js-4FC08D.svg?logo=vue.js)](https://vuejs.org/)
[![Django](https://img.shields.io/badge/Backend-Django-092E20.svg?logo=django)](https://www.djangoproject.com/)
[![MySQL](https://img.shields.io/badge/Database-MySQL-4479A1.svg?logo=mysql&logoColor=white)](https://www.mysql.com/)

> **数学冒险岛 (Math Adventure Island)** 是一个集游戏化学习、智能测评与个性化推荐于一体的智慧教育平台系统。本项目致力于打破传统数学学习的枯燥感，让学生在“闯关冒险”的过程中掌握数学知识，同时为教师提供精准的学情追踪与智能辅助教学工具。
> 

## 📖 项目简介 (Introduction)

在“数学冒险岛”中，每一个数学知识点都被设计成一个岛屿或关卡。学生通过答题闯关来获取积分和成就，平台后台则会根据学生的答题轨迹，运用**知识追踪（Knowledge Tracing）**和**大模型智能分析**，实时评估学生的知识掌握状态，并动态推荐适合的练习题。

本平台不仅是一个学习工具，更是一个连接学生、教师与家长的智慧生态系统。
![主页](./media/article_img/主页界面.png)
### ✨ 核心功能亮点 (Core Features)

* **🎮 游戏化学习引擎**：将枯燥的数学题转化为冒险关卡，支持积分榜、成就徽章和虚拟奖励，极大提升学生的学习内在驱动力。
* **🧠 智能知识追踪 (AI Knowledge Tracing)**：基于深度学习模型，动态追踪学生对各个数学概念（如代数、几何、概率）的掌握程度，精准定位知识薄弱点。
* **📈 多维学情分析看板**：为教师和家长提供可视化的学习报告，直观展示学习进度、能力雷达图和易错题分析。
* **🤖 AI 伴学助手**：集成大语言模型（LLM），在学生卡壳时提供“苏格拉底式”的引导和提示，而不是直接给出答案。
![登录](./media/article_img/登录界面.png)
![题库](./media/article_img/题库界.png)
![AI教师](./media/article_img/智能教师模型分析界面.png)
![报告分析](./media/article_img/报告界面.png)
## 🛠️ 技术栈 (Tech Stack)

本项目采用前后端分离的架构设计，确保系统的高可用性和易扩展性：

* **前端 (Frontend)**: Vue 3, TailwindCSS, ECharts (用于数据可视化)
* **后端 (Backend)**: Python Django (负责 AI 模型推理和核心业务逻辑)
* **数据库 (Database)**: MySQL (业务数据), Redis (缓存与排行榜)
* **AI 与算法**: PyTorch (知识追踪模型), 接入大语言模型 API (如文心一言/通义千问/ChatGPT)

## 🚀 快速启动 (Quick Start)

### 1. 环境准备
请确保您的本地开发环境已安装以下软件：
* Node.js (v16+)
* Python (v3.9+) 
* MySQL (v8.0+)

### 2. 后端服务启动

```bash
# 进入后端目录
cd backend

# 安装 Python 依赖 (如果后端为 Python)
pip install -r requirements.txt

# 运行数据库迁移脚本并启动服务
python manage.py runserver

```

### 3. 前端服务启动

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动本地开发服务器
npm run dev

```

*(启动成功后，可在浏览器访问 `http://localhost:5173` 或控制台提示的地址预览平台)*

## 📂 目录结构 (Directory Structure)

```text
Math-Adventure-Island/
├── frontend/          # 前端用户界面与可视化大屏代码
├── backend/           # 后端业务逻辑与 API 接口
├── ai_models/         # 知识追踪与推荐算法模型脚本
├── database/          # 数据库 SQL 脚本与数据字典
└── docs/              # 项目详细设计文档与 API 手册

```

## 🤝 参与贡献 (Contributing)

我们欢迎任何形式的贡献！如果您有好的建议或发现了 Bug，请提交 Issue。如果您希望贡献代码：

1. Fork 本仓库
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 将您的更改推送到分支 (`git push origin feature/AmazingFeature`)
5. 发起一个 Pull Request
6. 
## Demo Video
```text
Math-Adventure-Island/
├── frontend/ 
    ├──media/
       ├──demo.mp4

```
## ✉️ 联系方式 (Contact)

项目负责人：[ting yang]
联系邮箱：[您的邮箱地址]

