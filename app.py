"""
植研小白盒 v2 - Flask Web应用
功能：Protocol卡片展示 + 试剂计算器 + AI问答 + 仪器可视化指南
依赖安装：pip install flask anthropic langchain langchain-community chromadb sentence-transformers
运行方法：python app.py
"""

import os
import json
import math
import re
import sqlite3
import secrets
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# ========== 路径配置 ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROTOCOL_DIR = os.path.join(BASE_DIR, "protocol_docs")
INSTRUMENT_DIR = os.path.join(BASE_DIR, "instrument_guides")
DB_DIR = os.path.join(BASE_DIR, "chroma_db")
# Vercel 只读文件系统，数据库放 /tmp
USER_DB = os.path.join("/tmp", "users.db") if os.environ.get("VERCEL") else os.path.join(BASE_DIR, "users.db")


# ========== 用户数据库 ==========
def get_user_db():
    conn = sqlite3.connect(USER_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_user_db():
    conn = get_user_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            is_premium INTEGER DEFAULT 0,
            avatar TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS user_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            data_type TEXT NOT NULL,
            data_name TEXT NOT NULL,
            data_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS protocol_favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            protocol_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, protocol_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS protocol_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            protocol_id TEXT NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, protocol_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS experiment_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            protocol_id TEXT DEFAULT '',
            content TEXT NOT NULL,
            tags TEXT DEFAULT '',
            status TEXT DEFAULT 'done',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    # 创建默认管理员
    admin = conn.execute("SELECT id FROM users WHERE username='admin'").fetchone()
    if not admin:
        conn.execute(
            "INSERT INTO users (username, email, password_hash, role, is_premium) VALUES (?, ?, ?, ?, ?)",
            ("admin", "admin@zhiyan.com", generate_password_hash("admin123"), "admin", 1)
        )
    conn.commit()
    conn.close()


try:
    init_user_db()
except Exception as e:
    print(f"[WARN] 数据库初始化失败（Vercel环境可忽略）: {e}")


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("请先登录", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        conn = get_user_db()
        user = conn.execute("SELECT role FROM users WHERE id=?", (session["user_id"],)).fetchone()
        conn.close()
        if not user or user["role"] != "admin":
            flash("需要管理员权限", "error")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated




@app.context_processor
def inject_user():
    user = None
    if "user_id" in session:
        conn = get_user_db()
        user = conn.execute("SELECT id, username, email, role, avatar FROM users WHERE id=?",
                            (session["user_id"],)).fetchone()
        conn.close()
    return dict(current_user=user)

# ========== Protocol元数据（卡片展示用） ==========
PROTOCOL_META = [
    {"id": "P001", "name": "蒽酮比色法测可溶性糖含量", "category": "植物生理", "icon": "basic", "desc": "用蒽酮试剂和糖反应生成蓝绿色物质，颜色深浅代表糖含量多少，用分光光度计测吸光度就能算出来。", "difficulty": 2, "tags": ['分光光度计', '离心机', '水浴锅'], "file": "P001_蒽酮比色法测可溶性糖.txt", "color": "#2196F3"},
    {"id": "P002", "name": "考马斯亮蓝法", "category": "植物生理", "icon": "basic", "desc": "考马斯亮蓝染料和蛋白质结合后变蓝色，蛋白越多颜色越深，测595nm吸光度就能算蛋白含量。", "difficulty": 2, "tags": ['分光光度计', '离心机', '研钵'], "file": "P002_Bradford法测可溶性蛋白.txt", "color": "#FF9800"},
    {"id": "P003", "name": "TBA法测丙二醛", "category": "植物生理", "icon": "basic", "desc": "MDA是膜脂过氧化的产物，代表植物受伤害程度。MDA和TBA反应生成红色物质，测532nm吸光度就能算出来。", "difficulty": 2, "tags": ['分光光度计', '离心机', '水浴锅'], "file": "P003_TBA法测MDA含量.txt", "color": "#9C27B0"},
    {"id": "P004", "name": "过氧化物酶", "category": "植物生理", "icon": "basic", "desc": "POD能催化愈创木酚和H₂O₂反应生成茶褐色产物，470nm测颜色变化速率就能算出POD活性。", "difficulty": 2, "tags": ['分光光度计', '离心机', '研钵'], "file": "P004_POD活性测定.txt", "color": "#F44336"},
    {"id": "P005", "name": "过氧化氢酶", "category": "植物生理", "icon": "basic", "desc": "CAT能分解H₂O₂，通过测240nm处H₂O₂减少的速率就能算出CAT活性。", "difficulty": 2, "tags": ['分光光度计', '离心机', '研钵'], "file": "P005_CAT活性测定.txt", "color": "#00BCD4"},
    {"id": "P006", "name": "植物基因组DNA提取", "category": "分子生物", "icon": "basic", "desc": "用CTAB这种洗涤剂把植物细胞膜打破释放DNA，再用氯仿把蛋白和DNA分开，最后用异丙醇把DNA沉淀出来。", "difficulty": 2, "tags": ['分光光度计', '离心机', '水浴锅'], "file": "P006_植物基因组DNA提取.txt", "color": "#607D8B"},
    {"id": "P007", "name": "普通PCR反应体系与程序", "category": "分子生物", "icon": "basic", "desc": "PCR就像DNA的复印机，通过反复加热降温，把目标DNA片段从几个拷贝扩增到几百万个拷贝。", "difficulty": 2, "tags": ['离心机', '电泳槽'], "file": "P007_PCR反应体系.txt", "color": "#795548"},
    {"id": "P008", "name": "琼脂糖凝胶电泳", "category": "分子生物", "icon": "basic", "desc": "把DNA样品加到琼脂糖凝胶的小孔里，通电后DNA按大小分开，大片段跑得慢在上面，小片段跑得快在下面。", "difficulty": 3, "tags": ['电泳槽'], "file": "P008_琼脂糖凝胶电泳.txt", "color": "#E91E63"},
    {"id": "P009", "name": "总RNA提取", "category": "分子生物", "icon": "basic", "desc": "用TRIzol把细胞裂解，氯仿分层把RNA和蛋白/DNA分开，异丙醇沉淀出RNA，再用反转录酶把RNA变成cD", "difficulty": 2, "tags": ['离心机', '水浴锅', '研钵'], "file": "P009_总RNA提取与反转录.txt", "color": "#00BCD4"},
    {"id": "P010", "name": "液氮研磨与试剂母液配制", "category": "基础操作", "icon": "basic", "desc": "液氮研磨就是把植物组织冻到-196°C变脆，然后用研钵捣碎；母液就是高浓度的试剂原液，用的时候稀释就行。", "difficulty": 2, "tags": ['离心机', '研钵'], "file": "P010_液氮研磨与母液配制.txt", "color": "#FFC107"},
    {"id": "P011", "name": "过氧化物酶(POD)活性测定 - 愈创木酚法", "category": "植物生理", "icon": "basic", "desc": "POD催化H2O2把愈创木酚氧化成茶褐色，470nm测颜色变化速率就能算POD活性。", "difficulty": 2, "tags": ['分光光度计', '离心机', '水浴锅'], "file": "P011_过氧化物酶活性测定_李合生法.txt", "color": "#2196F3"},
    {"id": "P012", "name": "过氧化氢酶(CAT)活性测定 - 高锰酸钾滴定法", "category": "植物生理", "icon": "basic", "desc": "CAT分解H2O2，用高锰酸钾滴定剩余的H2O2，就能算出CAT分解了多少H2O2。", "difficulty": 2, "tags": ['离心机', '水浴锅', '研钵'], "file": "P012_过氧化氢酶活性测定_滴定法.txt", "color": "#FF9800"},
    {"id": "P013", "name": "丙二醛(MDA)含量测定 - TBA法", "category": "植物生理", "icon": "basic", "desc": "MDA是膜脂过氧化的产物，和TBA反应生成红色物质，测532nm算含量。", "difficulty": 2, "tags": ['分光光度计', '离心机', '水浴锅'], "file": "P013_丙二醛含量测定_李合生法.txt", "color": "#9C27B0"},
    {"id": "P014", "name": "可溶性糖含量测定 - 蒽酮比色法", "category": "植物生理", "icon": "basic", "desc": "糖在浓硫酸作用下脱水生成糠醛，和蒽酮反应生成蓝绿色，630nm测吸光度算糖含量。", "difficulty": 2, "tags": ['分光光度计', '水浴锅'], "file": "P014_可溶性糖含量测定_蒽酮法_李合生.txt", "color": "#F44336"},
    {"id": "P015", "name": "叶绿素含量测定 - 分光光度法", "category": "植物生理", "icon": "basic", "desc": "用乙醇提取叶绿素，测665nm和649nm吸光度，用公式算叶绿素a、b和类胡萝卜素含量。", "difficulty": 2, "tags": ['分光光度计', '研钵'], "file": "P015_叶绿素含量测定_分光光度法.txt", "color": "#00BCD4"},
    {"id": "P016", "name": "可溶性蛋白质含量测定 - 考马斯亮蓝G-250法", "category": "植物生理", "icon": "basic", "desc": "考马斯亮蓝和蛋白质结合变蓝，595nm测吸光度就能算蛋白质含量。", "difficulty": 2, "tags": ['分光光度计', '离心机', '研钵'], "file": "P016_可溶性蛋白质含量测定_考马斯亮蓝法.txt", "color": "#795548"},
    {"id": "P017", "name": "呼吸速率测定 - 小篮子法/广口瓶法", "category": "植物生理", "icon": "basic", "desc": "植物释放的CO2被Ba(OH)2吸收，用草酸滴定剩余碱液，算出CO2释放量就是呼吸速率。", "difficulty": 2, "tags": ['滴定管'], "file": "P017_呼吸速率测定_小篮子法.txt", "color": "#607D8B"},
    {"id": "P018", "name": "植物组织DNA提取与测定 - 盐溶法", "category": "分子生物", "icon": "basic", "desc": "用SDS裂解细胞释放DNA，氯仿-异戊醇去蛋白，乙醇沉淀DNA，二苯胺法测含量。", "difficulty": 2, "tags": ['分光光度计', '离心机', '水浴锅'], "file": "P018_DNA提取与测定_盐溶法.txt", "color": "#607D8B"},
    {"id": "P019", "name": "植物组织中自由水和束缚水含量的测定", "category": "植物生理", "icon": "basic", "desc": "自由水未被细胞原生质胶体颗粒吸附而可以自由移动、蒸发和结冰，也 可 以作为溶剂", "difficulty": 1, "tags": ['基础器材'], "file": "P019_自由水和束缚水含量测定.txt", "color": "#FFC107"},
    {"id": "P020", "name": "植物组织水势的测定", "category": "植物生理", "icon": "basic", "desc": "植物组织水势测定", "difficulty": 1, "tags": ['基础器材'], "file": "P020_植物组织水势测定.txt", "color": "#4CAF50"},
    {"id": "P021", "name": "植物细胞渗透势的测定(质壁分离法)", "category": "植物生理", "icon": "basic", "desc": "渗透势测定_质壁分离法", "difficulty": 1, "tags": ['基础器材'], "file": "P021_渗透势测定_质壁分离法.txt", "color": "#2196F3"},
    {"id": "P022", "name": "钾离子对气孔开度的影响", "category": "植物生理", "icon": "basic", "desc": "钾离子对气孔开度的影响", "difficulty": 1, "tags": ['基础器材'], "file": "P022_钾离子对气孔开度的影响.txt", "color": "#FF9800"},
    {"id": "P023", "name": "植物伤流液中糖和氨基酸的鉴定", "category": "植物生理", "icon": "basic", "desc": "用蒽酮试剂处理可以鉴定伤流液中糖的存在，并可测定其含量", "difficulty": 1, "tags": ['分光光度计', '水浴锅'], "file": "P023_伤流液中糖和氨基酸鉴定.txt", "color": "#9C27B0"},
    {"id": "P024", "name": "植物根系活力的测定(TTC法)", "category": "植物生理", "icon": "basic", "desc": "根系活力测定_TTC法", "difficulty": 2, "tags": ['分光光度计', '研钵'], "file": "P024_根系活力测定_TTC法.txt", "color": "#F44336"},
    {"id": "P025", "name": "植物组织中金属元素的测定(原子吸收分光光度法)", "category": "植物生理", "icon": "basic", "desc": "金属元素测定_原子吸收法", "difficulty": 3, "tags": ['分光光度计'], "file": "P025_金属元素测定_原子吸收法.txt", "color": "#00BCD4"},
    {"id": "P026", "name": "植物体内硝态氮含量的测定", "category": "植物生理", "icon": "basic", "desc": "硝态氮含量测定", "difficulty": 2, "tags": ['分光光度计', '水浴锅'], "file": "P026_硝态氮含量测定.txt", "color": "#795548"},
    {"id": "P027", "name": "植物体内硝酸还原酶活力的测定", "category": "植物生理", "icon": "basic", "desc": "硝酸还原酶活力测定", "difficulty": 2, "tags": ['分光光度计'], "file": "P027_硝酸还原酶活力测定.txt", "color": "#607D8B"},
    {"id": "P028", "name": "用真空渗入法测定环境因子", "category": "植物生理", "icon": "basic", "desc": "真空渗人法可使叶肉细胞间隙充满水分而下沉", "difficulty": 1, "tags": ['水浴锅'], "file": "P028_真空渗入法测定环境因子.txt", "color": "#E91E63"},
    {"id": "P029", "name": "叶绿体色素提取、分离和理化性质", "category": "植物生理", "icon": "basic", "desc": "叶绿体色素提取分离和理化性质", "difficulty": 1, "tags": ['水浴锅'], "file": "P029_叶绿体色素提取分离和理化性质.txt", "color": "#FFC107"},
    {"id": "P030", "name": "希尔反应的观察", "category": "植物生理", "icon": "basic", "desc": "希尔反应的观察", "difficulty": 1, "tags": ['研钵'], "file": "P030_希尔反应的观察.txt", "color": "#4CAF50"},
    {"id": "P031", "name": "RuBP羧化酶(RuBPCO)活性测定", "category": "植物生理", "icon": "basic", "desc": "RuBP羧化酶活性测定", "difficulty": 2, "tags": ['离心机', '水浴锅'], "file": "P031_RuBP羧化酶活性测定.txt", "color": "#2196F3"},
    {"id": "P032", "name": "乙醇酸氧化酶活性测定", "category": "植物生理", "icon": "basic", "desc": "乙醇酸氧化酶活性测定", "difficulty": 2, "tags": ['分光光度计', '离心机'], "file": "P032_乙醇酸氧化酶活性测定.txt", "color": "#FF9800"},
    {"id": "P033", "name": "红外CO₂分析仪测定光合与呼吸速率", "category": "植物生理", "icon": "basic", "desc": "红外CO2分析仪测光合呼吸速率", "difficulty": 3, "tags": ['基础器材'], "file": "P033_红外CO2分析仪测光合呼吸速率.txt", "color": "#9C27B0"},
    {"id": "P034", "name": "氧电极法测定光合与呼吸速率", "category": "植物生理", "icon": "basic", "desc": "氧电极法测光合呼吸速率", "difficulty": 3, "tags": ['水浴锅'], "file": "P034_氧电极法测光合呼吸速率.txt", "color": "#F44336"},
    {"id": "P035", "name": "叶绿体光诱导荧光强度的测定", "category": "植物生理", "icon": "basic", "desc": "叶绿体光诱导荧光测定", "difficulty": 2, "tags": ['分光光度计', '离心机'], "file": "P035_叶绿体光诱导荧光测定.txt", "color": "#00BCD4"},
    {"id": "P036", "name": "叶绿体甘油醛-3-磷酸脱氢酶活性测定", "category": "植物生理", "icon": "basic", "desc": "甘油醛_3_磷酸脱氢酶活性测定", "difficulty": 2, "tags": ['分光光度计', '离心机', '水浴锅'], "file": "P036_甘油醛_3_磷酸脱氢酶活性测定.txt", "color": "#795548"},
    {"id": "P037", "name": "微量定容测压法测定种子的呼吸速率", "category": "植物生理", "icon": "basic", "desc": "微量定容测压法测呼吸速率", "difficulty": 2, "tags": ['基础器材'], "file": "P037_微量定容测压法测呼吸速率.txt", "color": "#607D8B"},
    {"id": "P038", "name": "NBT法测定SOD活力", "category": "植物生理", "icon": "basic", "desc": "本实验依据超氧物歧化酶抑制氮蓝四唑( NBT) 在光下的还原作用来确定酶 活性大小", "difficulty": 2, "tags": ['分光光度计', '离心机', '研钵'], "file": "P038_氮蓝四唑NBT法测定SOD活力.txt", "color": "#E91E63"},
    {"id": "P039", "name": "淀粉酶活性的测定", "category": "植物生理", "icon": "basic", "desc": "β- 淀粉酶每次从淀粉的非还原端切下 一 分子麦芽  糖，又被称为糖化酶", "difficulty": 2, "tags": ['分光光度计', '离心机', '水浴锅'], "file": "P039_淀粉酶活性的测定.txt", "color": "#FFC107"},
    {"id": "P040", "name": "脲酶活性的测定", "category": "植物生理", "icon": "basic", "desc": "脲酶活性的测定", "difficulty": 2, "tags": ['分光光度计', '水浴锅'], "file": "P040_脲酶K.txt", "color": "#4CAF50"},
    {"id": "P041", "name": "POD同工酶凝胶圆盘电泳", "category": "分子生物", "icon": "basic", "desc": "POD同工酶凝胶圆盘电泳", "difficulty": 3, "tags": ['离心机', '电泳槽'], "file": "P041_植物过氧化物酶同工酶的测定_凝胶圆盘电泳.txt", "color": "#00BCD4"},
    {"id": "P042", "name": "SDS-PAGE测定蛋白质分子量", "category": "分子生物", "icon": "basic", "desc": "8蛋白质相对分子质量的测定(SDS-聚丙烯酰胺凝胶电泳法)", "difficulty": 3, "tags": ['电泳槽'], "file": "P042_蛋白质相对分子质量的测定_SDS_聚丙烯酰胺凝胶电泳法.txt", "color": "#607D8B"},
    {"id": "P043", "name": "凯氏定氮法测总氮和蛋白氮", "category": "植物生理", "icon": "basic", "desc": "凯氏定氮法测总氮和蛋白氮", "difficulty": 2, "tags": ['滴定管'], "file": "P043_植物组织中总氮_蛋白氮含量的测定_微量凯氏法.txt", "color": "#9C27B0"},
    {"id": "P044", "name": "茚三酮法测游离氨基酸总量", "category": "植物生理", "icon": "basic", "desc": "氨基酸与茚三酮共热时，能定量地生成二酮茚胺", "difficulty": 2, "tags": ['分光光度计', '水浴锅', '研钵'], "file": "P044_植物组织中游离氨基酸总量的测定_茚三酮显色法.txt", "color": "#F44336"},
    {"id": "P045", "name": "谷物淀粉含量的测定(旋光法)", "category": "植物生理", "icon": "basic", "desc": "谷物淀粉含量的测定(旋光法)", "difficulty": 2, "tags": ['离心机', '水浴锅'], "file": "P045_谷物淀粉含量的测定_旋光法.txt", "color": "#00BCD4"},
    {"id": "P046", "name": "植物种子生命力的快速测定", "category": "植物生理", "icon": "basic", "desc": "这些种子在衰老死亡时，内含 荧光物质虽然没有改变，但由于生命力衰退或已经死亡的细胞原生质之透性增 加，当浸泡种", "difficulty": 1, "tags": ['基础器材'], "file": "P046_植物种子生命力的快速测定.txt", "color": "#795548"},
    {"id": "P047", "name": "植物组织中纤维素含量的测定", "category": "植物生理", "icon": "basic", "desc": "植物组织中纤维素含量的测定", "difficulty": 2, "tags": ['分光光度计', '水浴锅'], "file": "P047_植物组织中纤维素含量的测定.txt", "color": "#607D8B"},
    {"id": "P048", "name": "苯丙氨酸解氨酶(PAL)活性测定", "category": "植物生理", "icon": "basic", "desc": "苯丙氨酸解氨酶(PAL)活性测定", "difficulty": 2, "tags": ['分光光度计', '离心机', '水浴锅'], "file": "P048_苯丙氨酸解氨酶PALase活性的测定.txt", "color": "#E91E63"},
    {"id": "P049", "name": "DNA琼脂糖凝胶电泳", "category": "分子生物", "icon": "basic", "desc": "DNA琼脂糖凝胶电泳", "difficulty": 3, "tags": ['分光光度计', '电泳槽'], "file": "P049_DNA的琼脂糖凝胶电泳.txt", "color": "#00BCD4"},
    {"id": "P050", "name": "RNA的聚丙烯酰胺凝胶电泳", "category": "分子生物", "icon": "basic", "desc": "聚丙烯酰胺凝胶电泳是以聚丙烯酰胺凝胶为载体进行电泳的方法(详见实 验28)", "difficulty": 3, "tags": ['电泳槽'], "file": "P050_RNA的聚丙烯酰胺凝胶电泳.txt", "color": "#607D8B"},
    {"id": "P051", "name": "植物组织ATP酶活性的测定", "category": "植物生理", "icon": "basic", "desc": "它存在于生物细 胞的多个部位，比如细胞质膜上、叶绿体类囊体膜上，对整个生命的维持有着重 要的作用", "difficulty": 3, "tags": ['分光光度计', '离心机', '水浴锅'], "file": "P051_植物组织ATP酶活性的测定.txt", "color": "#2196F3"},
    {"id": "P052", "name": "植物种子中主要不饱和脂肪酸的分离(反相纸层析法)", "category": "植物生理", "icon": "basic", "desc": "植物种子中主要不饱和脂肪酸的分离(反相纸层析法)", "difficulty": 3, "tags": ['基础器材'], "file": "P052_植物种子中主要不饱和脂肪酸的分离_反相纸层析法.txt", "color": "#FF9800"},
    {"id": "P053", "name": "种子粗脂肪含量的测定", "category": "植物生理", "icon": "basic", "desc": "脂 肪( fat) 广泛存在于油料植物种子和果实中，测定脂肪的含量，可以鉴别其 品质的优劣，也是油料作物选种和", "difficulty": 2, "tags": ['水浴锅', '研钵'], "file": "P053_种子粗脂肪含量的测定.txt", "color": "#9C27B0"},
    {"id": "P054", "name": "气相色谱法测定植物样品膜脂中脂肪酸的含量", "category": "植物生理", "icon": "basic", "desc": "高等植物中的膜脂主要是各种类脂，可以用氯仿一甲醇溶液研磨提取，在碱 性条件下水解出高级脂肪酸并制成甲酯后，即可", "difficulty": 3, "tags": ['离心机'], "file": "P054_气相色谱法测定膜脂中脂肪酸的含量.txt", "color": "#F44336"},
    {"id": "P055", "name": "气相色谱法测定乙烯含量", "category": "植物生理", "icon": "basic", "desc": "气相色谱法测定乙烯含量", "difficulty": 3, "tags": ['基础器材'], "file": "P055_气相色谱法测定乙烯含量.txt", "color": "#00BCD4"},
    {"id": "P056", "name": "酶联免疫吸附检测法(ELISA)测定植物激素含量", "category": "植物生理", "icon": "basic", "desc": "在 ELISA 中，抗原抗体反应的检测依靠酶标记物来实现，常用的酶有辣根过氧化物 酶和碱性磷酸酯酶", "difficulty": 3, "tags": ['分光光度计', '离心机', '研钵'], "file": "P056_酶联免疫吸附检测法ELISA测定植物激素含量.txt", "color": "#795548"},
    {"id": "P057", "name": "ABA和GA的分离与测定", "category": "植物生理", "icon": "basic", "desc": "再 对 纯 化 的ABA 和 GA 进行生物学鉴定或物理化学鉴定", "difficulty": 3, "tags": ['基础器材'], "file": "P057_植物体内脱落酸_赤霉素的分离和测定.txt", "color": "#607D8B"},
    {"id": "P058", "name": "赤霉素对α一淀粉酶的诱导形成", "category": "植物生理", "icon": "basic", "desc": "淀粉性种子在萌动过程中，胚释放出来的赤霉素能诱导糊粉层细胞中 a-    淀粉酶基 因 的 表 达，引起α- ", "difficulty": 2, "tags": ['分光光度计', '水浴锅'], "file": "P058_赤霉素对α一淀粉酶的诱导形成.txt", "color": "#E91E63"},
    {"id": "P059", "name": "植物激素对愈伤组织的形成和分化的影响", "category": "植物生理", "icon": "basic", "desc": "愈伤组织在适当培养条件下分化根和芽的现象称为再分化", "difficulty": 3, "tags": ['水浴锅'], "file": "P059_植物激素对愈伤组织的形成和分化的影响.txt", "color": "#FFC107"},
    {"id": "P060", "name": "类似生长素对种子萌发的影响", "category": "植物生理", "icon": "basic", "desc": "类似生长素对种子萌发的影响", "difficulty": 2, "tags": ['基础器材'], "file": "P060_类似生长素对种子萌发的影响.txt", "color": "#4CAF50"},
    {"id": "P061", "name": "植物春化和光周期现象的观察", "category": "植物生理", "icon": "basic", "desc": "植物春化和光周期现象的观察", "difficulty": 1, "tags": ['基础器材'], "file": "P061_植物春化和光周期现象的观察.txt", "color": "#2196F3"},
    {"id": "P062", "name": "抗坏血酸(维生素C)含量的测定", "category": "植物生理", "icon": "basic", "desc": "因此当用蓝色的碱性2,6- 二氯酚靛酚溶液滴定含有抗坏血酸的草酸溶液  时，其中的抗坏血酸可以将2,6 - 二", "difficulty": 1, "tags": ['分光光度计', '研钵', '滴定管'], "file": "P062_抗坏血酸_维生素C_含量的测定.txt", "color": "#FF9800"},
    {"id": "P063", "name": "谷类作物种子中赖氨酸含量的测定", "category": "植物生理", "icon": "basic", "desc": "谷类作物种子中赖氨酸含量的测定", "difficulty": 2, "tags": ['分光光度计', '离心机', '水浴锅'], "file": "P063_谷类作物种子中赖氨酸含量的测定.txt", "color": "#9C27B0"},
    {"id": "P064", "name": "脯氨酸含量的测定", "category": "植物生理", "icon": "basic", "desc": "脯氨酸含量的测定", "difficulty": 2, "tags": ['分光光度计', '离心机', '水浴锅'], "file": "P064_脯氨酸含量的测定.txt", "color": "#F44336"},
    {"id": "P065", "name": "电导仪法测定植物抗逆性", "category": "植物生理", "icon": "basic", "desc": "植物细胞膜对维持细胞的微环境和正常的代谢起着重要的作用", "difficulty": 2, "tags": ['水浴锅'], "file": "P065_植物抗逆性的测定_电导仪法.txt", "color": "#00BCD4"}
]

# ========== 仪器元数据 ==========
INSTRUMENT_META = [
    {
        "id": "I001", "name": "高速冷冻离心机",
        "icon": "centrifuge",
        "desc": "低温高速旋转分离液体中的固体和液体",
        "protocols": ["P002", "P003", "P004", "P005", "P006", "P011", "P012", "P013", "P016", "P018"],
        "color": "#1565C0",
        "hotspots": [
            {"name": "控制面板", "desc": "设置温度、转速、时间", "x": "30%", "y": "20%", "w": "40%", "h": "30%",
             "steps": ["按Temp设温度(一般4°C)", "按Speed设转速(看转子最大限制)", "按Time设时间", "按Start启动"],
             "tips": ["必须配平！对称管重量差<0.01g", "必须等转速归零再开盖", "超过转子最大转速会炸裂"],
             "video": {"search": "高速冷冻离心机 操作教程"}},
            {"name": "转子仓", "desc": "安装转子和样品管", "x": "10%", "y": "50%", "w": "80%", "h": "40%",
             "steps": ["检查转子安装牢固", "对称放置样品管", "用天平配平(差<0.01g)", "关盖锁紧"],
             "tips": ["不配平→剧烈震动→仪器损坏", "管不能装太满(最多2/3)", "转子有最大转速限制，看转子上的标注"],
             "video": {"search": "离心机 转子 安装 配平"}},
        ],
    },
    {
        "id": "I002", "name": "紫外分光光度计",
        "icon": "spectrophotometer",
        "desc": "测溶液吸光度，算出目标物质浓度",
        "protocols": ["P001", "P002", "P003", "P004", "P005", "P011", "P012", "P013", "P014", "P015", "P016", "P017"],
        "color": "#2E7D32",
        "hotspots": [
            {"name": "样品仓", "desc": "放入比色皿", "x": "35%", "y": "30%", "w": "30%", "h": "25%",
             "steps": ["打开样品仓盖", "放入比色皿(透光面朝光源方向)", "关盖"],
             "tips": ["比色皿透光面不能用手摸！", "用擦镜纸擦拭", "拿比色皿只捏磨砂面"],
             "video": {"search": "分光光度计 比色皿 使用方法"}},
            {"name": "操作面板", "desc": "设置波长、调零、读数", "x": "10%", "y": "10%", "w": "80%", "h": "20%",
             "steps": ["开机预热20min", "设置目标波长(如620nm)", "空白对照调零(Run/Zero)", "放入样品读数"],
             "tips": ["必须预热20min以上！", "空白对照每次换波长都要重调", "OD值超出0.1-0.8需稀释样品"],
             "video": {"search": "紫外分光光度计 操作教程"}},
        ],
    },
    {
        "id": "I003", "name": "PCR仪",
        "icon": "pcr_machine",
        "desc": "给DNA做复印机，通过温度循环扩增目标片段",
        "protocols": ["P007"],
        "color": "#00838F",
        "hotspots": [
            {"name": "热盖", "desc": "加热盖子防蒸发", "x": "20%", "y": "10%", "w": "60%", "h": "20%",
             "steps": ["确保热盖温度设为105°C", "PCR管盖要压紧"],
             "tips": ["热盖温度不够→管盖内壁冷凝→反应体积变化"],
             "video": {"search": "PCR仪 操作教程 设置程序"}},
            {"name": "样品槽", "desc": "放置PCR管", "x": "25%", "y": "40%", "w": "50%", "h": "40%",
             "steps": ["将PCR管放入孔中", "确保管底和金属孔充分接触", "空孔用空管填充"],
             "tips": ["管底有气泡→传热不均→扩增不均", "不要用半裙边板(高度不匹配)"],
             "video": {"search": "PCR仪 上机 操作步骤"}},
        ],
    },
    {
        "id": "I004", "name": "高压灭菌锅",
        "icon": "autoclave",
        "desc": "121°C高压杀灭所有微生物",
        "protocols": ["P006", "P007", "P010", "P018"],
        "color": "#D84315",
        "hotspots": [
            {"name": "锅盖", "desc": "密封加压", "x": "20%", "y": "5%", "w": "60%", "h": "25%",
             "steps": ["对角线拧紧螺丝", "检查密封圈完好"],
             "tips": ["密封圈老化→漏气→温度达不到", "螺丝没拧紧→蒸汽喷出→烫伤"],
             "video": {"search": "高压灭菌锅 操作教程 使用方法"}},
            {"name": "控制面板", "desc": "设置灭菌程序", "x": "60%", "y": "30%", "w": "30%", "h": "40%",
             "steps": ["设温度121°C", "设时间15-20min(液体30min)", "按Start"],
             "tips": ["液体不能装太满(最多2/3)", "液体灭菌完要自然降压，不能快排"],
             "video": {"search": "高压灭菌锅 灭菌程序 设置"}},
        ],
    },
    {
        "id": "I005", "name": "pH计",
        "icon": "ph_meter",
        "desc": "测溶液酸碱度",
        "protocols": ["P001", "P004", "P005", "P006", "P010", "P011", "P012", "P015"],
        "color": "#6A1B9A",
        "hotspots": [
            {"name": "电极", "desc": "pH感应探头", "x": "40%", "y": "10%", "w": "20%", "h": "60%",
             "steps": ["电极必须泡在3mol/L KCl保护液中保存", "用前用蒸馏水冲洗", "用滤纸轻轻吸干(不能擦！)"],
             "tips": ["电极干燥→读数不准且损坏电极", "不能擦电极球泡→产生静电→读数漂移"],
             "video": {"search": "pH计 电极 保存 使用"}},
            {"name": "操作面板", "desc": "校准和读数", "x": "10%", "y": "15%", "w": "30%", "h": "50%",
             "steps": ["两点校准：先pH6.86，再pH4.00(或9.18)", "校准后测样品"],
             "tips": ["每次用前必须校准！", "校准液要新鲜(3个月换一次)"],
             "video": {"search": "pH计 校准 两点校准 操作"}},
        ],
    },
    {
        "id": "I006", "name": "恒温水浴锅",
        "icon": "water_bath",
        "desc": "给反应提供恒定温度环境",
        "protocols": ["P001", "P003", "P006", "P013", "P014", "P015"],
        "color": "#0277BD",
        "hotspots": [
            {"name": "控制面板", "desc": "设置温度", "x": "10%", "y": "10%", "w": "35%", "h": "30%",
             "steps": ["设置目标温度", "等待温度稳定(约10min)", "用水银温度计校验"],
             "tips": ["面板显示温度可能不准→用水银温度计校验", "水位不能低于加热管"],
             "video": {"search": "恒温水浴锅 使用方法 操作"}},
        ],
    },
    {
        "id": "I007", "name": "凝胶成像系统",
        "icon": "gel_doc",
        "desc": "给跑完电泳的凝胶拍照，看DNA条带",
        "protocols": ["P008"],
        "color": "#37474F",
        "hotspots": [
            {"name": "紫外透射台", "desc": "放置凝胶并紫外激发", "x": "20%", "y": "30%", "w": "60%", "h": "50%",
             "steps": ["戴护目镜！", "将凝胶放在透射台上", "关上暗箱门", "打开紫外灯"],
             "tips": ["紫外灯开启时不能直视！", "凝胶放反了→条带左右颠倒", "拍照后立即关紫外灯"],
             "video": {"search": "凝胶成像系统 操作 拍照"}},
        ],
    },
    {
        "id": "I008", "name": "电泳槽",
        "icon": "electrophoresis",
        "desc": "让DNA在电场中按大小分开",
        "protocols": ["P008"],
        "color": "#4E342E",
        "hotspots": [
            {"name": "凝胶槽", "desc": "放置凝胶和缓冲液", "x": "15%", "y": "20%", "w": "70%", "h": "60%",
             "steps": ["将凝胶放入槽中(靠近黑色负极端)", "加缓冲液没过凝胶2mm", "拔梳子(垂直向上)", "接电源(红正黑负)"],
             "tips": ["正负极接反→DNA往反方向跑！", "缓冲液不够→局部干燥→条带扭曲", "拔梳子歪了→孔变形→条带歪"],
             "video": {"search": "琼脂糖凝胶电泳 操作教程"}},
        ],
    },
    {
        "id": "I009", "name": "液氮罐",
        "icon": "ln2_tank",
        "desc": "存放-196°C液氮，冻存样品",
        "protocols": ["P001", "P002", "P003", "P004", "P005", "P006", "P009", "P010", "P011", "P012", "P013", "P014", "P015", "P016", "P017", "P018"],
        "color": "#0D47A1",
        "hotspots": [
            {"name": "罐口", "desc": "取放样品", "x": "30%", "y": "5%", "w": "40%", "h": "20%",
             "steps": ["戴防冻手套+护目镜", "用长勺取放样品", "操作要快减少液氮蒸发"],
             "tips": ["裸手碰液氮→严重冻伤！", "密闭空间液氮蒸发→缺氧窒息", "液氮溅入眼睛→永久损伤"],
             "video": {"search": "液氮罐 使用 取样 操作"}},
        ],
    },
    {
        "id": "I010", "name": "电子天平",
        "icon": "balance",
        "desc": "精确称量试剂",
        "protocols": ["P001", "P002", "P010"],
        "color": "#558B2F",
        "hotspots": [
            {"name": "称量盘", "desc": "放置称量纸和试剂", "x": "25%", "y": "25%", "w": "50%", "h": "40%",
             "steps": ["水平气泡必须在中间", "放称量纸或称量瓶", "按Tare去皮", "用药匙加试剂"],
             "tips": ["气泡不在中间→称量不准→调地脚螺丝", "不能直接把试剂倒在称量盘上", "有腐蚀性试剂必须用称量瓶"],
             "video": {"search": "电子天平 使用方法 称量"}},
            {"name": "操作面板", "desc": "读数和功能键", "x": "10%", "y": "10%", "w": "30%", "h": "30%",
             "steps": ["开机预热", "按Cal校准(放标准砝码)", "按Tare去皮"],
             "tips": ["每天用前校准！", "精度0.0001g的天平要防震"],
             "video": {"search": "电子天平 校准 去皮 操作"}},
        ],
    },
]

# ========== 试剂分子量数据库 ==========
MW_DB = {
    "葡萄糖": 180.16, "蔗糖": 342.30, "Tris": 121.14, "EDTA": 372.24,
    "EDTA-2Na": 336.21, "NaCl": 58.44, "KCl": 74.55, "MgCl2": 95.21,
    "CaCl2": 110.98, "NaOH": 40.00, "KOH": 56.11, "HCl": 36.46,
    "H2SO4": 98.08, "SDS": 288.38, "DTT": 154.25, "VC(抗坏血酸)": 176.12,
    "愈创木酚": 124.14, "TBA": 144.15, "TCA": 163.39, "蒽酮": 194.23,
    "BSA": 66430, "NaH2PO4": 119.98, "Na2HPO4": 141.96, "KH2PO4": 136.09,
    "柠檬酸": 192.12, "柠檬酸钠": 258.06, "CTAB": 364.45, "甘油": 92.09,
}


# ========== Protocol文档解析 ==========
def parse_protocol(filepath):
    """解析Protocol txt文件，按section返回结构化内容"""
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    sections = {
        "meta": {}, "principle": "", "source": "", "instruments": "",
        "reagents": "", "formula": "", "steps": [], "safety": "",
        "tips": "", "data": "", "troubleshoot": "",
    }

    current_section = None
    lines = text.split("\n")
    buffer = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("Protocol编号"):
            sections["meta"]["id"] = stripped.split("：")[-1].strip() if "：" in stripped else stripped.split(":")[-1].strip()
        elif stripped.startswith("实验名称"):
            sections["meta"]["name"] = stripped.split("：")[-1].strip() if "：" in stripped else stripped.split(":")[-1].strip()
        elif stripped.startswith("一、"):
            if current_section and buffer:
                sections[current_section] = "\n".join(buffer)
            current_section = "principle"
            buffer = []
        elif stripped.startswith("二、"):
            if current_section and buffer:
                sections[current_section] = "\n".join(buffer)
            current_section = "principle_inner"
            buffer = []
        elif stripped.startswith("三、"):
            if current_section and buffer:
                sections[current_section] = "\n".join(buffer)
            current_section = "source"
            buffer = []
        elif stripped.startswith("四、"):
            if current_section and buffer:
                sections[current_section] = "\n".join(buffer)
            current_section = "instruments"
            buffer = []
        elif stripped.startswith("五、"):
            if current_section and buffer:
                sections[current_section] = "\n".join(buffer)
            current_section = "reagents"
            buffer = []
        elif stripped.startswith("六、"):
            if current_section and buffer:
                sections[current_section] = "\n".join(buffer)
            current_section = "formula"
            buffer = []
        elif stripped.startswith("七、"):
            if current_section and buffer:
                sections[current_section] = "\n".join(buffer)
            current_section = "steps"
            buffer = []
        elif stripped.startswith("八、"):
            if current_section and buffer:
                if current_section == "steps":
                    sections["steps_raw"] = "\n".join(buffer)
                else:
                    sections[current_section] = "\n".join(buffer)
            current_section = "safety"
            buffer = []
        elif stripped.startswith("九、"):
            if current_section and buffer:
                sections[current_section] = "\n".join(buffer)
            current_section = "tips"
            buffer = []
        elif stripped.startswith("十、"):
            if current_section and buffer:
                sections[current_section] = "\n".join(buffer)
            current_section = "data"
            buffer = []
        elif stripped.startswith("十一、"):
            if current_section and buffer:
                sections[current_section] = "\n".join(buffer)
            current_section = "troubleshoot"
            buffer = []
        else:
            buffer.append(line)

    if current_section and buffer:
        if current_section == "steps":
            sections["steps_raw"] = "\n".join(buffer)
        else:
            sections[current_section] = "\n".join(buffer)

    # Parse steps into structured list
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
                    if current_step["how"]:
                        current_step["how"] += " " + stripped
                    else:
                        current_step["how"] = stripped
        if current_step:
            parsed_steps.append(current_step)
        sections["steps"] = parsed_steps

    return sections


# ========== 仪器SVG图形生成 ==========
INSTRUMENT_SVG = {
    "centrifuge": """<svg viewBox="0 0 120 120"><rect x="25" y="20" width="70" height="80" rx="10" fill="#E3F2FD"/><rect x="30" y="25" width="60" height="35" rx="8" fill="#1565C0"/><circle cx="60" cy="42" r="14" fill="white" opacity="0.3"/><circle cx="60" cy="42" r="10" fill="white" opacity="0.5"/><circle cx="60" cy="42" r="4" fill="#0D47A1"/><line x1="60" y1="42" x2="50" y2="35" stroke="#0D47A1" stroke-width="2"/><line x1="60" y1="42" x2="70" y2="35" stroke="#0D47A1" stroke-width="2"/><line x1="60" y1="42" x2="60" y2="32" stroke="#0D47A1" stroke-width="2"/><rect x="35" y="70" width="50" height="20" rx="4" fill="#90CAF9"/><rect x="42" y="74" width="8" height="12" rx="2" fill="#1565C0"/><circle cx="58" cy="80" r="3" fill="#1565C0"/><circle cx="68" cy="80" r="3" fill="#1565C0"/></svg>""",
    "spectrophotometer": """<svg viewBox="0 0 120 120"><rect x="15" y="30" width="90" height="70" rx="8" fill="#E8F5E9"/><rect x="20" y="35" width="40" height="30" rx="4" fill="#2E7D32"/><rect x="25" y="40" width="30" height="20" rx="2" fill="#C8E6C9"/><rect x="70" y="38" width="30" height="24" rx="3" fill="#F5F5F5" stroke="#BDBDBD"/><text x="85" y="54" text-anchor="middle" font-size="8" fill="#333" font-weight="bold">0.452</text><rect x="55" y="70" width="15" height="25" rx="3" fill="#FFF9C4" stroke="#F9A825"/><rect x="25" y="80" width="8" height="5" rx="1" fill="#FF6F00"/><rect x="38" y="80" width="8" height="5" rx="1" fill="#FF6F00"/><rect x="51" y="80" width="8" height="5" rx="1" fill="#FF6F00"/><rect x="20" y="95" width="80" height="5" rx="2" fill="#E0E0E0"/></svg>""",
    "pcr_machine": """<svg viewBox="0 0 120 120"><rect x="20" y="25" width="80" height="70" rx="10" fill="#E0F2F1"/><rect x="25" y="30" width="70" height="20" rx="6" fill="#00838F"/><rect x="30" y="55" width="60" height="30" rx="4" fill="#B2DFDB"/><rect x="35" y="60" width="12" height="8" rx="2" fill="#00838F"/><rect x="52" y="60" width="12" height="8" rx="2" fill="#00838F"/><rect x="69" y="60" width="12" height="8" rx="2" fill="#00838F"/><rect x="35" y="72" width="12" height="8" rx="2" fill="#00838F"/><rect x="52" y="72" width="12" height="8" rx="2" fill="#00838F"/><rect x="69" y="72" width="12" height="8" rx="2" fill="#00838F"/></svg>""",
    "autoclave": """<svg viewBox="0 0 120 120"><ellipse cx="60" cy="85" rx="35" ry="15" fill="#B0BEC5"/><rect x="25" y="35" width="70" height="55" rx="8" fill="#CFD8DC"/><ellipse cx="60" cy="35" rx="35" ry="12" fill="#ECEFF1"/><circle cx="60" cy="35" r="8" fill="#FF5722" opacity="0.3"/><circle cx="60" cy="35" r="4" fill="#FF5722"/><rect x="42" y="25" width="6" height="12" rx="2" fill="#78909C"/><rect x="57" y="25" width="6" height="12" rx="2" fill="#78909C"/><rect x="72" y="25" width="6" height="12" rx="2" fill="#78909C"/><circle cx="40" cy="65" r="5" fill="#FFF" stroke="#FF5722"/><text x="40" y="68" text-anchor="middle" font-size="6" fill="#FF5722" font-weight="bold">121°</text><circle cx="80" cy="65" r="5" fill="#FFF" stroke="#4CAF50"/><text x="80" y="68" text-anchor="middle" font-size="6" fill="#4CAF50" font-weight="bold">OK</text></svg>""",
    "ph_meter": """<svg viewBox="0 0 120 120"><rect x="35" y="20" width="50" height="80" rx="8" fill="#EDE7F6"/><rect x="40" y="25" width="40" height="30" rx="4" fill="#7B1FA2"/><rect x="45" y="30" width="30" height="20" rx="2" fill="#E1BEE7"/><text x="60" y="44" text-anchor="middle" font-size="10" fill="white" font-weight="bold">7.00</text><rect x="42" y="62" width="36" height="8" rx="2" fill="#CE93D8"/><rect x="55" y="75" width="10" height="30" rx="3" fill="#9E9E9E"/><circle cx="60" cy="105" r="5" fill="#7B1FA2"/></svg>""",
    "water_bath": """<svg viewBox="0 0 120 120"><rect x="15" y="40" width="90" height="60" rx="8" fill="#E3F2FD"/><rect x="20" y="45" width="80" height="40" rx="6" fill="#BBDEFB"/><ellipse cx="60" cy="55" rx="30" ry="6" fill="#90CAF9" opacity="0.5"/><circle cx="50" cy="65" r="3" fill="#42A5F5" opacity="0.4"/><circle cx="70" cy="60" r="2" fill="#42A5F5" opacity="0.4"/><circle cx="60" cy="70" r="2.5" fill="#42A5F5" opacity="0.4"/><rect x="20" y="90" width="25" height="10" rx="3" fill="#1565C0"/><text x="32" y="98" text-anchor="middle" font-size="7" fill="white">100°C</text><rect x="55" y="90" width="45" height="10" rx="3" fill="#E0E0E0"/></svg>""",
    "gel_doc": """<svg viewBox="0 0 120 120"><rect x="20" y="25" width="80" height="70" rx="10" fill="#37474F"/><rect x="28" y="33" width="64" height="45" rx="6" fill="#263238"/><rect x="35" y="40" width="50" height="30" rx="3" fill="#1B5E20" opacity="0.8"/><rect x="42" y="45" width="3" height="20" fill="#76FF03" opacity="0.7"/><rect x="50" y="48" width="3" height="14" fill="#76FF03" opacity="0.6"/><rect x="58" y="44" width="3" height="22" fill="#76FF03" opacity="0.8"/><rect x="66" y="50" width="3" height="12" fill="#76FF03" opacity="0.5"/><rect x="74" y="46" width="3" height="18" fill="#76FF03" opacity="0.7"/><rect x="35" y="85" width="50" height="8" rx="2" fill="#546E7A"/><circle cx="42" cy="89" r="2" fill="#4CAF50"/><circle cx="52" cy="89" r="2" fill="#FF9800"/><circle cx="62" cy="89" r="2" fill="#F44336"/></svg>""",
    "electrophoresis": """<svg viewBox="0 0 120 120"><rect x="15" y="35" width="90" height="65" rx="6" fill="#EFEBE9"/><rect x="20" y="40" width="80" height="50" rx="4" fill="#D7CCC8"/><rect x="30" y="50" width="60" height="15" rx="2" fill="#FFF9C4"/><rect x="35" y="45" width="4" height="25" fill="#795548"/><rect x="75" y="45" width="4" height="25" fill="#795548"/><line x1="20" y1="48" x2="35" y2="48" stroke="#F44336" stroke-width="2"/><line x1="85" y1="48" x2="100" y2="48" stroke="#212121" stroke-width="2"/><rect x="35" y="55" width="3" height="8" fill="#212121" opacity="0.3"/><rect x="45" y="53" width="3" height="12" fill="#212121" opacity="0.5"/><rect x="55" y="56" width="3" height="6" fill="#212121" opacity="0.2"/><rect x="65" y="54" width="3" height="10" fill="#212121" opacity="0.4"/><text x="40" y="75" font-size="6" fill="#795548" font-weight="bold">+ (red)</text><text x="75" y="75" font-size="6" fill="#795548" font-weight="bold">- (black)</text></svg>""",
    "ln2_tank": """<svg viewBox="0 0 120 120"><ellipse cx="60" cy="95" rx="28" ry="10" fill="#90CAF9"/><rect x="32" y="25" width="56" height="75" rx="6" fill="#E3F2FD"/><rect x="36" y="30" width="48" height="65" rx="4" fill="#BBDEFB"/><rect x="45" y="18" width="30" height="15" rx="6" fill="#1565C0"/><rect x="55" y="15" width="10" height="8" rx="3" fill="#90CAF9"/><circle cx="50" cy="60" r="6" fill="#90CAF9" opacity="0.5"/><circle cx="65" cy="55" r="5" fill="#90CAF9" opacity="0.4"/><circle cx="58" cy="70" r="4" fill="#90CAF9" opacity="0.3"/><text x="60" y="88" text-anchor="middle" font-size="7" fill="#0D47A1" font-weight="bold">-196°C</text></svg>""",
    "balance": """<svg viewBox="0 0 120 120"><rect x="25" y="65" width="70" height="35" rx="6" fill="#E8EAF6"/><rect x="30" y="70" width="60" height="25" rx="4" fill="#C5CAE9"/><rect x="35" y="72" width="40" height="15" rx="2" fill="#FFF" stroke="#E0E0E0"/><text x="55" y="83" text-anchor="middle" font-size="9" fill="#333" font-weight="bold">0.0000</text><rect x="80" y="75" width="8" height="4" rx="1" fill="#FF6F00"/><rect x="80" y="82" width="8" height="4" rx="1" fill="#4CAF50"/><rect x="35" y="55" width="50" height="12" rx="3" fill="#F5F5F5" stroke="#BDBDBD"/><rect x="38" y="58" width="44" height="6" rx="2" fill="#FFF"/><line x1="60" y1="60" x2="60" y2="65" stroke="#9E9E9E" stroke-width="1"/></svg>""",
}

def get_instrument_svg(icon_type):
    """获取仪器SVG图形"""
    return INSTRUMENT_SVG.get(icon_type, "")


# ========== 认证路由 ==========

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conn = get_user_db()
        user = conn.execute("SELECT * FROM users WHERE username=? OR email=?",
                            (username, username)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            conn.execute("UPDATE users SET last_login=? WHERE id=?", (datetime.now(), user["id"]))
            conn.commit()
            conn.close()
            flash(f"欢迎回来，{user['username']}！", "success")
            return redirect(url_for("home"))
        conn.close()
        flash("用户名或密码错误", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if len(username) < 2:
            flash("用户名至少2个字符", "error")
        elif len(password) < 6:
            flash("密码至少6位", "error")
        elif password != confirm:
            flash("两次密码不一致", "error")
        else:
            conn = get_user_db()
            existing = conn.execute("SELECT id FROM users WHERE username=? OR email=?",
                                    (username, email)).fetchone()
            if existing:
                flash("用户名或邮箱已被注册", "error")
            else:
                conn.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (username, email, generate_password_hash(password))
                )
                conn.commit()
                conn.close()
                flash("注册成功，请登录", "success")
                return redirect(url_for("login"))
            conn.close()
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("已退出登录", "info")
    return redirect(url_for("home"))


@app.route("/profile")
@login_required
def profile():
    conn = get_user_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    history = conn.execute(
        "SELECT * FROM user_data WHERE user_id=? ORDER BY created_at DESC LIMIT 20",
        (session["user_id"],)
    ).fetchall()
    conn.close()
    return render_template("profile.html", user=user, history=history)


@app.route("/api/user/save-data", methods=["POST"])
@login_required
def save_user_data():
    data = request.json
    conn = get_user_db()
    conn.execute(
        "INSERT INTO user_data (user_id, data_type, data_name, data_json) VALUES (?, ?, ?, ?)",
        (session["user_id"], data["type"], data["name"], json.dumps(data["content"], ensure_ascii=False))
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/user/history")
@login_required
def user_history():
    conn = get_user_db()
    rows = conn.execute(
        "SELECT * FROM user_data WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
        (session["user_id"],)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/user/delete-data/<int:data_id>", methods=["POST"])
@login_required
def delete_user_data(data_id):
    conn = get_user_db()
    conn.execute("DELETE FROM user_data WHERE id=? AND user_id=?", (data_id, session["user_id"]))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


# ========== Protocol收藏/评分API ==========

@app.route("/api/favorite/<pid>", methods=["POST"])
@login_required
def toggle_favorite(pid):
    conn = get_user_db()
    existing = conn.execute(
        "SELECT id FROM protocol_favorites WHERE user_id=? AND protocol_id=?",
        (session["user_id"], pid)
    ).fetchone()
    if existing:
        conn.execute("DELETE FROM protocol_favorites WHERE id=?", (existing["id"],))
        conn.commit()
        conn.close()
        return jsonify({"favorited": False})
    else:
        conn.execute(
            "INSERT INTO protocol_favorites (user_id, protocol_id) VALUES (?, ?)",
            (session["user_id"], pid)
        )
        conn.commit()
        conn.close()
        return jsonify({"favorited": True})


@app.route("/api/favorites")
@login_required
def get_favorites():
    conn = get_user_db()
    rows = conn.execute(
        "SELECT protocol_id FROM protocol_favorites WHERE user_id=?",
        (session["user_id"],)
    ).fetchall()
    conn.close()
    return jsonify([r["protocol_id"] for r in rows])


@app.route("/api/rate/<pid>", methods=["POST"])
@login_required
def rate_protocol(pid):
    data = request.json
    rating = int(data.get("rating", 5))
    comment = data.get("comment", "")
    conn = get_user_db()
    existing = conn.execute(
        "SELECT id FROM protocol_ratings WHERE user_id=? AND protocol_id=?",
        (session["user_id"], pid)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE protocol_ratings SET rating=?, comment=? WHERE id=?",
            (rating, comment, existing["id"])
        )
    else:
        conn.execute(
            "INSERT INTO protocol_ratings (user_id, protocol_id, rating, comment) VALUES (?, ?, ?, ?)",
            (session["user_id"], pid, rating, comment)
        )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/ratings/<pid>")
def get_ratings(pid):
    conn = get_user_db()
    avg = conn.execute(
        "SELECT AVG(rating) as avg_rating, COUNT(*) as count FROM protocol_ratings WHERE protocol_id=?",
        (pid,)
    ).fetchone()
    my_rating = None
    if "user_id" in session:
        r = conn.execute(
            "SELECT rating FROM protocol_ratings WHERE user_id=? AND protocol_id=?",
            (session["user_id"], pid)
        ).fetchone()
        if r:
            my_rating = r["rating"]
    recent = conn.execute(
        "SELECT r.rating, r.comment, r.created_at, u.username FROM protocol_ratings r "
        "JOIN users u ON r.user_id=u.id WHERE r.protocol_id=? ORDER BY r.created_at DESC LIMIT 10",
        (pid,)
    ).fetchall()
    conn.close()
    return jsonify({
        "avg": round(avg["avg_rating"], 1) if avg["avg_rating"] else 0,
        "count": avg["count"],
        "my_rating": my_rating,
        "recent": [dict(r) for r in recent]
    })


@app.route("/api/top-protocols")
def top_protocols():
    conn = get_user_db()
    favs = conn.execute(
        "SELECT protocol_id, COUNT(*) as cnt FROM protocol_favorites GROUP BY protocol_id ORDER BY cnt DESC LIMIT 6"
    ).fetchall()
    rated = conn.execute(
        "SELECT protocol_id, AVG(rating) as avg_r, COUNT(*) as cnt FROM protocol_ratings "
        "GROUP BY protocol_id HAVING cnt>=2 ORDER BY avg_r DESC LIMIT 6"
    ).fetchall()
    conn.close()
    return jsonify({"favorites": [dict(r) for r in favs], "rated": [dict(r) for r in rated]})


# ========== 实验日志API ==========

@app.route("/journal")
@login_required
def journal_page():
    return render_template("journal.html")


@app.route("/api/journal", methods=["GET"])
@login_required
def get_journal():
    conn = get_user_db()
    logs = conn.execute(
        "SELECT * FROM experiment_logs WHERE user_id=? ORDER BY created_at DESC LIMIT 100",
        (session["user_id"],)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in logs])


@app.route("/api/journal", methods=["POST"])
@login_required
def add_journal():
    data = request.json
    conn = get_user_db()
    conn.execute(
        "INSERT INTO experiment_logs (user_id, title, protocol_id, content, tags, status) VALUES (?, ?, ?, ?, ?, ?)",
        (session["user_id"], data["title"], data.get("protocol_id", ""),
         data["content"], data.get("tags", ""), data.get("status", "done"))
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/journal/<int:lid>", methods=["DELETE"])
@login_required
def delete_journal(lid):
    conn = get_user_db()
    conn.execute("DELETE FROM experiment_logs WHERE id=? AND user_id=?", (lid, session["user_id"]))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/pricing")
def pricing():
    return render_template("pricing.html")


# ========== 管理后台 ==========

@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = get_user_db()
    users = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    total_users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    total_data = conn.execute("SELECT COUNT(*) as c FROM user_data").fetchone()["c"]
    conn.close()
    return render_template("admin.html", users=users, total_users=total_users, total_data=total_data)


@app.route("/admin/api/delete-user/<int:uid>", methods=["POST"])
@admin_required
def delete_user(uid):
    if uid == session.get("user_id"):
        return jsonify({"error": "不能删除自己"}), 400
    conn = get_user_db()
    conn.execute("DELETE FROM user_data WHERE user_id=?", (uid,))
    conn.execute("DELETE FROM users WHERE id=?", (uid,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/admin/api/reset-password/<int:uid>", methods=["POST"])
@admin_required
def reset_password(uid):
    new_pw = secrets.token_hex(6)
    conn = get_user_db()
    conn.execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(new_pw), uid))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "new_password": new_pw})


# ========== 路由 ==========

@app.route("/")
def home():
    """首页 - Protocol卡片网格 + 功能入口"""
    return render_template("home.html", protocols=PROTOCOL_META)


@app.route("/protocol/<protocol_id>")
def protocol_detail(protocol_id):
    """Protocol详情页 - 分tab展示"""
    meta = next((p for p in PROTOCOL_META if p["id"] == protocol_id), None)
    if not meta:
        return "Protocol not found", 404

    filepath = os.path.join(PROTOCOL_DIR, meta["file"])
    content = parse_protocol(filepath)

    # 获取关联仪器
    related_instruments = [i for i in INSTRUMENT_META if protocol_id in i.get("protocols", [])]

    return render_template("protocol.html", meta=meta, content=content,
                           instruments=related_instruments)


@app.route("/calculator")
def calculator():
    """试剂计算器页面"""
    return render_template("calculator.html", mw_db=MW_DB)


@app.route("/data")
def data_processing():
    """数据处理中心页面"""
    return render_template("data.html")


@app.route("/api/calculate", methods=["POST"])
def api_calculate():
    """计算器API"""
    data = request.json
    calc_type = data.get("type")

    if calc_type == "molarity_to_mass":
        mw = float(data["mw"])
        molarity = float(data["molarity"])
        volume = float(data["volume"])
        mass_g = molarity * mw * (volume / 1000)
        return jsonify({
            "mass_g": round(mass_g, 4),
            "mass_mg": round(mass_g * 1000, 2),
            "volume": volume,
        })

    elif calc_type == "mass_to_molarity":
        mw = float(data["mw"])
        mass = float(data["mass"])
        volume = float(data["volume"])
        molarity = mass / (mw * volume / 1000)
        return jsonify({
            "molarity_mol": round(molarity, 6),
            "molarity_mmol": round(molarity * 1000, 4),
            "mass_conc": round(mass * 1000 / volume, 4),
        })

    elif calc_type == "dilution":
        stock = float(data["stock"])
        target = float(data["target"])
        volume = float(data["volume"])
        if stock < target:
            return jsonify({"error": "母液浓度必须大于目标浓度"})
        vol_stock = (target * volume) / stock
        vol_solvent = volume - vol_stock
        return jsonify({
            "vol_stock_ml": round(vol_stock, 4),
            "vol_stock_ul": round(vol_stock * 1000, 2),
            "vol_solvent": round(vol_solvent, 4),
            "dilution_ratio": round(stock / target, 2),
        })

    elif calc_type == "gradient":
        start = float(data["start"])
        factor = float(data["factor"])
        steps = int(data["steps"])
        vol = float(data["vol"])
        result = []
        for i in range(steps + 1):
            conc = start / (factor ** i)
            if i == 0:
                result.append({"level": f"第{i}级(原液)", "conc": round(conc, 6), "method": f"取原液 {vol}mL"})
            else:
                vs = (conc * vol) / start
                vx = vol - vs
                result.append({
                    "level": f"第{i}级(稀释{factor**i:.0f}倍)",
                    "conc": round(conc, 6),
                    "method": f"取原液 {round(vs*1000,2)}μL + 溶剂 {round(vx,3)}mL",
                })
        return jsonify({"table": result})

    elif calc_type == "rpm_rcf":
        mode = data["mode"]
        radius = float(data["radius"])
        if mode == "rpm_to_rcf":
            rpm = float(data["value"])
            rcf = 1.118e-5 * radius * rpm ** 2
            return jsonify({"result": round(rcf, 2), "unit": "×g"})
        else:
            rcf = float(data["value"])
            rpm = math.sqrt(rcf / (1.118e-5 * radius))
            return jsonify({"result": round(rpm, 0), "unit": "rpm"})

    elif calc_type == "reconstitution":
        mass_mg = float(data["mass"])
        conc_mg_ml = float(data["conc"])
        mw = float(data["mw"]) if data.get("mw") else 0
        volume_ml = mass_mg / conc_mg_ml if conc_mg_ml != 0 else 0
        result = {
            "volume_ml": round(volume_ml, 4),
            "volume_ul": round(volume_ml * 1000, 2),
        }
        if mw > 0:
            molarity = (mass_mg / (mw * 1000)) / (volume_ml / 1000) if volume_ml > 0 else 0
            result["molarity_mmol"] = round(molarity * 1000, 4)
        return jsonify(result)

    elif calc_type == "specific_activity":
        ed50 = float(data["ed50"])
        mw = float(data.get("mw", 0))
        if ed50 <= 0:
            return jsonify({"error": "ED50必须大于0"})
        sa = 1e6 / ed50
        result = {
            "sa_unit_mg": round(sa, 4),
        }
        if mw > 0:
            sa_mol = 1e6 / (ed50 * mw)
            result["sa_nmol_mg"] = round(sa_mol, 4)
        return jsonify(result)

    return jsonify({"error": "未知计算类型"})


@app.route("/instruments")
def instruments():
    """仪器指南列表页"""
    return render_template("instruments.html", instruments=INSTRUMENT_META, svg=get_instrument_svg)


@app.route("/instrument/<instrument_id>")
def instrument_detail(instrument_id):
    """仪器详情页 - 热区交互"""
    inst = next((i for i in INSTRUMENT_META if i["id"] == instrument_id), None)
    if not inst:
        return "Instrument not found", 404

    related_protocols = [p for p in PROTOCOL_META if p["id"] in inst.get("protocols", [])]
    svg_html = get_instrument_svg(inst.get("icon", ""))
    return render_template("instrument.html", inst=inst, protocols=related_protocols, svg=svg_html)


@app.route("/ai")
def ai_chat():
    """AI问答助手页面"""
    return render_template("ai.html")


def search_protocols_for_context(query, k=3):
    """基于关键词搜索Protocol，返回相关内容作为上下文"""
    keywords = query.lower().split()
    scores = []
    for meta in PROTOCOL_META:
        filepath = os.path.join(PROTOCOL_DIR, meta["file"])
        if not os.path.exists(filepath):
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        score = 0
        name_lower = meta["name"].lower()
        content_lower = content.lower()
        for kw in keywords:
            if kw in name_lower:
                score += 10
            if kw in content_lower:
                score += content_lower.count(kw)
        if score > 0:
            scores.append((score, meta, content))
    scores.sort(key=lambda x: x[0], reverse=True)
    results = []
    for _, meta, content in scores[:k]:
        results.append(f"【{meta['id']} {meta['name']}】\n{content[:2000]}")
    return "\n\n---\n\n".join(results)


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """AI问答API - 基于本地Protocol知识库"""
    data = request.json
    user_msg = data.get("message", "")
    history = data.get("history", [])

    if not user_msg:
        return jsonify({"error": "请输入问题"})

    # 检索相关Protocol
    context = ""
    try:
        context = search_protocols_for_context(user_msg, k=3)
    except:
        pass

    answer = generate_local_answer(query=user_msg, context=context)
    return jsonify({"response": answer})


def generate_local_answer(query, context):
    """基于本地Protocol知识库的回答"""
    query_lower = query.lower()

    # 计算类问题
    if any(kw in query_lower for kw in ["算", "称", "配", "浓度", "稀释", "摩尔", "质量", "体积"]):
        answer = "### 🧪 试剂计算\n\n"
        answer += "请使用 **试剂计算器** 页面，支持以下功能：\n\n"
        answer += "| 计算类型 | 说明 |\n|---------|------|\n"
        answer += "| **稀释计算** | C₁V₁ = C₂V₂，支持mM/μM/mg/mL等单位 |\n"
        answer += "| **摩尔浓度** | 输入浓度+体积，自动算需称多少克 |\n"
        answer += "| **复溶计算** | 输入质量和目标浓度，算加多少溶剂 |\n"
        answer += "| **比活力计算** | 输入ED₅₀值，算Specific Activity |\n"
        answer += "| **单位换算** | 浓度、体积、rpm↔rcf互算 |\n\n"
        answer += "👉 [点击打开试剂计算器](/calculator)\n\n"
        if context:
            answer += "**相关Protocol配方参考：**\n\n"
            for line in context.split("\n")[:15]:
                if line.strip():
                    answer += f"> {line.strip()}\n"
        return answer

    # 失败排查
    if any(kw in query_lower for kw in ["失败", "没有", "不出", "不对", "偏低", "偏高", "怎么办", "异常", "问题"]):
        answer = "### 🔬 实验失败排查\n\n"
        answer += "实验失败很常见！帮你定位问题，请告诉我：\n\n"
        answer += "1. **你做的什么实验？**\n2. **具体现象是什么？**\n3. **操作细节？**\n\n"
        answer += "| 现象 | 可能原因 | 解决方案 |\n|------|---------|---------|\n"
        answer += "| 标准曲线R²<0.99 | 标准液配制不准 | 重新配制，每个点做3个重复 |\n"
        answer += "| OD值>0.8 | 样品浓度太高 | 稀释样品后重测 |\n"
        answer += "| 没有显色 | 试剂失效/温度不够 | 检查试剂有效期，确保沸水浴 |\n"
        answer += "| DNA条带模糊 | 降解/量太少 | 全程低温，增加样品量 |\n"
        answer += "| RNA降解 | RNase污染 | 全程RNase-free操作 |\n\n"
        if context:
            answer += "**相关Protocol避坑提示：**\n\n"
            for line in context.split("\n")[:15]:
                if line.strip() and ("做错" in line or "避坑" in line or "注意" in line or "不要" in line):
                    answer += f"> {line.strip()}\n"
        answer += "\n💡 也可以在 [Protocol库](/) 中查看对应实验的「避坑指南」Tab。"
        return answer

    # 有Protocol上下文时，给出结构化回答
    if context:
        answer = "### 📋 找到相关Protocol\n\n"

        # 解析protocol内容，提取关键信息
        lines = context.split("\n")
        current_section = ""
        sections = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("一、") or line.startswith("二、") or line.startswith("三、") or \
               line.startswith("四、") or line.startswith("五、") or line.startswith("六、") or \
               line.startswith("七、") or line.startswith("八、") or line.startswith("九、") or \
               line.startswith("十、"):
                current_section = line
                sections[current_section] = []
            elif current_section and line:
                sections.setdefault(current_section, []).append(line)

        # 组织回答
        if "七、分步操作步骤" in sections or "七、分步操作" in context:
            for sec_name, sec_lines in sections.items():
                if "步骤" in sec_name or "操作" in sec_name:
                    answer += f"**{sec_name}**\n\n"
                    for l in sec_lines[:12]:
                        answer += f"- {l}\n"
                    answer += "\n"
                    break

        # 提取安全/避坑
        for sec_name, sec_lines in sections.items():
            if "安全" in sec_name or "避坑" in sec_name:
                answer += f"**{sec_name}**\n\n"
                for l in sec_lines[:8]:
                    answer += f"> {l}\n"
                answer += "\n"

        # 如果没有解析到结构化内容，给原始内容
        if answer == "### 📋 找到相关Protocol\n\n":
            for line in lines[:25]:
                if line.strip():
                    answer += f"> {line.strip()}\n"

        answer += "\n---\n\n"
        answer += "💡 在 [Protocol库](/) 中可以查看完整内容，每个步骤都有详细的操作指南。\n"
        answer += "如果你有更具体的问题，请告诉我！"
        return answer

    # 默认回答
    return """### 🌿 你好！我是植研小白盒AI助手

我可以帮你解答植物实验相关的问题：

**🧪 试剂配制**
- 帮你计算摩尔浓度、稀释倍数
- 告诉你具体称多少克、加多少溶剂

**🔬 实验操作**
- 解释实验原理
- 指导操作步骤
- 说明每步「做对了看到什么」

**❌ 失败排查**
- 分析实验失败原因
- 给出解决方案

**📊 数据处理**
- 标准曲线怎么做
- 数据怎么计算

👉 试试问我：「配100mL 0.1mol/L Tris需要称多少克？」"""

    # 默认回答
    return """### 🌿 你好！我是植研小白盒AI助手

我可以帮你解答植物实验相关的问题：

**🧪 试剂配制**
- 帮你计算摩尔浓度、稀释倍数
- 告诉你具体称多少克、加多少溶剂

**🔬 实验操作**
- 解释实验原理
- 指导操作步骤
- 说明每步「做对了看到什么」

**⚠️ 失败排查**
- 分析实验失败的可能原因
- 给出解决方案

**📊 结果分析**
- 帮你解读数据
- 判断结果是否正常

👉 直接问我问题，或者试试上方的快捷按钮！

💡 你也可以在 [Protocol库](/) 中浏览65个标准化Protocol。"""


@app.route("/search")
def search_page():
    """Protocol检索页面"""
    return render_template("search.html")


@app.route("/api/search", methods=["POST"])
def api_search():
    """Protocol检索API - 全文关键词搜索 + 分类/难度筛选"""
    data = request.json
    query = data.get("query", "").strip()
    category = data.get("category", "")
    difficulty = data.get("difficulty", "")
    sort_by = data.get("sort", "relevance")

    keywords = query.split() if query else []

    results = []
    for meta in PROTOCOL_META:
        # 分类筛选
        if category and meta["category"] != category:
            continue
        # 难度筛选
        if difficulty and str(meta["difficulty"]) != str(difficulty):
            continue

        filepath = os.path.join(PROTOCOL_DIR, meta["file"])
        if not os.path.exists(filepath):
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        score = 0
        content_lower = content.lower()
        name_lower = meta["name"].lower()
        desc_lower = meta.get("desc", "").lower()

        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in name_lower:
                score += 10
            if kw_lower in desc_lower:
                score += 5
            # 内容匹配
            count = content_lower.count(kw_lower)
            score += count

        # 如果有筛选但无关键词，也返回全部匹配项
        if not keywords and (category or difficulty):
            score = 1

        if score > 0:
            snippet = ""
            for kw in keywords:
                idx = content_lower.find(kw.lower())
                if idx >= 0:
                    start = max(0, idx - 40)
                    end = min(len(content), idx + 80)
                    snippet = content[start:end].replace("\n", " ")
                    break

            # 获取收藏数和评分
            conn = get_user_db()
            fav_cnt = conn.execute(
                "SELECT COUNT(*) as c FROM protocol_favorites WHERE protocol_id=?",
                (meta["id"],)
            ).fetchone()["c"]
            rating_row = conn.execute(
                "SELECT AVG(rating) as avg_r FROM protocol_ratings WHERE protocol_id=?",
                (meta["id"],)
            ).fetchone()
            avg_rating = round(rating_row["avg_r"], 1) if rating_row["avg_r"] else 0
            conn.close()

            results.append({
                "protocol_id": meta["id"],
                "protocol_name": meta["name"],
                "category": meta["category"],
                "difficulty": meta["difficulty"],
                "desc": meta.get("desc", ""),
                "score": score,
                "snippet": snippet,
                "favorites": fav_cnt,
                "avg_rating": avg_rating,
            })

    # 排序
    if sort_by == "favorites":
        results.sort(key=lambda x: x["favorites"], reverse=True)
    elif sort_by == "rating":
        results.sort(key=lambda x: x["avg_rating"], reverse=True)
    elif sort_by == "difficulty":
        results.sort(key=lambda x: x["difficulty"])
    else:
        results.sort(key=lambda x: x["score"], reverse=True)

    return jsonify({"results": results})


# ========== 导出功能 ==========
from docx import Document as DocxDocument
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import io
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill


@app.route("/api/export-excel", methods=["POST"])
def export_excel():
    """导出数据处理结果为Excel格式"""
    data = request.json
    sheet_name = data.get("sheetName", "数据处理结果")
    headers = data.get("headers", [])
    rows = data.get("rows", [])
    title = data.get("title", "")

    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name

    # 字体定义：中文宋体+英文Times New Roman，5号(10.5pt)
    font_header = Font(name="宋体", size=10.5, bold=True)
    font_data = Font(name="宋体", size=10.5)
    font_title = Font(name="宋体", size=14, bold=True)

    # 对齐
    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)

    # 边框
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    # 标题行
    start_row = 1
    if title:
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(len(headers), 1))
        cell = ws.cell(row=1, column=1, value=title)
        cell.font = font_title
        cell.alignment = align_center
        start_row = 2

    # 表头
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=start_row, column=col_idx, value=h)
        cell.font = font_header
        cell.alignment = align_center
        cell.border = thin_border
        cell.fill = PatternFill(start_color="D9E2C8", end_color="D9E2C8", fill_type="solid")

    # 数据行
    for row_idx, row_data in enumerate(rows, start_row + 1):
        for col_idx, val in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = font_data
            cell.alignment = align_center
            cell.border = thin_border

    # 自动列宽（根据内容计算）
    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            if cell.value:
                # 中文字符占2个宽度
                val = str(cell.value)
                length = sum(2 if ord(c) > 127 else 1 for c in val)
                max_len = max(max_len, length)
        ws.column_dimensions[col_letter].width = min(max_len + 4, 40)

    # 自动行高（根据内容自动扩展）
    for row in ws.rows:
        max_lines = 1
        for cell in row:
            if cell.value:
                val = str(cell.value)
                # 计算需要的行数（根据列宽估算）
                col_width = ws.column_dimensions[cell.column_letter].width or 10
                chars_per_line = max(col_width / 2, 5)
                lines = math.ceil(len(val) / chars_per_line) if len(val) > chars_per_line else 1
                max_lines = max(max_lines, lines)
        ws.row_dimensions[row[0].row].height = max(max_lines * 15, 20)

    # 输出
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"{sheet_name}.xlsx",
    )


