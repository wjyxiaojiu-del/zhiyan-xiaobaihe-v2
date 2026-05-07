#!/usr/bin/env python3
"""构建静态GitHub Pages站点"""
import os
import re
import html

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROTOCOL_DIR = os.path.join(BASE_DIR, "protocol_docs")
OUTPUT_DIR = os.path.join(BASE_DIR, "_site")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "protocols"), exist_ok=True)

CSS = """
:root { --primary: #6B7C4E; --primary-light: #8FA465; --bg: #F5F0E8; --card: #FFFEF9; --text: #3D3229; --text-secondary: #8C7E6E; --border: #E4DFD6; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }
.container { max-width: 1200px; margin: 0 auto; padding: 0 1.5rem; }
nav { background: white; border-bottom: 1px solid var(--border); padding: 1rem 0; position: sticky; top: 0; z-index: 100; }
nav .container { display: flex; align-items: center; justify-content: space-between; }
nav .logo { font-size: 1.3rem; font-weight: 700; color: var(--primary); text-decoration: none; }
nav .nav-links { display: flex; gap: 1.5rem; }
nav .nav-links a { color: var(--text-secondary); text-decoration: none; font-weight: 500; font-size: 0.95rem; }
nav .nav-links a:hover { color: var(--primary); }
.hero { background: linear-gradient(135deg, #6B7C4E, #8FA465); color: white; text-align: center; padding: 4rem 1.5rem; }
.hero h1 { font-size: 2.5rem; margin-bottom: 0.5rem; }
.hero p { font-size: 1.1rem; opacity: 0.9; }
.stats { display: flex; justify-content: center; gap: 3rem; margin-top: 2rem; }
.stat-item { text-align: center; }
.stat-num { font-size: 2rem; font-weight: 700; }
.stat-label { font-size: 0.9rem; opacity: 0.8; }
.section { padding: 3rem 0; }
.section h2 { text-align: center; font-size: 1.8rem; margin-bottom: 0.5rem; color: var(--text); }
.section .subtitle { text-align: center; color: var(--text-secondary); margin-bottom: 2rem; }
.features { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.5rem; margin-bottom: 3rem; }
.feature-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; text-align: center; text-decoration: none; color: var(--text); transition: transform 0.2s, box-shadow 0.2s; }
.feature-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.1); }
.feature-card .icon { font-size: 2rem; margin-bottom: 0.5rem; }
.feature-card h3 { margin-bottom: 0.3rem; }
.feature-card p { color: var(--text-secondary); font-size: 0.9rem; }
.protocol-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1rem; }
.protocol-card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 1rem 1.2rem; text-decoration: none; color: var(--text); display: flex; gap: 0.8rem; align-items: flex-start; transition: transform 0.2s; }
.protocol-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.protocol-card .bar { width: 4px; border-radius: 2px; min-height: 50px; flex-shrink: 0; }
.protocol-card .bar.physiology { background: #6B7C4E; }
.protocol-card .bar.molecular { background: #5B7FA5; }
.protocol-card .bar.basic { background: #C49B5C; }
.protocol-card .id { font-weight: 700; color: var(--text-secondary); font-size: 0.85rem; }
.protocol-card .name { font-weight: 600; font-size: 0.95rem; }
.protocol-card .desc { color: var(--text-secondary); font-size: 0.8rem; margin-top: 0.3rem; }
.protocol-detail { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 2rem; margin: 2rem 0; }
.protocol-detail h1 { color: var(--primary); margin-bottom: 1rem; }
.protocol-detail h2 { color: var(--primary); font-size: 1.2rem; margin: 1.5rem 0 0.5rem; padding-bottom: 0.3rem; border-bottom: 2px solid var(--border); }
.protocol-detail p, .protocol-detail li { margin-bottom: 0.3rem; }
.protocol-detail ul { padding-left: 1.5rem; }
.warning { background: #FFF3CD; border-left: 4px solid #FFC107; padding: 1rem; border-radius: 0 8px 8px 0; margin: 1rem 0; }
.danger { background: #F8D7DA; border-left: 4px solid #DC3545; padding: 1rem; border-radius: 0 8px 8px 0; margin: 1rem 0; }
.back-link { display: inline-block; margin-bottom: 1rem; color: var(--primary); text-decoration: none; font-weight: 500; }
.back-link:hover { text-decoration: underline; }
footer { text-align: center; padding: 2rem; color: var(--text-secondary); font-size: 0.85rem; border-top: 1px solid var(--border); margin-top: 2rem; }
"""

