"""
检索服务 — Elasticsearch 查询构造器

支持三种检索模式：
- keyword: 关键词检索（IK 分词 + 多字段加权 + 高亮）
- semantic: 语义检索（LLM query 理解 → ES DSL）
- advanced: 高级条件组合检索

ES 不可用时降级为 SQLite 简单查询。
"""

import time
from typing import Optional

from app.core.config import settings
from app.core.database import get_es, SessionLocal
from app.services.llm_client import llm_client

# ==================== 字段权重 ====================
FIELD_BOOST = {
    "title": 3.0,
    "author": 2.0,
    "file_code": 2.5,
    "subject": 2.0,
    "full_text": 1.0,
    "department": 2.0,
    "category": 0.5,
}

# ==================== 同义词映射 ====================
SYNONYM_MAP = {
    "学生": ["学籍", "在校生", "学员"],
    "毕业": ["校友", "毕业生", "结业"],
    "成绩": ["成绩单", "学业成绩", "分数"],
    "招生": ["录取", "入学", "招收"],
    "教职工": ["教工", "教师", "员工", "教员"],
    "档案": ["案卷", "卷宗", "文件"],
}

# ==================== 搜索入口 ====================

def search_keyword(
    keywords: str,
    scope_nodes: list[str] | None = None,
    level: str = "all",
    page: int = 1,
    page_size: int = 20,
    sort: str = "score",
    exact: bool = False,
    dimension: str = "all",
    user: dict | None = None,
) -> dict:
    """关键词检索"""
    t0 = time.time()

    # 扩展同义词（精确模式不扩展）
    expanded = keywords if exact else _expand_synonyms(keywords)

    es = get_es()
    if es is None:
        return _fallback_search(keywords, page, page_size, t0, sort, scope_nodes, level, user)

    query = _build_keyword_query(expanded, scope_nodes, level, exact, dimension)
    return _execute_es_search(es, query, page, page_size, t0, sort, user=user)


def search_semantic(
    query_text: str,
    scope_nodes: list[str] | None = None,
    page: int = 1,
    page_size: int = 20,
    sort: str = "score",
    user: dict | None = None,
) -> dict:
    """语义检索 — LLM 理解意图 → ES 查询"""
    t0 = time.time()

    # LLM 理解用户意图
    intent = llm_client.understand_query(query_text)

    es = get_es()
    if es is None:
        return _fallback_search(query_text, page, page_size, t0, sort, scope_nodes, user=user)

    # 用 LLM 解析出的关键词 + 实体构造 ES 查询
    keywords = " ".join(intent.get("keywords", []) or query_text.split())
    query = _build_keyword_query(keywords, scope_nodes)
    query = _add_semantic_boost(query, intent)

    return _execute_es_search(es, query, page, page_size, t0, sort, user=user)


def search_advanced(
    keywords: str | None = None,
    author: str | None = None,
    file_code: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    category: str | None = None,
    department: str | None = None,
    fonds_id: str | None = None,
    fonds_ids: list[str] | None = None,
    retention_period: str | None = None,
    open_status: str | None = None,
    level: str = "all",
    page: int = 1,
    page_size: int = 20,
    sort: str = "score",
    user: dict | None = None,
) -> dict:
    """高级条件检索"""
    t0 = time.time()

    es = get_es()
    if es is None:
        return _fallback_search(keywords or "", page, page_size, t0, sort, level=level, user=user, year_from=year_from, year_to=year_to, category=category, department=department, fonds_id=fonds_id, fonds_ids=fonds_ids, author=author, file_code=file_code, open_status=open_status, retention_period=retention_period)

    must_clauses = []
    filters = []

    # 关键词
    if keywords:
        expanded = _expand_synonyms(keywords)
        must_clauses.append({
            "multi_match": {
                "query": expanded,
                "fields": [f"{k}^{v}" for k, v in FIELD_BOOST.items()],
                "type": "best_fields",
                "operator": "and",
            }
        })

    # 如果没有关键词，match_all
    if not must_clauses:
        must_clauses.append({"match_all": {}})

    # 过滤条件
    if year_from or year_to:
        rng = {}
        if year_from: rng["gte"] = year_from
        if year_to: rng["lte"] = year_to
        filters.append({"range": {"year": rng}})
    if category:
        filters.append({"term": {"category": category}})
    if department:
        filters.append({"term": {"department": department}})
    if author:
        filters.append({"term": {"author": author}})
    if file_code:
        filters.append({"term": {"file_code": file_code}})
    if fonds_id:
        filters.append({"term": {"fonds_id": fonds_id}})
    if fonds_ids:
        filters.append({"terms": {"fonds_id": fonds_ids}})
    if retention_period:
        filters.append({"term": {"retention_period": retention_period}})
    if open_status:
        filters.append({"term": {"open_status": open_status}})

    query = {
        "bool": {
            "must": must_clauses,
            "filter": filters,
        }
    }

    return _execute_es_search(es, query, page, page_size, t0, sort, user=user)


