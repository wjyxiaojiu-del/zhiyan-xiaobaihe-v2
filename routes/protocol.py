"""Protocol 路由 - 展示/搜索/收藏/评分"""
from flask import Blueprint, render_template, request, jsonify, session
from data.protocol_meta import PROTOCOL_META
from data.instrument_meta import INSTRUMENT_META
from services.protocol_service import parse_protocol
from services.search_service import search_protocols
from services.database import get_db
from routes.auth import login_required
from config import PROTOCOL_DIR
import os

protocol_bp = Blueprint("protocol", __name__)


@protocol_bp.route("/")
def home():
    return render_template("home.html", protocols=PROTOCOL_META)


@protocol_bp.route("/protocol/<protocol_id>")
def protocol_detail(protocol_id):
    meta = next((p for p in PROTOCOL_META if p["id"] == protocol_id), None)
    if not meta:
        return "Protocol not found", 404
    filepath = os.path.join(PROTOCOL_DIR, meta["file"])
    content = parse_protocol(filepath)
    related_instruments = [i for i in INSTRUMENT_META if protocol_id in i.get("protocols", [])]
    return render_template("protocol.html", meta=meta, content=content, instruments=related_instruments)


@protocol_bp.route("/search")
def search_page():
    return render_template("search.html")


@protocol_bp.route("/api/search", methods=["POST"])
def api_search():
    data = request.json
    query = data.get("query", "").strip()
    category = data.get("category", "")
    difficulty = data.get("difficulty", "")
    sort_by = data.get("sort", "relevance")
    keywords = query.split() if query else []
    results = search_protocols(keywords, category, difficulty, sort_by, PROTOCOL_META)
    return jsonify({"results": results})


# ========== 收藏/评分 API ==========

@protocol_bp.route("/api/favorite/<pid>", methods=["POST"])
@login_required
def toggle_favorite(pid):
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM protocol_favorites WHERE user_id=? AND protocol_id=?",
            (session["user_id"], pid)
        ).fetchone()
        if existing:
            conn.execute("DELETE FROM protocol_favorites WHERE id=?", (existing["id"],))
            return jsonify({"favorited": False})
        else:
            conn.execute(
                "INSERT INTO protocol_favorites (user_id, protocol_id) VALUES (?, ?)",
                (session["user_id"], pid)
            )
            return jsonify({"favorited": True})


@protocol_bp.route("/api/favorites")
@login_required
def get_favorites():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT protocol_id FROM protocol_favorites WHERE user_id=?",
            (session["user_id"],)
        ).fetchall()
    return jsonify([r["protocol_id"] for r in rows])


@protocol_bp.route("/api/rate/<pid>", methods=["POST"])
@login_required
def rate_protocol(pid):
    data = request.json
    rating = int(data.get("rating", 5))
    comment = data.get("comment", "")
    with get_db() as conn:
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
    return jsonify({"ok": True})


@protocol_bp.route("/api/ratings/<pid>")
def get_ratings(pid):
    with get_db() as conn:
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
    return jsonify({
        "avg": round(avg["avg_rating"], 1) if avg["avg_rating"] else 0,
        "count": avg["count"],
        "my_rating": my_rating,
        "recent": [dict(r) for r in recent]
    })


@protocol_bp.route("/api/top-protocols")
def top_protocols():
    with get_db() as conn:
        favs = conn.execute(
            "SELECT protocol_id, COUNT(*) as cnt FROM protocol_favorites GROUP BY protocol_id ORDER BY cnt DESC LIMIT 6"
        ).fetchall()
        rated = conn.execute(
            "SELECT protocol_id, AVG(rating) as avg_r, COUNT(*) as cnt FROM protocol_ratings "
            "GROUP BY protocol_id HAVING cnt>=2 ORDER BY avg_r DESC LIMIT 6"
        ).fetchall()
    return jsonify({"favorites": [dict(r) for r in favs], "rated": [dict(r) for r in rated]})
