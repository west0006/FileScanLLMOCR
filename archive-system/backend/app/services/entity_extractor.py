"""
中文档案实体抽取 — 基于正则 + 词典匹配

抽取实体类型:
  - PERSON:   中文姓名
  - ORG:      机构/单位
  - DATE:     日期/年份
  - DOC_ID:   文件编号 (校党字[1995]第12号)
  - EVENT:    事件关键词
  - LOCATION: 地名

用法:
  from app.services.entity_extractor import extract_entities
  entities = extract_entities(ocr_text)
  # [{"type": "PERSON", "name": "张某某", "start": 42, "end": 45}, ...]
"""

import re
from collections import defaultdict


# ============================================================
# 模式库
# ============================================================

# 常见中文姓氏 (top 100)
_SURNAMES = (
    "王李张刘陈杨黄赵周吴徐孙马胡朱郭何罗高林郑梁谢唐许冯宋韩邓彭曹曾田萧潘袁蔡蒋余于杜叶程魏苏吕丁任卢姚沈钟姜崔谭陆范汪廖石金韦贾夏付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤"
)

# 机构模式
_ORG_PATTERNS = [
    r"(中南财经(政法)?大学)",
    r"([\u4e00-\u9fa5]{2,6}(大学|学院|学校))",
    r"([\u4e00-\u9fa5]{2,8}(处|部|室|科|中心|办公室|委员会))",
    r"(校(党委|行政|工会|团委))",
    r"(国务院|教育部|省委|省政府|省教育厅)",
    r"(人事处|财务处|教务处|科研处|基建处|保卫部|组织部|宣传部|统战部|纪委|工会|档案馆)",
]

# 文件编号模式
_DOC_ID_PATTERNS = [
    r"([\u4e00-\u9fa5]+字?\[\d+\]第?\d*号?)",
    r"(校党字\[\d+\]第\d+号)",
    r"(\[[\d]+\][\u4e00-\u9fa5]+字?第?\d*号?)",
]

# 日期模式
_DATE_PATTERNS = [
    r"(\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日?)",
    r"(\d{4}\.\d{1,2}\.\d{1,2})",
    r"(\d{4}-\d{1,2}-\d{1,2})",
    r"(\d{4}\s*年\s*\d{1,2}\s*月)",
    r"(\d{4}\s*年)",
    r"([零一二三四五六七八九十百千]+年[零一二三四五六七八九十百千]+月)",
    r"(一九\d{2}年|二[零〇]\d{2}年)",
]

# 事件关键词
_EVENT_KEYWORDS = {
    "招生": ["招生", "录取", "入学", "招收"],
    "毕业": ["毕业", "结业", "校友"],
    "人事任免": ["任职", "任免", "任命", "免去", "退休", "调任"],
    "会议": ["会议", "大会", "常委会", "办公会", "党委会"],
    "财务": ["预算", "决算", "经费", "报销", "财务报告"],
    "教学": ["教学计划", "培养方案", "课程", "考试"],
    "处分": ["处分", "警告", "记过", "开除"],
    "审计": ["审计", "审核", "检查"],
    "建设": ["建设", "基建", "教学楼", "施工"],
    "党建": ["党委", "党支部", "党员", "入党", "组织生活"],
    "评优": ["评优", "表彰", "先进", "优秀"],
    "历史运动": ["文化大革命", "批林批孔", "大跃进", "反右", "整风", "四清"],
}

# 地名
_LOCATION_PATTERNS = [
    r"(湖北省|武汉市|武昌|汉口|汉阳)",
    r"([\u4e00-\u9fa5]{2,4}(市|区|县|镇|乡))",
]


# ============================================================
# 抽取引擎
# ============================================================

def extract_entities(text: str) -> list[dict]:
    """
    从文本中抽取实体。

    Returns:
        [{"type": "PERSON", "name": "张某某", "start": 42, "end": 45}, ...]
    """
    if not text:
        return []

    entities = []
    seen = set()  # (start, end, type) 去重

    # 1. 人名
    _extract_persons(text, entities, seen)

    # 2. 机构
    _extract_by_patterns(text, _ORG_PATTERNS, "ORG", entities, seen)

    # 3. 文件编号
    _extract_by_patterns(text, _DOC_ID_PATTERNS, "DOC_ID", entities, seen)

    # 4. 日期
    _extract_by_patterns(text, _DATE_PATTERNS, "DATE", entities, seen)

    # 5. 事件
    _extract_events(text, entities, seen)

    # 6. 地名
    _extract_by_patterns(text, _LOCATION_PATTERNS, "LOCATION", entities, seen)

    # 按位置排序
    entities.sort(key=lambda e: e["start"])

    return entities


def _extract_persons(text: str, entities: list, seen: set):
    """抽取中文姓名"""
    pattern = re.compile(rf'([{_SURNAMES}][\u4e00-\u9fa5]{{1,3}})')
    for m in pattern.finditer(text):
        full = m.group(1)
        # 过滤误匹配（全是姓氏本身不算）
        if len(full) < 2:
            continue
        key = (m.start(), m.end(), "PERSON", full)
        if key not in seen:
            seen.add(key)
            entities.append({
                "type": "PERSON",
                "name": full,
                "start": m.start(),
                "end": m.end(),
            })


def _extract_by_patterns(text: str, patterns: list[str], etype: str, entities: list, seen: set):
    """通用正则抽取"""
    for pat in patterns:
        for m in re.finditer(pat, text):
            key = (m.start(), m.end(), etype, m.group(1))
            if key not in seen:
                seen.add(key)
                entities.append({
                    "type": etype,
                    "name": m.group(1),
                    "start": m.start(),
                    "end": m.end(),
                })


def _extract_events(text: str, entities: list, seen: set):
    """抽取事件关键词"""
    for category, keywords in _EVENT_KEYWORDS.items():
        for kw in keywords:
            idx = 0
            while True:
                idx = text.find(kw, idx)
                if idx == -1:
                    break
                key = (idx, idx + len(kw), "EVENT", kw)
                if key not in seen:
                    seen.add(key)
                    entities.append({
                        "type": "EVENT",
                        "name": kw,
                        "category": category,
                        "start": idx,
                        "end": idx + len(kw),
                    })
                idx += 1


def extract_entity_summary(entities: list[dict]) -> dict:
    """将实体列表汇总为 {"PERSON": ["张三","李四"], "ORG": ["人事处"], ...}"""
    summary = defaultdict(list)
    for e in entities:
        name = e.get("name", "")
        if name not in summary[e["type"]]:
            summary[e["type"]].append(name)
    return dict(summary)


def find_shared_entities(entities_a: list[dict], entities_b: list[dict]) -> list[dict]:
    """找出两份档案的共享实体（用于构建关联边）"""
    names_a = {(e["type"], e.get("name", "")) for e in entities_a}
    shared = []
    for e in entities_b:
        key = (e["type"], e.get("name", ""))
        if key in names_a:
            shared.append(e)
    return shared
