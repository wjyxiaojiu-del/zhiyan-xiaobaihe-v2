"""植研小白盒 - 配置管理"""
import os
import secrets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROTOCOL_DIR = os.path.join(BASE_DIR, "protocol_docs")
INSTRUMENT_DIR = os.path.join(BASE_DIR, "instrument_guides")

# Vercel 只读文件系统，数据库放 /tmp
USER_DB = os.path.join("/tmp", "users.db") if os.environ.get("VERCEL") else os.path.join(BASE_DIR, "users.db")

SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32))

# Claude API
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")