@app.route("/export")
def export_page():
    return render_template("export.html", protocols=PROTOCOL_META)

@app.route("/api/export/<pid>/<fmt>")
def export_protocol(pid, fmt):
    """导出Protocol为md/docx"""
    matching = None
    for p in PROTOCOL_META:
        if p["id"] == pid:
            matching = p
            break
    if not matching:
        return jsonify({"error": "Protocol not found"}), 404

    filepath = os.path.join(PROTOCOL_DIR, matching["file"])
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if fmt == "md":
        md_content = convert_to_markdown(content, matching)
        buf = io.BytesIO()
        buf.write(md_content.encode("utf-8"))
        buf.seek(0)
        return send_file(buf, mimetype="text/markdown",
                        as_attachment=True,
                        download_name=f"{pid}_{matching['name']}.md")

    elif fmt == "docx":
        doc = create_docx(content, matching)
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        return send_file(buf,
                        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        as_attachment=True,
                        download_name=f"{pid}_{matching['name']}.docx")

    return jsonify({"error": "Unsupported format"}), 400

def set_run_font(run, size_pt=10.5, bold=False):
    """设置run字体：中文宋体，英文Times New Roman，五号=10.5pt"""
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.name = "Times New Roman"
    # 设置中文字体
    r = run._element
    rPr = r.find(qn('w:rPr'))
    if rPr is None:
        rPr = r.makeelement(qn('w:rPr'), {})
        r.insert(0, rPr)
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = rPr.makeelement(qn('w:rFonts'), {})
        rPr.insert(0, rFonts)
    rFonts.set(qn('w:eastAsia'), '宋体')

