"""实验日志路由"""
from flask import Blueprint, render_template, request, jsonify
from services.database import get_db
from routes.auth import login_required

journal_bp = Blueprint("journal", __name__)


@journal_bp.route("/journal")
@login_required
def journal_page():
    return render_template("journal.html")


@journal_bp.route("/api/journal", methods=["GET"])
@login_required
def get_journal():
    from flask import session
    with get_db() as conn:
        logs = conn.execute(
            "SELECT * FROM experiment_logs WHERE user_id=? ORDER BY created_at DESC LIMIT 100",
            (session["user_id"],)
        ).fetchall()
    return jsonify([dict(r) for r in logs])


@journal_bp.route("/api/journal", methods=["POST"])
@login_required
def add_journal():
    from flask import session
    data = request.json
    with get_db() as conn:
        conn.execute(
            "INSERT INTO experiment_logs (user_id, title, protocol_id, content, tags, status) VALUES (?, ?, ?, ?, ?, ?)",
            (session["user_id"], data["title"], data.get("protocol_id", ""),
             data["content"], data.get("tags", ""), data.get("status", "done"))
        )
    return jsonify({"ok": True})


@journal_bp.route("/api/journal/<int:lid>", methods=["DELETE"])
@login_required
def delete_journal(lid):
    from flask import session
    with get_db() as conn:
        conn.execute("DELETE FROM experiment_logs WHERE id=? AND user_id=?", (lid, session["user_id"]))
    return jsonify({"ok": True})
