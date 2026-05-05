# 植研小白盒 v1.0

植物生理生化实验一站式Web工具，面向实验新手，提供Protocol检索、试剂计算、AI问答等功能。

## 功能

- **Protocol库** — 65个标准化实验Protocol，涵盖植物生理、生化、分子生物学三大方向
- **智能检索** — 关键词全文搜索，按相关度排序，支持多关键词组合
- **Protocol详情** — 分Tab展示原理、操作步骤、试剂配方、避坑指南、数据处理
- **试剂计算器** — 6种常用计算（稀释、摩尔浓度、百分比、母液配制等）
- **导出功能** — 支持导出为Word（.docx）和Markdown（.md），适合打印
- **AI问答** — 基于Protocol知识库的实验问题解答
- **仪器指南** — 常用实验仪器的可视化操作指南

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python app.py
```

浏览器访问 http://localhost:5000

## 项目结构

```
├── app.py                  # Flask主程序
├── protocol_docs/          # 65个Protocol文档（P001-P065）
├── templates/              # HTML模板
│   ├── base.html           # 基础布局
│   ├── home.html           # 首页
│   ├── search.html         # 检索页
│   ├── protocol.html       # Protocol详情页
│   ├── calculator.html     # 试剂计算器
│   ├── export.html         # 导出页
│   ├── ai.html             # AI问答
│   ├── instruments.html    # 仪器列表
│   └── instrument.html     # 仪器详情
├── static/                 # 静态资源（CSS/JS/图片）
├── instrument_guides/      # 仪器操作指南文档
└── requirements.txt        # Python依赖
```

## 数据来源

Protocol数据基于李合生《植物生理生化实验原理和技术》教材整理，结合实验室常用操作规范。

## License

MIT
