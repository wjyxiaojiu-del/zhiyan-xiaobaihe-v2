"""
GitHub API Push via Contents API
绕过代理 + 无需 repo scope
"""
import base64
import json
import os
import requests
import subprocess
import time

REPO = "wjyxiaojiu-del/zhiyan-xiaobaihe-v2"
BRANCH = "master"

result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
TOKEN = result.stdout.strip()

HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "X-Hub-Accept": "application/vnd.github.v3+json"
}
BASE = "https://api.github.com"

IGNORE_DIRS = {".git", "__pycache__", "chroma_db"}
IGNORE_EXTS = {".pyc", ".pyo"}
EXCLUDE_FILES = {".env", "users.db"}

root = os.path.dirname(os.path.abspath(__file__))

def should_ignore(relpath):
    parts = relpath.split("/")
    for p in parts:
        if p in IGNORE_DIRS:
            return True
    for ext in IGNORE_EXTS:
        if relpath.endswith(ext):
            return True
    if os.path.basename(relpath) in EXCLUDE_FILES:
        return True
    return False

def api_get(path):
    r = requests.get(BASE + path, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

def api_put(path, data):
    r = requests.put(BASE + path, headers=HEADERS, json=data, timeout=30)
    if r.status_code >= 400:
        print(f"  ⚠️ {r.status_code}: {r.text[:150]}")
    r.raise_for_status()
    return r.json()

# 收集文件
files = []
for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
    for filename in filenames:
        filepath = os.path.join(dirpath, filename)
        relpath = os.path.relpath(filepath, root).replace(os.sep, "/")
        if should_ignore(relpath):
            continue
        with open(filepath, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")
        files.append({"path": relpath, "content": content, "filepath": filepath})

print(f"待上传 {len(files)} 个文件...")

# 先获取当前 README SHA，避免冲突
try:
    readme = api_get(f"/repos/{REPO}/contents/README.md?ref={BRANCH}")
    readme_sha = readme["sha"]
except:
    readme_sha = None
    print("README.md 不存在，将作为新文件创建")

# 上传所有文件（Contents API 不需要 repo scope）
success = 0
errors = 0
for i, f in enumerate(files):
    try:
        # 先尝试获取现有 SHA
        existing = None
        try:
            existing = api_get(f"/repos/{REPO}/contents/{f['path']}?ref={BRANCH}")
        except:
            pass

        data = {
            "message": f"chore: upload {f['path']}",
            "content": f["content"],
            "branch": BRANCH
        }
        if existing:
            data["sha"] = existing["sha"]

        api_put(f"/repos/{REPO}/contents/{f['path']}", data)
        success += 1
        if i % 10 == 0:
            print(f"进度: {i+1}/{len(files)}")
    except Exception as e:
        errors += 1
        print(f"  ❌ {f['path']}: {e}")
        if errors > 5:
            print("错误过多，停止上传")
            break
    time.sleep(0.05)  # 避免触发 rate limit

print(f"\n✅ 完成！成功 {success}，失败 {errors}")