PROTOCOLS = [
    {"id": "P001", "name": "蒽酮比色法测可溶性糖含量", "category": "植物生理", "color": "#6B7C4E", "desc": "用蒽酮试剂与糖反应显色，分光光度法测定", "difficulty": 2},
    {"id": "P002", "name": "Bradford法测可溶性蛋白", "category": "植物生理", "color": "#6B7C4E", "desc": "考马斯亮蓝G-250与蛋白质结合显色", "difficulty": 2},
    {"id": "P003", "name": "TBA法测MDA含量", "category": "植物生理", "color": "#6B7C4E", "desc": "硫代巴比妥酸反应法测定丙二醛", "difficulty": 2},
    {"id": "P004", "name": "POD活性测定", "category": "植物生理", "color": "#6B7C4E", "desc": "愈创木酚法测定过氧化物酶活性", "difficulty": 2},
    {"id": "P005", "name": "CAT活性测定", "category": "植物生理", "color": "#6B7C4E", "desc": "紫外吸收法测定过氧化氢酶活性", "difficulty": 2},
    {"id": "P006", "name": "植物基因组DNA提取", "category": "分子生物", "color": "#5B7FA5", "desc": "CTAB法提取植物基因组DNA", "difficulty": 3},
    {"id": "P007", "name": "PCR反应体系", "category": "分子生物", "color": "#5B7FA5", "desc": "PCR扩增体系配制与程序设置", "difficulty": 3},
    {"id": "P008", "name": "琼脂糖凝胶电泳", "category": "分子生物", "color": "#5B7FA5", "desc": "DNA/RNA琼脂糖凝胶电泳检测", "difficulty": 2},
    {"id": "P009", "name": "总RNA提取与反转录", "category": "分子生物", "color": "#5B7FA5", "desc": "TRIzol法提取总RNA并反转录为cDNA", "difficulty": 3},
    {"id": "P010", "name": "液氮研磨与母液配制", "category": "基础操作", "color": "#C49B5C", "desc": "液氮研磨样品与常用母液配制方法", "difficulty": 1},
    {"id": "P011", "name": "过氧化物酶活性测定_李合生法", "category": "植物生理", "color": "#6B7C4E", "desc": "李合生教材中的POD测定方法", "difficulty": 2},
    {"id": "P012", "name": "过氧化氢酶活性测定_滴定法", "category": "植物生理", "color": "#6B7C4E", "desc": "高锰酸钾滴定法测定CAT活性", "difficulty": 2},
    {"id": "P013", "name": "丙二醛含量测定_李合生法", "category": "植物生理", "color": "#6B7C4E", "desc": "李合生教材中的MDA测定方法", "difficulty": 2},
    {"id": "P014", "name": "可溶性糖含量测定_蒽酮法_李合生", "category": "植物生理", "color": "#6B7C4E", "desc": "李合生教材中的蒽酮比色法", "difficulty": 2},
    {"id": "P015", "name": "叶绿素含量测定_分光光度法", "category": "植物生理", "color": "#6B7C4E", "desc": "丙酮乙醇混合液提取法测定叶绿素", "difficulty": 2},
    {"id": "P016", "name": "可溶性蛋白质含量测定_考马斯亮蓝法", "category": "植物生理", "color": "#6B7C4E", "desc": "Bradford法测定可溶性蛋白", "difficulty": 2},
    {"id": "P017", "name": "呼吸速率测定_小篮子法", "category": "植物生理", "color": "#6B7C4E", "desc": "碱液吸收法测定呼吸速率", "difficulty": 3},
    {"id": "P018", "name": "DNA提取与测定_盐溶法", "category": "分子生物", "color": "#5B7FA5", "desc": "高盐低pH法提取DNA", "difficulty": 3},
    {"id": "P019", "name": "自由水和束缚水含量测定", "category": "植物生理", "color": "#6B7C4E", "desc": "马林契克法测定自由水和束缚水", "difficulty": 2},
    {"id": "P020", "name": "植物组织水势测定", "category": "植物生理", "color": "#6B7C4E", "desc": "小液流法测定组织水势", "difficulty": 2},
    {"id": "P021", "name": "植物组织渗透势测定", "category": "植物生理", "color": "#6B7C4E", "desc": "质壁分离法测定渗透势", "difficulty": 2},
    {"id": "P022", "name": "叶片相对含水量测定", "category": "植物生理", "color": "#6B7C4E", "desc": "饱和鲜重法测定相对含水量", "difficulty": 1},
    {"id": "P023", "name": "植物体内硝酸还原酶活性测定", "category": "植物生理", "color": "#6B7C4E", "desc": "活体法测定硝酸还原酶活性", "difficulty": 3},
    {"id": "P024", "name": "淀粉酶活性测定", "category": "植物生理", "color": "#6B7C4E", "desc": "DNS法测定淀粉酶活性", "difficulty": 2},
    {"id": "P025", "name": "植物体内脯氨酸含量测定", "category": "植物生理", "color": "#6B7C4E", "desc": "酸性茚三酮法测定脯氨酸", "difficulty": 2},
    {"id": "P026", "name": "植物体内可溶性糖含量测定_苯酚法", "category": "植物生理", "color": "#6B7C4E", "desc": "苯酚-硫酸法测定总糖", "difficulty": 2},
    {"id": "P027", "name": "植物体内淀粉含量测定", "category": "植物生理", "color": "#6B7C4E", "desc": "酸水解法测定淀粉含量", "difficulty": 2},
    {"id": "P028", "name": "植物体内维生素C含量测定", "category": "植物生理", "color": "#6B7C4E", "desc": "2,6-二氯酚靛酚滴定法", "difficulty": 2},
    {"id": "P029", "name": "植物体内过氧化氢含量测定", "category": "植物生理", "color": "#6B7C4E", "desc": "碘化钾法测定H₂O₂含量", "difficulty": 2},
    {"id": "P030", "name": "植物体内超氧化物歧化酶活性测定", "category": "植物生理", "color": "#6B7C4E", "desc": "NBT光化学还原法测定SOD活性", "difficulty": 3},
    {"id": "P031", "name": "植物体内抗坏血酸过氧化物酶活性测定", "category": "植物生理", "color": "#6B7C4E", "desc": "紫外吸收法测定APX活性", "difficulty": 3},
    {"id": "P032", "name": "植物体内谷胱甘肽还原酶活性测定", "category": "植物生理", "color": "#6B7C4E", "desc": "NADPH氧化法测定GR活性", "difficulty": 3},
    {"id": "P033", "name": "植物体内脱氢抗坏血酸含量测定", "category": "植物生理", "color": "#6B7C4E", "desc": "DTNB法测定DHA含量", "difficulty": 3},
    {"id": "P034", "name": "植物体内还原型抗坏血酸含量测定", "category": "植物生理", "color": "#6B7C4E", "desc": "分光光度法测定AsA含量", "difficulty": 2},
    {"id": "P035", "name": "植物体内类胡萝卜素含量测定", "category": "植物生理", "color": "#6B7C4E", "desc": "丙酮提取分光光度法", "difficulty": 2},
    {"id": "P036", "name": "植物体内花青素含量测定", "category": "植物生理", "color": "#6B7C4E", "desc": "pH示差法测定花青素", "difficulty": 2},
    {"id": "P037", "name": "植物体内酚类化合物含量测定", "category": "植物生理", "color": "#6B7C4E", "desc": "Folin-Ciocalteu法测定总酚", "difficulty": 2},
    {"id": "P038", "name": "植物体内黄酮含量测定", "category": "植物生理", "color": "#6B7C4E", "desc": "AlCl₃显色法测定总黄酮", "difficulty": 2},
    {"id": "P039", "name": "植物体内生物碱含量测定", "category": "植物生理", "color": "#6B7C4E", "desc": "酸性染料比色法测定生物碱", "difficulty": 3},
    {"id": "P040", "name": "植物体内皂苷含量测定", "category": "植物生理", "color": "#6B7C4E", "desc": "香草醛-硫酸比色法", "difficulty": 2},
    {"id": "P041", "name": "植物体内萜类化合物含量测定", "category": "植物生理", "color": "#6B7C4E", "desc": "比色法测定总萜类", "difficulty": 2},
    {"id": "P042", "name": "植物体内木质素含量测定", "category": "植物生理", "color": "#6B7C4E", "desc": "硫代巴比妥酸法测定木质素", "difficulty": 3},
    {"id": "P043", "name": "植物体内纤维素含量测定", "category": "植物生理", "color": "#6B7C4E", "desc": "浓酸水解法测定纤维素", "difficulty": 3},
    {"id": "P044", "name": "植物体内半纤维素含量测定", "category": "植物生理", "color": "#6B7C4E", "desc": "比色法测定半纤维素", "difficulty": 3},
    {"id": "P045", "name": "植物体内果胶含量测定", "category": "植物生理", "color": "#6B7C4E", "desc": "咔唑比色法测定果胶", "difficulty": 3},
    {"id": "P046", "name": "植物体内粗脂肪含量测定", "category": "植物生理", "color": "#6B7C4E", "desc": "索氏提取法测定粗脂肪", "difficulty": 2},
    {"id": "P047", "name": "植物体内粗蛋白含量测定", "category": "植物生理", "color": "#6B7C4E", "desc": "凯氏定氮法测定粗蛋白", "difficulty": 3},
    {"id": "P048", "name": "植物体内氨基酸含量测定", "category": "植物生理", "color": "#6B7C4E", "desc": "茚三酮比色法测定氨基酸", "difficulty": 2},
    {"id": "P049", "name": "植物体内有机酸含量测定", "category": "植物生理", "color": "#6B7C4E", "desc": "NaOH滴定法测定有机酸", "difficulty": 2},
    {"id": "P050", "name": "植物体内可溶性氮含量测定", "category": "植物生理", "color": "#6B7C4E", "desc": "纳氏试剂比色法", "difficulty": 2},
    {"id": "P051", "name": "植物体内非蛋白氮含量测定", "category": "植物生理", "color": "#6B7C4E", "desc": "TCA沉淀法测定非蛋白氮", "difficulty": 3},
    {"id": "P052", "name": "植物体内核酸含量测定", "category": "分子生物", "color": "#5B7FA5", "desc": "紫外吸收法测定核酸含量", "difficulty": 3},
    {"id": "P053", "name": "植物体内ATP含量测定", "category": "分子生物", "color": "#5B7FA5", "desc": "萤火虫荧光素酶法测定ATP", "difficulty": 3},
    {"id": "P054", "name": "植物体内ADP含量测定", "category": "分子生物", "color": "#5B7FA5", "desc": "酶偶联法测定ADP", "difficulty": 3},
    {"id": "P055", "name": "植物体内AMP含量测定", "category": "分子生物", "color": "#5B7FA5", "desc": "酶偶联法测定AMP", "difficulty": 3},
    {"id": "P056", "name": "植物体内NAD⁺含量测定", "category": "分子生物", "color": "#5B7FA5", "desc": "酶循环法测定NAD⁺", "difficulty": 3},
    {"id": "P057", "name": "植物体内NADH含量测定", "category": "分子生物", "color": "#5B7FA5", "desc": "酶循环法测定NADH", "difficulty": 3},
    {"id": "P058", "name": "植物体内NADP⁺含量测定", "category": "分子生物", "color": "#5B7FA5", "desc": "酶循环法测定NADP⁺", "difficulty": 3},
    {"id": "P059", "name": "植物体内NADPH含量测定", "category": "分子生物", "color": "#5B7FA5", "desc": "酶循环法测定NADPH", "difficulty": 3},
    {"id": "P060", "name": "植物体内GSH含量测定", "category": "分子生物", "color": "#5B7FA5", "desc": "DTNB法测定还原型谷胱甘肽", "difficulty": 3},
    {"id": "P061", "name": "植物体内GSSG含量测定", "category": "分子生物", "color": "#5B7FA5", "desc": "DTNB法测定氧化型谷胱甘肽", "difficulty": 3},
    {"id": "P062", "name": "植物体内硫醇含量测定", "category": "分子生物", "color": "#5B7FA5", "desc": "Ellman试剂法测定总硫醇", "difficulty": 3},
    {"id": "P063", "name": "植物体内金属离子含量测定", "category": "基础操作", "color": "#C49B5C", "desc": "原子吸收光谱法测定金属离子", "difficulty": 3},
    {"id": "P064", "name": "植物体内矿质元素含量测定", "category": "基础操作", "color": "#C49B5C", "desc": "ICP-OES法测定矿质元素", "difficulty": 3},
    {"id": "P065", "name": "植物体内水分含量测定", "category": "基础操作", "color": "#C49B5C", "desc": "烘干法测定水分含量", "difficulty": 1},
]

