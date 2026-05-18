"""AI 问答服务 - Claude API + 本地回退"""
import os
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

# 延迟导入 anthropic，未配置 API key 时不影响启动
_client = None


def _get_client():
    global _client
    if _client is None and ANTHROPIC_API_KEY:
        try:
            import anthropic
            _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        except ImportError:
            pass
    return _client


SYSTEM_PROMPT = """你是「植研小白盒」AI助手，专门帮助植物科研新手解决实验问题。

## 核心规则
1. **只回答植物/农学/生物化学方向的问题**，拒绝无关话题
2. **术语必须加通俗解释**，面向实验新手
3. **给精确数值，不给模糊范围**（如"加10.5mL"而非"加适量"）
4. **危险操作先说安全提醒**（如液氮、浓硫酸、紫外灯）
5. **每步告诉用户「做对了看到什么」「做错了看到什么」**
6. 回答使用 Markdown 格式，善用表格和列表

## 你的能力
- 解释实验原理和操作步骤
- 帮助计算试剂用量（摩尔浓度、稀释倍数等）
- 排查实验失败原因
- 推荐相关 Protocol
- 解读实验数据

## 回答风格
- 先给结论，再解释原因
- 用中文回答
- 如果用户问的问题不完整，追问具体细节
"""


def generate_answer(query, context="", history=None):
    """生成 AI 回答，优先使用 Claude API，回退到本地规则引擎"""
    client = _get_client()

    if client:
        return _call_claude(client, query, context, history)
    else:
        return _local_fallback(query, context)


def _call_claude(client, query, context, history=None):
    """调用 Claude API"""
    user_content = query
    if context:
        user_content = f"以下是可能相关的 Protocol 知识库内容：\n\n{context}\n\n用户问题：{query}"

    messages = []
    if history:
        for msg in history[-6:]:  # 最近 6 条对话
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
    messages.append({"role": "user", "content": user_content})

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        return response.content[0].text
    except Exception as e:
        # API 调用失败，回退到本地引擎
        return _local_fallback(query, context)


def _local_fallback(query, context):
    """本地规则引擎（Claude API 不可用时的回退方案）"""
    query_lower = query.lower()

    # 计算类问题
    if any(kw in query_lower for kw in ["算", "称", "配", "浓度", "稀释", "摩尔", "质量", "体积"]):
        answer = "### 试剂计算\n\n"
        answer += "请使用 **试剂计算器** 页面，支持以下功能：\n\n"
        answer += "| 计算类型 | 说明 |\n|---------|------|\n"
        answer += "| **稀释计算** | C1V1 = C2V2，支持 mM/uM/mg/mL 等单位 |\n"
        answer += "| **摩尔浓度** | 输入浓度+体积，自动算需称多少克 |\n"
        answer += "| **复溶计算** | 输入质量和目标浓度，算加多少溶剂 |\n"
        answer += "| **比活力计算** | 输入 ED50 值，算 Specific Activity |\n"
        answer += "| **单位换算** | 浓度、体积、rpm-rcf 互算 |\n\n"
        answer += "[点击打开试剂计算器](/calculator)\n\n"
        if context:
            answer += "**相关 Protocol 配方参考：**\n\n"
            for line in context.split("\n")[:15]:
                if line.strip():
                    answer += f"> {line.strip()}\n"
        return answer

    # 失败排查
    if any(kw in query_lower for kw in ["失败", "没有", "不出", "不对", "偏低", "偏高", "怎么办", "异常", "问题"]):
        answer = "### 实验失败排查\n\n"
        answer += "实验失败很常见！帮你定位问题，请告诉我：\n\n"
        answer += "1. **你做的什么实验？**\n2. **具体现象是什么？**\n3. **操作细节？**\n\n"
        answer += "| 现象 | 可能原因 | 解决方案 |\n|------|---------|----------|\n"
        answer += "| 标准曲线 R2<0.99 | 标准液配制不准 | 重新配制，每个点做 3 个重复 |\n"
        answer += "| OD 值>0.8 | 样品浓度太高 | 稀释样品后重测 |\n"
        answer += "| 没有显色 | 试剂失效/温度不够 | 检查试剂有效期，确保沸水浴 |\n"
        answer += "| DNA 条带模糊 | 降解/量太少 | 全程低温，增加样品量 |\n"
        answer += "| RNA 降解 | RNase 污染 | 全程 RNase-free 操作 |\n\n"
        if context:
            answer += "**相关 Protocol 避坑提示：**\n\n"
            for line in context.split("\n")[:15]:
                if line.strip() and any(kw in line for kw in ["做错", "避坑", "注意", "不要"]):
                    answer += f"> {line.strip()}\n"
        answer += "\n也可以在 [Protocol 库](/) 中查看对应实验的「避坑指南」Tab。"
        return answer

    # 有 Protocol 上下文时
    if context:
        answer = "### 找到相关 Protocol\n\n"
        lines = context.split("\n")
        for line in lines[:25]:
            if line.strip():
                answer += f"> {line.strip()}\n"
        answer += "\n---\n\n"
        answer += "在 [Protocol 库](/) 中可以查看完整内容，每个步骤都有详细的操作指南。\n"
        answer += "如果你有更具体的问题，请告诉我！"
        return answer

    # 默认回答
    return """### 你好！我是植研小白盒 AI 助手

我可以帮你解答植物实验相关的问题：

**试剂配制** - 帮你计算摩尔浓度、稀释倍数，告诉你具体称多少克、加多少溶剂

**实验操作** - 解释实验原理，指导操作步骤，说明每步「做对了看到什么」

**失败排查** - 分析实验失败原因，给出解决方案

**数据处理** - 标准曲线怎么做，数据怎么计算

试试问我：「配 100mL 0.1mol/L Tris 需要称多少克？」

> 提示：配置 ANTHROPIC_API_KEY 环境变量后，将启用 Claude AI 获得更智能的回答。"""
