# 植研小白盒 v3.0

植物生理生化实验一站式 Web 工具，面向实验新手，提供 Protocol 检索、试剂计算、Claude AI 问答等功能。

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

### AI 问答助手 (Claude AI)
- 接入 Anthropic Claude API，提供专业的植物实验问答
- 自动检索 Protocol 知识库作为上下文，回答更精准
- 支持多轮对话历史
- 未配置 API Key 时自动回退到本地规则引擎

### 数据处理中心
- 内置常用统计分析工具，支持实验数据的快速处理

### 实验日志
- 记录实验过程、结果和心得
- 支持查看历史记录

### 仪器操作指南
- 常用实验仪器的可视化操作指南
- 图文并茂，适合新手快速上手

### 导出功能
- 支持将 Protocol 导出为 Word（.docx）和 Markdown（.md）格式
- 支持将数据处理结果导出为 Excel（.xlsx）

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

# (可选) 配置 Claude AI
export ANTHROPIC_API_KEY=sk-ant-xxx

# 启动服务
python app.py
```

浏览器访问 http://localhost:5000

### Vercel 部署

1. Fork 本仓库
2. 在 Vercel 中导入项目
3. (可选) 在 Environment Variables 中添加 `ANTHROPIC_API_KEY`
4. 部署完成

## 项目结构

```
├── app.py                  # Flask 应用入口（工厂模式）
├── config.py               # 配置管理
├── routes/                 # 路由模块（Blueprint）
│   ├── __init__.py         # Blueprint 注册
│   ├── auth.py             # 认证路由（登录/注册/个人中心）
│   ├── protocol.py         # Protocol 路由（展示/搜索/收藏/评分）
│   ├── calculator.py       # 试剂计算器 API
│   ├── ai.py               # AI 问答路由
│   ├── instrument.py       # 仪器指南路由
│   ├── journal.py          # 实验日志路由
│   ├── admin.py            # 管理后台路由
│   └── export.py           # 导出路由（MD/DOCX/Excel）
├── services/               # 业务逻辑层
│   ├── database.py         # 数据库连接管理（context manager）
│   ├── cache.py            # 内存缓存（TTL）
│   ├── protocol_service.py # Protocol 解析与缓存
│   ├── search_service.py   # 搜索服务（批量查询优化）
│   └── ai_service.py       # AI 服务（Claude API + 本地回退）
├── data/                   # 数据层
│   ├── protocol_meta.py    # Protocol 元数据（65 条）
│   ├── instrument_meta.py  # 仪器元数据（10 条）
│   ├── reagent_db.py       # 试剂分子量数据库
│   └── svg_icons.py        # 仪器 SVG 图标
├── protocol_docs/          # 65 个 Protocol 文档（P001-P065）
├── templates/              # Jinja2 HTML 模板
├── static/css/style.css    # 全局样式
├── requirements.txt        # Python 依赖
└── vercel.json             # Vercel 部署配置
```

## 技术栈

- **后端**: Python / Flask（Blueprint 模块化）
- **前端**: HTML / CSS / JavaScript（Jinja2 模板）
- **数据库**: SQLite（用户系统）
- **部署**: Vercel（Serverless）
- **AI**: Anthropic Claude API（claude-sonnet-4-20250514）

## v3.0 架构优化

### 代码架构
- 从 1607 行单文件拆分为模块化 Blueprint 架构
- 数据/服务/路由三层分离，职责清晰
- Flask 应用工厂模式，便于测试和扩展

### 性能优化
- Protocol 文件内存缓存（TTL 5 分钟），避免每次请求读磁盘
- 搜索结果缓存（TTL 2 分钟）
- 搜索 API 批量查询收藏数和评分，消除 N+1 问题
- 数据库连接使用 context manager，杜绝连接泄漏

### AI 能力
- 接入 Claude API 实现真正的智能问答
- 自动检索 Protocol 知识库作为上下文
- 支持多轮对话
- 未配置 API Key 时自动回退到本地规则引擎

### 代码质量
- 消除重复代码（默认回答块）
- 统一错误处理
- 输入验证增强

## 更新日志

### v3.0 (2026-05-18)
- 架构重构：单文件拆分为 Blueprint 模块化架构
- 接入 Claude API 实现真正的 AI 问答
- 性能优化：缓存 + 批量查询
- 代码质量提升

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