def add_paragraph(doc, text, size=10.5, bold=False, align=None, space_after=Pt(3)):
    """添加一个段落，设置中英文混排字体"""
    p = doc.add_paragraph()
    if align:
        p.alignment = align
    p.paragraph_format.space_after = space_after
    p.paragraph_format.space_before = Pt(0)
    run = p.add_run(text)
    set_run_font(run, size, bold)
    return p

def add_checkbox_line(doc, text, size=10.5):
    """添加带打勾空格的行：☐ text"""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.left_indent = Cm(0.5)
    # 空格方框 ☐
    run = p.add_run("☐ ")
    set_run_font(run, size)
    run = p.add_run(text)
    set_run_font(run, size)
    return p

def convert_to_markdown(content, meta):
    """将Protocol txt转为格式化Markdown"""
    lines = content.split("\n")
    md = []
    md.append(f"# {meta['id']} {meta['name']}\n")

    for line in lines:
        line = line.strip()
        if not line:
            md.append("")
            continue
        if re.match(r"^[一二三四五六七八九十]+[、.]", line):
            md.append(f"\n## {line}\n")
        elif re.match(r"^步骤\d+", line):
            md.append(f"\n### {line}\n")
        elif re.match(r"^\d+\.", line):
            md.append(f"- [ ] {line[2:]}")
        else:
            md.append(line)

    return "\n".join(md)

