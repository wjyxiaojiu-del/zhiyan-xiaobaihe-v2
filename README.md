# 植研小白盒 v2.0

植物生理生化实验一站式 Web 工具，面向实验新手，提供 Protocol 检索、试剂计算、AI 问答等功能。

**在线访问**: https://zhiyan-xiaobaihe-v2-git-master-wjyxiaojiu-dels-projects.vercel.app

## 功能一览

### Protocol 检索
- 65 个标准化实验 Protocol，涵盖植物生理、分子生物学、基础操作三大方向
- 关键词全文搜索，按相关度排序，支持多关键词组合
- Protocol 详情页分 Tab 展示：实验原理、操作步骤、试剂配方、避坑指南、数据处理
- 支持收藏 Protocol 和评分

### 试剂计算器
- **摩尔浓度 ↔ 质量换算** — 输入分子量、浓度、体积，自动计算所需质量
- **梯度稀释计算** — 输入母液浓度和目标浓度，给出取液量和加溶剂量
- **梯度稀释表生成** — 自动计算多级稀释方案
- **RPM ↔ RCF 互换** — 转速与相对离心力互算
- **母液配制计算** — 输入目标浓度和质量，计算所需溶剂体积
- **比活力计算** — ED50 与比活力互算

### 数据处理中心
- 内置常用统计分析工具，支持实验数据的快速处理

### 实验日志
- 记录实验过程、结果和心得
- 支持查看历史记录

### 仪器操作指南
- 常用实验仪器的可视化操作指南
- 图文并茂，适合新手快速上手

### AI 问答助手
- 基于 Protocol 知识库的实验问题解答
- 可以问实验操作、试剂配制、结果分析等问题

### 导出功能
- 支持将 Protocol 导出为 Word（.docx）和 Markdown（.md）格式
- 适合打印和分享

### 用户系统
- 注册 / 登录 / 个人中心
- 收藏 Protocol、实验日志管理
- 管理员后台（用户管理、密码重置）

## 快速开始

### 在线使用
直接访问：https://zhiyan-xiaobaihe-v2-git-master-wjyxiaojiu-dels-projects.vercel.app

### 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python app.py
```

浏览器访问 http://localhost:5000

## 项目结构

```
├── app.py                  # Flask 主程序（路由、API、用户系统）
├── protocol_docs/          # 65 个 Protocol 文档（P001-P065）
├── templates/              # Jinja2 HTML 模板
│   ├── base.html           # 基础布局（导航栏、全局样式）
│   ├── home.html           # 首页（Protocol 卡片网格 + 功能入口）
│   ├── search.html         # Protocol 检索页
│   ├── protocol.html       # Protocol 详情页
│   ├── calculator.html     # 试剂计算器
│   ├── data.html           # 数据处理中心
│   ├── export.html         # 导出页
│   ├── ai.html             # AI 问答
│   ├── journal.html        # 实验日志
│   ├── instruments.html    # 仪器列表
│   ├── instrument.html     # 仪器详情
│   ├── login.html          # 登录
│   ├── register.html       # 注册
│   ├── profile.html        # 个人中心
│   ├── admin.html          # 管理后台
│   └── pricing.html        # 会员页
├── static/css/style.css    # 全局样式
├── public/                 # Vercel 静态文件目录
├── instrument_guides/      # 仪器操作指南文档
├── requirements.txt        # Python 依赖
└── vercel.json             # Vercel 部署配置
```

## 技术栈

- **后端**: Python / Flask
- **前端**: HTML / CSS / JavaScript（Jinja2 模板）
- **数据库**: SQLite（用户系统）
- **部署**: Vercel（Serverless）
- **AI**: Anthropic Claude API

## 更新日志

### v2.0 (2026-05-07)
- 全面升级界面与交互体验
- 新增 AI 智能问答功能
- 新增实验日志功能
- 新增数据处理中心
- 完善仪器可视化操作指南
- 新增用户系统（注册/登录/收藏/评分）
- 新增管理员后台

### v1.0 (2026-05-05)
- 首次发布
- 65 个标准化实验 Protocol
- 试剂计算器与导出功能

## 数据来源

Protocol 数据基于李合生《植物生理生化实验原理和技术》教材整理，结合实验室常用操作规范。

## License

MIT
