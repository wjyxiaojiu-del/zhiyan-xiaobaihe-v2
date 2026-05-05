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
from flask import Flask, render_template, request, jsonify, send_file

app = Flask(__name__)

# ========== 路径配置 ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROTOCOL_DIR = os.path.join(BASE_DIR, "protocol_docs")
INSTRUMENT_DIR = os.path.join(BASE_DIR, "instrument_guides")
DB_DIR = os.path.join(BASE_DIR, "chroma_db")

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
             "video": {"bvid": "BV1xx411c7mD", "t": 120}},
            {"name": "转子仓", "desc": "安装转子和样品管", "x": "10%", "y": "50%", "w": "80%", "h": "40%",
             "steps": ["检查转子安装牢固", "对称放置样品管", "用天平配平(差<0.01g)", "关盖锁紧"],
             "tips": ["不配平→剧烈震动→仪器损坏", "管不能装太满(最多2/3)", "转子有最大转速限制，看转子上的标注"],
             "video": {"bvid": "BV1xx411c7mD", "t": 240}},
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
             "video": {"bvid": "BV1xx411c7mD", "t": 60}},
            {"name": "操作面板", "desc": "设置波长、调零、读数", "x": "10%", "y": "10%", "w": "80%", "h": "20%",
             "steps": ["开机预热20min", "设置目标波长(如620nm)", "空白对照调零(Run/Zero)", "放入样品读数"],
             "tips": ["必须预热20min以上！", "空白对照每次换波长都要重调", "OD值超出0.1-0.8需稀释样品"],
             "video": {"bvid": "BV1xx411c7mD", "t": 90}},
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
             "video": {"bvid": "BV1xx411c7mD", "t": 180}},
            {"name": "样品槽", "desc": "放置PCR管", "x": "25%", "y": "40%", "w": "50%", "h": "40%",
             "steps": ["将PCR管放入孔中", "确保管底和金属孔充分接触", "空孔用空管填充"],
             "tips": ["管底有气泡→传热不均→扩增不均", "不要用半裙边板(高度不匹配)"],
             "video": {"bvid": "BV1xx411c7mD", "t": 200}},
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
             "video": {"bvid": "BV1xx411c7mD", "t": 30}},
            {"name": "控制面板", "desc": "设置灭菌程序", "x": "60%", "y": "30%", "w": "30%", "h": "40%",
             "steps": ["设温度121°C", "设时间15-20min(液体30min)", "按Start"],
             "tips": ["液体不能装太满(最多2/3)", "液体灭菌完要自然降压，不能快排"],
             "video": {"bvid": "BV1xx411c7mD", "t": 60}},
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
             "video": {"bvid": "BV1xx411c7mD", "t": 45}},
            {"name": "操作面板", "desc": "校准和读数", "x": "10%", "y": "15%", "w": "30%", "h": "50%",
             "steps": ["两点校准：先pH6.86，再pH4.00(或9.18)", "校准后测样品"],
             "tips": ["每次用前必须校准！", "校准液要新鲜(3个月换一次)"],
             "video": {"bvid": "BV1xx411c7mD", "t": 90}},
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
             "video": {"bvid": "BV1xx411c7mD", "t": 20}},
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
             "video": {"bvid": "BV1xx411c7mD", "t": 150}},
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
             "video": {"bvid": "BV1xx411c7mD", "t": 120}},
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
             "video": {"bvid": "BV1xx411c7mD", "t": 15}},
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
             "video": {"bvid": "BV1xx411c7mD", "t": 10}},
            {"name": "操作面板", "desc": "读数和功能键", "x": "10%", "y": "10%", "w": "30%", "h": "30%",
             "steps": ["开机预热", "按Cal校准(放标准砝码)", "按Tare去皮"],
             "tips": ["每天用前校准！", "精度0.0001g的天平要防震"],
             "video": {"bvid": "BV1xx411c7mD", "t": 25}},
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

    return jsonify({"error": "未知计算类型"})


@app.route("/instruments")
def instruments():
    """仪器指南列表页"""
    return render_template("instruments.html", instruments=INSTRUMENT_META)


@app.route("/instrument/<instrument_id>")
def instrument_detail(instrument_id):
    """仪器详情页 - 热区交互"""
    inst = next((i for i in INSTRUMENT_META if i["id"] == instrument_id), None)
    if not inst:
        return "Instrument not found", 404

    related_protocols = [p for p in PROTOCOL_META if p["id"] in inst.get("protocols", [])]
    return render_template("instrument.html", inst=inst, protocols=related_protocols)


@app.route("/ai")
def ai_chat():
    """AI问答助手页面"""
    return render_template("ai.html")


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """AI问答API"""
    data = request.json
    user_msg = data.get("message", "")
    api_key = data.get("api_key", "")

    if not api_key:
        return jsonify({"error": "请输入API Key"})

    # 检索相关Protocol
    context = ""
    try:
        if os.path.exists(DB_DIR):
            from langchain_community.vectorstores import Chroma
            from langchain_community.embeddings import HuggingFaceEmbeddings
            embeddings = HuggingFaceEmbeddings(model_name="shibing624/text2vec-base-chinese")
            db = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
            docs = db.similarity_search(user_msg, k=2)
            context = "\n\n".join([d.page_content for d in docs])
    except:
        pass

    system = """你是「植研小白盒」AI助手，专门帮助植物科学/农学方向的科研新手。
核心能力：解答植物实验问题、试剂配比计算、实验失败排查、仪器操作指导。
规则：1.术语必须加通俗解释 2.给精确数值不给模糊范围 3.危险操作先说安全提醒 4.注明来源 5.每步告诉用户做对了看到什么 6.非植物/农学问题礼貌拒绝"""

    full_prompt = user_msg
    if context:
        full_prompt = f"以下是可能相关的Protocol内容：\n\n{context}\n\n用户问题：{user_msg}"

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=system,
            messages=[{"role": "user", "content": full_prompt}],
        )
        return jsonify({"response": msg.content[0].text})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/search")
def search_page():
    """Protocol检索页面"""
    return render_template("search.html")


@app.route("/api/search", methods=["POST"])
def api_search():
    """Protocol检索API - 全文关键词搜索"""
    data = request.json
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"results": []})

    # 支持多关键词搜索（空格分隔）
    keywords = query.split()

    results = []
    for meta in PROTOCOL_META:
        filepath = os.path.join(PROTOCOL_DIR, meta["file"])
        if not os.path.exists(filepath):
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # 计算匹配分数
        score = 0
        content_lower = content.lower()
        name_lower = meta["name"].lower()
        desc_lower = meta.get("desc", "").lower()

        for kw in keywords:
            kw_lower = kw.lower()
            # 名称匹配权重最高
            if kw_lower in name_lower:
                score += 10
            # 描述匹配
            if kw_lower in desc_lower:
                score += 5
            # 内容匹配
            count = content_lower.count(kw_lower)
            score += count

        if score > 0:
            # 找到匹配的上下文片段
            snippet = ""
            for kw in keywords:
                idx = content_lower.find(kw.lower())
                if idx >= 0:
                    start = max(0, idx - 40)
                    end = min(len(content), idx + 80)
                    snippet = content[start:end].replace("\n", " ")
                    break

            results.append({
                "protocol_id": meta["id"],
                "protocol_name": meta["name"],
                "category": meta["category"],
                "desc": meta.get("desc", ""),
                "score": score,
                "snippet": snippet,
            })

    # 按分数排序，取前8个
    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:8]

    return jsonify({"results": results})


# ========== 导出功能 ==========
from docx import Document as DocxDocument
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import io

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
