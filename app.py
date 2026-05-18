"""
植研小白盒 v3 - Flask Web 应用（模块化重构）
功能：Protocol 检索 + 试剂计算器 + Claude AI 问答 + 仪器可视化指南
运行：python app.py
"""
import os
from flask import Flask, session, send_from_directory
from config import SECRET_KEY, BASE_DIR
from services.database import init_db
from routes import register_blueprints


def create_app():
    app = Flask(__name__)
    app.secret_key = SECRET_KEY

    # 注册所有 Blueprint
    register_blueprints(app)

    # 上下文处理器：注入当前用户信息
    @app.context_processor
    def inject_user():
        user = None
        if "user_id" in session:
            from services.database import get_db
            with get_db() as conn:
                user = conn.execute(
                    "SELECT id, username, email, role, avatar FROM users WHERE id=?",
                    (session["user_id"],)
                ).fetchone()
        return dict(current_user=user)

    # 静态文件路由（Vercel 兼容）
    @app.route("/static/<path:filename>")
    def serve_static(filename):
        return send_from_directory(os.path.join(BASE_DIR, "static"), filename)

    # 会员页
    @app.route("/pricing")
    def pricing():
        from flask import render_template
        return render_template("pricing.html")

    # 数据处理中心
    @app.route("/data")
    def data_processing():
        from flask import render_template
        return render_template("data.html")

    # 初始化数据库
    try:
        init_db()
        _create_default_admin()
    except Exception as e:
        print(f"[WARN] 数据库初始化失败（Vercel 环境可忽略）: {e}")

    return app


def _create_default_admin():
    """创建默认管理员账户"""
    from werkzeug.security import generate_password_hash
    from services.database import get_db
    with get_db() as conn:
        admin = conn.execute("SELECT id FROM users WHERE username='admin'").fetchone()
        if not admin:
            conn.execute(
                "INSERT INTO users (username, email, password_hash, role, is_premium) VALUES (?, ?, ?, ?, ?)",
                ("admin", "admin@zhiyan.com", generate_password_hash("admin123"), "admin", 1)
            )


# Vercel 需要模块级 app 变量
app = create_app()

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  植研小白盒 v3 启动中...")
    print("  访问地址: http://localhost:5000")
    print("=" * 50 + "\n")
    app.run(debug=True, port=5000)