# ==================== ES 查询构造 ====================

def _build_keyword_query(
    keywords: str,
    scope_nodes: list[str] | None = None,
    level: str = "all",
    exact: bool = False,
    dimension: str = "all",
) -> dict:
    """构造关键词 ES 查询"""
    # 按维度选择搜索字段
    dim_fields = {
        "all": [f"{k}^{v}" for k, v in FIELD_BOOST.items()],
        "title": ["title^10"],
        "archive_id": ["archive_id^10"],
        "author": ["author^10"],
        "subject": ["subject^8"],
    }
    fields = dim_fields.get(dimension, dim_fields["all"])

    match_clause = {
        "multi_match": {
            "query": keywords,
            "fields": fields,
            "type": "phrase" if exact else "best_fields",
        }
    }
    if exact:
        match_clause["multi_match"]["operator"] = "and"
    return {
        "bool": {
            "must": [match_clause],
            "filter": _build_level_filter(level, scope_nodes),
        }
    }


def _build_level_filter(level: str, scope_nodes: list[str] | None = None) -> list[dict]:
    """层级筛选 + 目录节点过滤"""
    filters = []
    if level == "project": filters.append({"term": {"level": "project"}})
    elif level == "box": filters.append({"term": {"level": "box"}})
    elif level == "file": filters.append({"term": {"level": "file"}})
    if scope_nodes:
        filters.append({"terms": {"category": scope_nodes}})
    return filters


def _add_semantic_boost(query: dict, intent: dict) -> dict:
    """根据 LLM 意图调整 ES 查询权重"""
    suggest_fields = intent.get("suggest_fields", [])
    if suggest_fields and "bool" in query:
        # 对 LLM 建议的字段提高权重
        for clause in query["bool"].get("must", []):
            if "multi_match" in clause:
                existing = {f.split("^")[0]: float(f.split("^")[1]) if "^" in f else 1.0
                           for f in clause["multi_match"].get("fields", [])}
                for sf in suggest_fields:
                    field_name = sf.split("^")[0]
                    boost = float(sf.split("^")[1]) if "^" in sf else 2.0
                    if field_name in FIELD_BOOST:
                        existing[field_name] = FIELD_BOOST[field_name] * boost
                clause["multi_match"]["fields"] = [f"{k}^{v}" for k, v in existing.items()]

    # 时间范围过滤
    time_range = intent.get("time_range")
    if time_range and len(time_range) == 2 and time_range[0]:
        if "bool" not in query:
            query["bool"] = {}
        filters = query["bool"].get("filter", [])
        rng = {}
        if time_range[0]: rng["gte"] = time_range[0]
        if time_range[1]: rng["lte"] = time_range[1]
        filters.append({"range": {"year": rng}})
        query["bool"]["filter"] = filters

    return query


def _expand_synonyms(keywords: str) -> str:
    """扩展同义词"""
    terms = keywords.split()
    expanded = list(terms)
    for term in terms:
        if term in SYNONYM_MAP:
            expanded.extend(SYNONYM_MAP[term])
    return " ".join(expanded)


# ==================== 数据权限过滤（ES 层面） ====================

def _build_data_scope_filters(user: dict) -> list[dict]:
    """基于用户 tree_auth 构造 ES filter 子句"""
    from app.core.security import ROLE_SYSTEM_ADMIN, ROLE_ARCHIVE_ADMIN

    if user.get("role") in (ROLE_SYSTEM_ADMIN, ROLE_ARCHIVE_ADMIN):
        return []

    from app.core.database import SessionLocal
    from app.models.models import User as UserModel

    db = SessionLocal()
    try:
        u = db.query(UserModel).filter(UserModel.id == user.get("user_id")).first()
        if not u or not u.tree_auth:
            if u and u.department:
                return [{"term": {"department": u.department}}]
            return []

        tree_auth = u.tree_auth
        cats = set()
        depts = set()
        for node in tree_auth:
            if "/" in node:
                cat, dept = node.split("/", 1)
                cats.add(cat)
                depts.add(dept)
            else:
                cats.add(node)

        filters = []
        if cats and depts:
            filters.append({
                "bool": {
                    "should": [
                        {"terms": {"category": list(cats)}},
                        {"terms": {"department": list(depts)}},
                    ],
                    "minimum_should_match": 1,
                }
            })
        elif cats:
            filters.append({"terms": {"category": list(cats)}})
        elif depts:
            filters.append({"terms": {"department": list(depts)}})
        elif u.department:
            filters.append({"term": {"department": u.department}})

        return filters
    finally:
        db.close()


# ==================== ES 执行 ====================

