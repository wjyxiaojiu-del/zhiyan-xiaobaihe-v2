"""Protocol 解析与管理 - 带缓存"""
import os
from config import PROTOCOL_DIR
from services.cache import protocol_cache


def parse_protocol(filepath):
    """解析 Protocol txt 文件，按 section 返回结构化内容（带缓存）"""
    cached = protocol_cache.get(filepath)
    if cached is not None:
        return cached

    if not os.path.exists(filepath):
        return None

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    sections = {
        "meta": {}, "principle": "", "source": "", "instruments": "",
        "reagents": "", "formula": "", "steps": [], "safety": "",
        "tips": "", "data": "", "troubleshoot": "",
    }

    section_map = {
        "一、": "principle", "二、": "principle_inner", "三、": "source",
        "四、": "instruments", "五、": "reagents", "六、": "formula",
        "七、": "steps", "八、": "safety", "九、": "tips",
        "十、": "data", "十一、": "troubleshoot",
    }

    current_section = None
    buffer = []

    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("Protocol编号"):
            sections["meta"]["id"] = stripped.split("：")[-1].strip() if "：" in stripped else stripped.split(":")[-1].strip()
        elif stripped.startswith("实验名称"):
            sections["meta"]["name"] = stripped.split("：")[-1].strip() if "：" in stripped else stripped.split(":")[-1].strip()
        else:
            matched = False
            for prefix, sec_name in section_map.items():
                if stripped.startswith(prefix):
                    if current_section and buffer:
                        if current_section == "steps":
                            sections["steps_raw"] = "\n".join(buffer)
                        else:
                            sections[current_section] = "\n".join(buffer)
                    current_section = sec_name
                    buffer = []
                    matched = True
                    break
            if not matched:
                buffer.append(line)

    if current_section and buffer:
        if current_section == "steps":
            sections["steps_raw"] = "\n".join(buffer)
        else:
            sections[current_section] = "\n".join(buffer)

    # 解析步骤为结构化列表
    steps_raw = sections.get("steps_raw", sections.get("steps", ""))
    if isinstance(steps_raw, str):
        parsed_steps = []
        current_step = None
        for line in steps_raw.split("\n"):
            stripped = line.strip()
            if stripped.startswith("步骤"):
                if current_step:
                    parsed_steps.append(current_step)
                current_step = {"title": stripped, "why": "", "how": "", "correct": "", "wrong": ""}
            elif current_step:
                if stripped.startswith("为什么"):
                    current_step["why"] = stripped.split("：")[-1].strip() if "：" in stripped else stripped[3:]
                elif stripped.startswith("做对了"):
                    current_step["correct"] = stripped.split("：")[-1].strip() if "：" in stripped else stripped[3:]
                elif stripped.startswith("做错了"):
                    current_step["wrong"] = stripped.split("：")[-1].strip() if "：" in stripped else stripped[3:]
                elif not any(stripped.startswith(k) for k in ["为什么", "做对了", "做错了", "步骤"]):
                    current_step["how"] = (current_step["how"] + " " + stripped) if current_step["how"] else stripped
        if current_step:
            parsed_steps.append(current_step)
        sections["steps"] = parsed_steps

    protocol_cache.set(filepath, sections)
    return sections


def get_protocol_content(meta):
    """获取 Protocol 原始文本内容（带缓存）"""
    filepath = os.path.join(PROTOCOL_DIR, meta["file"])
    cache_key = f"raw:{filepath}"
    cached = protocol_cache.get(cache_key)
    if cached is not None:
        return cached

    if not os.path.exists(filepath):
        return ""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    protocol_cache.set(cache_key, content)
    return content