def parse_protocol(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    sections = {}
    current_section = None
    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        if re.match(r'^[一二三四五六七八九十]+、', line) or line.startswith("Protocol编号") or line.startswith("实验名称"):
            current_section = line
            sections[current_section] = []
        elif current_section:
            sections[current_section].append(line)
    return sections

def format_content(sections):
    html_parts = []
    for key, lines in sections.items():
        if key.startswith("Protocol编号") or key.startswith("实验名称"):
            continue
        html_parts.append(f"<h2>{html.escape(key)}</h2>")
        for line in lines:
            line = html.escape(line)
            if line.startswith("问题：") or line.startswith("- "):
                html_parts.append(f"<p>{line}</p>")
            else:
                html_parts.append(f"<p>{line}</p>")
    return "\n".join(html_parts)

def generate_index():
    cards_html = ""
    for p in PROTOCOLS:
        cat_class = "physiology" if p["category"] == "植物生理" else ("molecular" if p["category"] == "分子生物" else "basic")
        cards_html += f'''
        <a href="protocols/{p["id"]}.html" class="protocol-card">
            <div class="bar {cat_class}"></div>
            <div>
                <div class="id">{p["id"]}</div>
                <div class="name">{html.escape(p["name"])}</div>
                <div class="desc">{html.escape(p["desc"])}</div>
            </div>
        </a>'''

    content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>植研小白盒 v2.0 - 植物生理生化实验一站式工具</title>
<style>{CSS}</style>
</head>
<body>
<nav><div class="container">
    <a href="index.html" class="logo">🌿 植研小白盒</a>
    <div class="nav-links">
        <a href="index.html">首页</a>
        <a href="#protocols">Protocol库</a>
    </div>
</div></nav>

<section class="hero">
    <h1>🌿 植研小白盒 v2.0</h1>
    <p>进实验室不慌，有小白盒兜底 —— 你的随身实验室教练</p>
    <div class="stats">
        <div class="stat-item"><div class="stat-num">65</div><div class="stat-label">标准化Protocol</div></div>
        <div class="stat-item"><div class="stat-num">3</div><div class="stat-label">实验大类覆盖</div></div>
        <div class="stat-item"><div class="stat-num">10</div><div class="stat-label">仪器操作指南</div></div>
    </div>
</section>

<div class="container">
    <section class="section" id="features">
        <h2>功能介绍</h2>
        <p class="subtitle">面向实验新手的一站式解决方案</p>
        <div class="features">
            <div class="feature-card"><div class="icon">🔍</div><h3>Protocol检索</h3><p>输入实验问题，智能匹配最相关Protocol</p></div>
            <div class="feature-card"><div class="icon">🧪</div><h3>试剂计算器</h3><p>摩尔浓度换算、梯度稀释、复溶比活力一键搞定</p></div>
            <div class="feature-card"><div class="icon">🤖</div><h3>AI问答助手</h3><p>专属植物科研AI，解答问题、排查失败</p></div>
        </div>
    </section>

    <section class="section" id="protocols">
        <h2>标准化Protocol库</h2>
        <p class="subtitle">点击查看完整Protocol，每个步骤都有避坑指南</p>
        <div class="protocol-grid">{cards_html}</div>
    </section>
</div>

<footer>
    <p>植研小白盒 v2.0 | 基于李合生《植物生理生化实验原理和技术》整理</p>
    <p>MIT License</p>
</footer>
</body>
</html>"""
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(content)

def generate_protocol_pages():
    for p in PROTOCOLS:
        filepath = os.path.join(PROTOCOL_DIR, f"{p['id']}_{p['name'].replace('/', '_')}.txt")
        if not os.path.exists(filepath):
            # Try finding by ID prefix
            for fn in os.listdir(PROTOCOL_DIR):
                if fn.startswith(p["id"] + "_"):
                    filepath = os.path.join(PROTOCOL_DIR, fn)
                    break
        if not os.path.exists(filepath):
            continue
        sections = parse_protocol(filepath)
        content_html = format_content(sections)
        page_title = sections.get("实验名称", [p["name"]])[0] if "实验名称" in sections else p["name"]
        if page_title.startswith("实验名称："):
            page_title = page_title.replace("实验名称：", "")

        page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(p['id'])} {html.escape(page_title)} - 植研小白盒</title>
<style>{CSS}</style>
</head>
<body>
<nav><div class="container">
    <a href="../index.html" class="logo">🌿 植研小白盒</a>
    <div class="nav-links">
        <a href="../index.html">首页</a>
        <a href="../index.html#protocols">Protocol库</a>
    </div>
</div></nav>

<div class="container">
    <a href="../index.html" class="back-link">← 返回Protocol库</a>
    <div class="protocol-detail">
        <h1>{html.escape(p['id'])} {html.escape(page_title)}</h1>
        <p><strong>分类：</strong>{html.escape(p['category'])} | <strong>难度：</strong>{'⭐' * p['difficulty']}</p>
        {content_html}
    </div>
</div>

<footer>
    <p>植研小白盒 v2.0 | 基于李合生《植物生理生化实验原理和技术》整理</p>
</footer>
</body>
</html>"""
        outpath = os.path.join(OUTPUT_DIR, "protocols", f"{p['id']}.html")
        with open(outpath, "w", encoding="utf-8") as f:
            f.write(page)

if __name__ == "__main__":
    print("Building static site...")
    generate_index()
    print(f"  Generated index.html")
    generate_protocol_pages()
    print(f"  Generated {len(PROTOCOLS)} protocol pages")
    print("Done!")
