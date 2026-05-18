"""认证路由 - 登录/注册/个人中心"""
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from services.database import get_db

auth_bp = Blueprint("auth", __name__)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            if request.is_json:
                return jsonify({"error": "请先登录"}), 401
            flash("请先登录", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        with get_db() as conn:
            user = conn.execute("SELECT role FROM users WHERE id=?", (session["user_id"],)).fetchone()
        if not user or user["role"] != "admin":
            flash("需要管理员权限", "error")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with get_db() as conn:
            user = conn.execute("SELECT * FROM users WHERE username=? OR email=?",
                                (username, username)).fetchone()
            if user and check_password_hash(user["password_hash"], password):
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                session["role"] = user["role"]
                conn.execute("UPDATE users SET last_login=? WHERE id=?", (datetime.now(), user["id"]))
                flash(f"欢迎回来，{user['username']}！", "success")
                return redirect(url_for("home"))
        flash("用户名或密码错误", "error")
    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
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
            with get_db() as conn:
                existing = conn.execute("SELECT id FROM users WHERE username=? OR email=?",
                                        (username, email)).fetchone()
                if existing:
                    flash("用户名或邮箱已被注册", "error")
                else:
                    conn.execute(
                        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                        (username, email, generate_password_hash(password))
                    )
                    flash("注册成功，请登录", "success")
                    return redirect(url_for("auth.login"))
    return render_template("register.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("已退出登录", "info")
    return redirect(url_for("home"))


@auth_bp.route("/profile")
@login_required
def profile():
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
        history = conn.execute(
            "SELECT * FROM user_data WHERE user_id=? ORDER BY created_at DESC LIMIT 20",
            (session["user_id"],)
        ).fetchall()
    return render_template("profile.html", user=user, history=history)


@auth_bp.route("/api/user/save-data", methods=["POST"])
@login_required
def save_user_data():
    data = request.json
    with get_db() as conn:
        conn.execute(
            "INSERT INTO user_data (user_id, data_type, data_name, data_json) VALUES (?, ?, ?, ?)",
            (session["user_id"], data["type"], data["name"],
             __import__("json").dumps(data["content"], ensure_ascii=False))
        )
    return jsonify({"ok": True})


@auth_bp.route("/api/user/history")
@login_required
def user_history():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM user_data WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
            (session["user_id"],)
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@auth_bp.route("/api/user/delete-data/<int:data_id>", methods=["POST"])
@login_required
def delete_user_data(data_id):
    with get_db() as conn:
        conn.execute("DELETE FROM user_data WHERE id=? AND user_id=?", (data_id, session["user_id"]))
    return jsonify({"ok": True})