def _execute_es_search(es, query: dict, page: int, page_size: int, t0: float, sort: str = "score", user: dict | None = None) -> dict:
    """执行 ES 搜索并格式化结果"""
    from_idx = (page - 1) * page_size

    # 数据权限过滤 — ES 层面的 category/department 过滤
    if user:
        data_filters = _build_data_scope_filters(user)
        if data_filters:
            if "bool" not in query:
                query = {"bool": {"must": [query]}}
            existing_filters = query["bool"].get("filter", [])
            query["bool"]["filter"] = existing_filters + data_filters

    sort_clause = [{"_score": "desc"}]
    if sort == "time_asc": sort_clause = [{"year": "asc"}]
    elif sort == "time_desc": sort_clause = [{"year": "desc"}]

    body = {
        "query": query,
        "from": from_idx,
        "size": page_size,
        "sort": sort_clause,
        "highlight": {
            "fields": {
                "title": {"number_of_fragments": 0},
                "full_text": {"fragment_size": 150, "number_of_fragments": 2},
            },
            "pre_tags": ["<mark class='search-highlight'>"],
            "post_tags": ["</mark>"],
        },
        "track_total_hits": True,
    }

    try:
        index = f"{settings.ES_INDEX_PREFIX}_fulltext"
        resp = es.search(index=index, body=body)

        hits = resp.get("hits", {})
        total = hits.get("total", {}).get("value", 0)
        results = []

        for hit in hits.get("hits", []):
            src = hit.get("_source", {})
            hl = hit.get("highlight", {})
            results.append({
                "archive_id": src.get("archive_id", ""),
                "title": hl.get("title", [src.get("title", "")])[0],
                "year": src.get("year"),
                "category": src.get("category", ""),
                "department": src.get("department", ""),
                "summary": " ".join(hl.get("full_text", [src.get("full_text", "")[:200]])),
                "relevance": round(hit.get("_score", 0) * 100 / 10, 1) if hit.get("_score") else 0,
                "risk_level": src.get("open_status", "低"),
            })

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": results,
            "query_time_ms": round((time.time() - t0) * 1000),
        }

    except Exception as e:
        return {
            "total": 0,
            "page": page,
            "page_size": page_size,
            "results": [],
            "query_time_ms": round((time.time() - t0) * 1000),
            "error": str(e),
        }


# ==================== SQLite 降级 ====================

def _fallback_search(keywords: str, page: int, page_size: int, t0: float, sort: str = "score", scope_nodes: list[str] | None = None, level: str = "all", user: dict | None = None, year_from: int | None = None, year_to: int | None = None, category: str | None = None, department: str | None = None, fonds_id: str | None = None, fonds_ids: list[str] | None = None, author: str | None = None, file_code: str | None = None, open_status: str | None = None, retention_period: str | None = None) -> dict:
    """ES 不可用时的 SQLite 降级搜索"""
    db = SessionLocal()
    try:
        from app.models.models import Archive
        from sqlalchemy import or_
        query = db.query(Archive)
        if user:
            from app.core.security import apply_data_scope
            query = apply_data_scope(user, query, Archive)
        if keywords:
            for kw in keywords.split():
                query = query.filter(
                    (Archive.title.contains(kw)) |
                    (Archive.ocr_text.contains(kw))
                )
        if scope_nodes:
            query = query.filter(Archive.category.in_(scope_nodes))
        # 高级筛选
        if year_from: query = query.filter(Archive.year >= year_from)
        if year_to: query = query.filter(Archive.year <= year_to)
        if category: query = query.filter(Archive.category == category)
        if department: query = query.filter(Archive.department == department)
        if author: query = query.filter(Archive.author.contains(author))
        if file_code: query = query.filter(Archive.file_code.contains(file_code))
        if fonds_id: query = query.filter(Archive.fonds_id == fonds_id)
        if fonds_ids: query = query.filter(Archive.fonds_id.in_(fonds_ids))
        if open_status: query = query.filter(Archive.open_status == open_status)
        if retention_period: query = query.filter(Archive.retention_period == retention_period)
        # 层级
        if level == "project":
            query = query.filter(Archive.level == "project")
        elif level == "box":
            query = query.filter(Archive.level == "box")
        elif level == "file":
            query = query.filter(Archive.level == "file")
        total = query.count()
        if sort == "time_asc": query = query.order_by(Archive.year.asc())
        elif sort == "time_desc": query = query.order_by(Archive.year.desc())
        rows = query.offset((page - 1) * page_size).limit(page_size).all()
        results = [{
            "archive_id": r.archive_id,
            "title": r.title,
            "year": r.year,
            "category": r.category or "",
            "department": r.department or "",
            "summary": (r.ocr_text or "")[:200],
            "relevance": 85.0,
            "risk_level": "低",
        } for r in rows]
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": results,
            "query_time_ms": round((time.time() - t0) * 1000),
        }
    finally:
        db.close()
