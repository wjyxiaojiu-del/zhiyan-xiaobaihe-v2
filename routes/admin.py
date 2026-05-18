"""管理后台路由"""
import secrets
from flask import Blueprint, render_template, request, jsonify, session
from werkzeug.security import generate_password_hash
from services.database import get_db
from routes.auth import admin_required

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
@admin_required
def admin_dashboard():
    with get_db() as conn:
        users = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
        total_users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
        total_data = conn.execute("SELECT COUNT(*) as c FROM user_data").fetchone()["c"]
    return render_template("admin.html", users=users, total_users=total_users, total_data=total_data)


@admin_bp.route("/admin/api/delete-user/<int:uid>", methods=["POST"])
@admin_required
def delete_user(uid):
    if uid == session.get("user_id"):
        return jsonify({"error": "不能删除自己"}), 400
    with get_db() as conn:
        conn.execute("DELETE FROM user_data WHERE user_id=?", (uid,))
        conn.execute("DELETE FROM users WHERE id=?", (uid,))
    return jsonify({"ok": True})


@admin_bp.route("/admin/api/reset-password/<int:uid>", methods=["POST"])
@admin_required
def reset_password(uid):
    new_pw = secrets.token_hex(6)
    with get_db() as conn:
        conn.execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(new_pw), uid))
    return jsonify({"ok": True, "new_password": new_pw})
