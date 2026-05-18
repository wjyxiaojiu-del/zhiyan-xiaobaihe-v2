"""搜索服务 - 带缓存和批量数据库查询"""
from services.cache import search_cache
from services.protocol_service import get_protocol_content
from services.database import get_db


def search_protocols(keywords, category="", difficulty="", sort_by="relevance", protocol_meta=None):
    """搜索 Protocol，返回结果列表"""
    cache_key = f"{keywords}:{category}:{difficulty}:{sort_by}"
    cached = search_cache.get(cache_key)
    if cached is not None:
        return cached

    keywords_lower = [k.lower() for k in keywords] if keywords else []
    results = []

    for meta in protocol_meta:
        if category and meta["category"] != category:
            continue
        if difficulty and str(meta["difficulty"]) != str(difficulty):
            continue

        content = get_protocol_content(meta)
        if not content:
            continue

        score = 0
        content_lower = content.lower()
        name_lower = meta["name"].lower()
        desc_lower = meta.get("desc", "").lower()

        for kw in keywords_lower:
            if kw in name_lower:
                score += 10
            if kw in desc_lower:
                score += 5
            score += content_lower.count(kw)

        if not keywords_lower and (category or difficulty):
            score = 1

        if score > 0:
            snippet = ""
            for kw in keywords_lower:
                idx = content_lower.find(kw)
                if idx >= 0:
                    start = max(0, idx - 40)
                    end = min(len(content), idx + 80)
                    snippet = content[start:end].replace("\n", " ")
                    break

            results.append({
                "protocol_id": meta["id"],
                "protocol_name": meta["name"],
                "category": meta["category"],
                "difficulty": meta["difficulty"],
                "desc": meta.get("desc", ""),
                "score": score,
                "snippet": snippet,
            })

    # 批量查询收藏数和评分（避免 N+1）
    if results:
        pids = [r["protocol_id"] for r in results]
        fav_counts, avg_ratings = _batch_query_stats(pids)
        for r in results:
            r["favorites"] = fav_counts.get(r["protocol_id"], 0)
            r["avg_rating"] = avg_ratings.get(r["protocol_id"], 0)

    # 排序
    if sort_by == "favorites":
        results.sort(key=lambda x: x["favorites"], reverse=True)
    elif sort_by == "rating":
        results.sort(key=lambda x: x["avg_rating"], reverse=True)
    elif sort_by == "difficulty":
        results.sort(key=lambda x: x["difficulty"])
    else:
        results.sort(key=lambda x: x["score"], reverse=True)

    search_cache.set(cache_key, results)
    return results


def _batch_query_stats(protocol_ids):
    """批量查询收藏数和评分，替代 N+1 查询"""
    fav_counts = {}
    avg_ratings = {}

    if not protocol_ids:
        return fav_counts, avg_ratings

    placeholders = ",".join("?" * len(protocol_ids))

    with get_db() as conn:
        # 批量查收藏数
        rows = conn.execute(
            f"SELECT protocol_id, COUNT(*) as cnt FROM protocol_favorites "
            f"WHERE protocol_id IN ({placeholders}) GROUP BY protocol_id",
            protocol_ids
        ).fetchall()
        for r in rows:
            fav_counts[r["protocol_id"]] = r["cnt"]

        # 批量查评分
        rows = conn.execute(
            f"SELECT protocol_id, AVG(rating) as avg_r, COUNT(*) as cnt FROM protocol_ratings "
            f"WHERE protocol_id IN ({placeholders}) GROUP BY protocol_id HAVING cnt >= 1",
            protocol_ids
        ).fetchall()
        for r in rows:
            avg_ratings[r["protocol_id"]] = round(r["avg_r"], 1)

    return fav_counts, avg_ratings


def search_for_context(query, protocol_meta, k=3):
    """为 AI 问答检索相关 Protocol 内容"""
    keywords = query.lower().split()
    scores = []
    for meta in protocol_meta:
        content = get_protocol_content(meta)
        if not content:
            continue
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
