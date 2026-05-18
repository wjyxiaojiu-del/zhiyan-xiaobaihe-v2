"""AI 问答路由"""
from flask import Blueprint, render_template, request, jsonify
from data.protocol_meta import PROTOCOL_META
from services.ai_service import generate_answer
from services.search_service import search_for_context

ai_bp = Blueprint("ai", __name__)


@ai_bp.route("/ai")
def ai_chat():
    return render_template("ai.html")


@ai_bp.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.json
    user_msg = data.get("message", "")
    history = data.get("history", [])

    if not user_msg:
        return jsonify({"error": "请输入问题"})

    # 检索相关 Protocol 作为上下文
    context = ""
    try:
        context = search_for_context(user_msg, PROTOCOL_META, k=3)
    except Exception:
        pass

    answer = generate_answer(query=user_msg, context=context, history=history)
    return jsonify({"response": answer})