def create_docx(content, meta):
    """将Protocol txt转为Word文档 - 宋体五号/Times New Roman五号"""
    doc = DocxDocument()

    # 设置页面边距
    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    # 设置Normal样式
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(10.5)
    style.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')

    # ===== 大标题 =====
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_p.paragraph_format.space_after = Pt(6)
    run = title_p.add_run(f"{meta['id']}  {meta['name']}")
    set_run_font(run, 16, bold=True)

    # ===== 来源出处 =====
    src_p = doc.add_paragraph()
    src_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    src_p.paragraph_format.space_after = Pt(12)
    run = src_p.add_run("植研小白盒 · 标准化Protocol")
    set_run_font(run, 9)
    run.font.color.rgb = RGBColor(0x90, 0x90, 0x90)

    # ===== 解析内容 =====
    lines = content.split("\n")
    current_section = ""

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line:
            continue

        # 跳过Protocol编号和实验名称行（已在标题中）
        if line.startswith("Protocol编号") or line.startswith("实验名称"):
            continue

        # 一级标题：一、原理  二、材料  三、步骤 ...
        if re.match(r"^[一二三四五六七八九十]+[、.]", line):
            current_section = line
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(4)
            # 标题下加横线
            pPr = p._element.get_or_add_pPr()
            pBdr = pPr.makeelement(qn('w:pBdr'), {})
            bottom = pBdr.makeelement(qn('w:bottom'), {
                qn('w:val'): 'single',
                qn('w:sz'): '4',
                qn('w:space'): '1',
                qn('w:color'): '2E7D32',
            })
            pBdr.append(bottom)
            pPr.append(pBdr)
            run = p.add_run(line)
            set_run_font(run, 12, bold=True)
            run.font.color.rgb = RGBColor(0x2E, 0x7D, 0x32)
            continue

        # 步骤标题：步骤1：xxx
        if re.match(r"^步骤\d+", line):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run("🔹 " + line)
            set_run_font(run, 11, bold=True)
            continue

        # 子项：为什么/做对了/做错了 -> 带缩进
        if line.startswith("为什么：") or line.startswith("做对了：") or line.startswith("做错了："):
            add_checkbox_line(doc, line)
            continue

        # 普通列表项 1. 2. 3.
        if re.match(r"^\d+\.", line):
            add_checkbox_line(doc, line)
            continue

        # 普通正文
        add_paragraph(doc, line)

    # ===== 底部签字栏 =====
    doc.add_paragraph()  # 空行
    sign_p = doc.add_paragraph()
    sign_p.paragraph_format.space_before = Pt(20)
    run = sign_p.add_run("实验日期：____________    操作人：____________    复核人：____________")
    set_run_font(run, 10.5)

    return doc

# ========== 启动 ==========
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  植研小白盒 v2 启动中...")
    print("  访问地址: http://localhost:5000")
    print("=" * 50 + "\n")
    app.run(debug=True, port=5000)
