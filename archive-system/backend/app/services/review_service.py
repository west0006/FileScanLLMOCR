"""
审核规则引擎 — 敏感词分类匹配 + 规则评分

敏感词来源：z.about/相关文档/敏感词.md (400+ 词条)
分类依据：z.about/相关文档/档案控制使用和开放范围.md (9 类不予开放情形)
"""

# ==================== 敏感词分类库 ====================
# 按 9 类不予开放情形组织

SENSITIVE_RULES = {
    # (一) 涉及党和国家秘密的
    "国家秘密": [
        "秘密", "机密", "绝密", "机要", "秘密工作", "秘密组织",
        "国防", "国防设施", "国家安全局", "国家安全部",
        "军备合同", "军事情报", "军事组织", "军委", "军宣队",
        "总参", "总后", "总政", "驻青部队", "战略防御",
        "研发机密", "合作机密", "窃密", "窃取", "刺探",
    ],
    # (二) 涉及党和国家重大问题、重大事件尚未作出结论的
    "未结论重大事项": [
        "尚未结论", "审定中", "审理情况", "审查", "封闭审查",
        "组织调查", "政审", "人事调查", "事故调查",
        "待调查", "调查中", "未公开",
    ],
    # (三) 涉及学校不对外公开事项的
    "内部事项": [
        "内部文件", "不宜公开", "不对外公开", "内部会议",
        "评价不公开", "行政划分", "特殊处理",
    ],
    # (四) 涉及知识产权的
    "知识产权": [
        "知识产权", "专利", "版权", "商标",
    ],
    # (五) 涉及个人隐私的
    "个人隐私": [
        "个人隐私", "个人声誉", "个人形象", "人格荣辱",
        "生活历程", "成份谈话记录", "家庭出身",
        "人事调查", "纪检处理", "纪检审查", "纪律审查",
        "处分", "作风问题", "检讨", "坦白材料",
    ],
    # (六) 档案形成者要求限制利用范围的
    "限制利用": [
        "限制利用", "不公开", "内部阅览",
    ],
    # (七) 所有上级来文和外收文
    "上级来文": [
        "上级来文", "外收文", "国务院", "教育部",
        "中央文件", "省委", "省政府", "部委",
    ],
    # (八) 接收捐献和寄存档案，未得到权属人书面同意的
    "捐献未授权": [
        "捐献", "寄存", "捐赠",
    ],
    # (九) 敏感历史/政治词汇 — 需结合上下文判断
    "历史敏感": [
        "文革", "文化大革命", "文功武卫", "破四旧",
        "大跃进", "大炼钢铁运动", "大饥荒", "赶英超美", "鸣放",
        "反右", "右派", "极右", "中右", "整风", "摘帽",
        "红卫兵", "工宣队", "农宣队", "军宣队", "革委会", "革分会",
        "造反", "走资派", "批斗改", "批林", "批孔",
        "四人帮", "林彪", "九一三",
        "三反", "五反", "四清", "肃反", "镇反", "一打三反",
        "三支两军", "清理阶级队伍", "两清运动", "五不准学习班",
        "下放", "劳动教养", "劳教",
        "四类分子", "坏分子", "三种人",
        "工总", "钢二司", "钢新之争", "钢九一三", "七二〇",
        "武汉市革命委员会", "湖北省革命委员会", "湖北大学革命委员会",
        "胡厚民", "胡耀邦", "胡风", "夏邦银", "张立国", "赵辛初", "钟汉华", "朱洪霞",
        "高自联", "学潮", "学运", "四二六事件",
        "法轮功", "异教徒", "邪教", "自焚",
        "西藏问题", "领土安全", "领土争端", "民族纠纷", "民族矛盾",
        "示威", "游行", "抗议", "绝食", "罢工", "罢课", "暴动", "暴乱", "动乱",
        "武装冲突", "戒严", "倾覆", "策反",
    ],
    # 违法犯罪类
    "违法犯罪": [
        "贪污", "受贿", "行贿", "贿赂", "走私", "贩毒", "贩黄", "贩私",
        "偷税", "投机倒把", "挪用", "滥用职权",
        "强奸", "奸污", "奸淫", "猥亵", "嫖娼", "嫖妓", "嫖宿", "卖淫",
        "杀害", "投敌", "投诚", "投降", "叛国", "叛党", "反党", "反动", "反革命", "反共",
        "特务", "内奸", "间谍",
        "窝藏", "串供", "胁迫",
        "有组织犯罪", "恐怖袭击",
        "无期徒刑", "有期徒刑", "拘役", "逮捕", "批捕", "起诉",
    ],
    # 违法违规/纪律类
    "违纪违规": [
        "违法违纪", "违法审理", "违纪处理", "违纪调查", "违规行动",
        "弄虚作假", "谎报", "虚假报告", "虚假指控",
        "诬蔑", "污蔑", "诽谤", "侮辱", "造谣", "迫害造谣",
        "舞弊", "监守自盗", "小偷小摸", "偷盗", "偷摸", "偷窃",
        "挑拨离间", "煽动",
        "双规", "双反运动",
    ],
    # 其他敏感
    "其他敏感": [
        "敏感信息共享", "敏感文化", "事务机密", "外交秘密", "外交渠道", "外交文件",
        "侨务方针", "侨务政策", "统战工作", "两党合作",
        "民主运动", "民主墙", "民主评议会", "民主生活会",
        "领导人通信", "世维大会", "三青团",
        "宪政部门", "宪政制度", "宪政组织", "白旗",
        "特殊行动队", "特殊任务组", "特殊手段", "特殊机构", "特殊训练",
        "战犯", "战俘", "债务纠纷",
    ],
}

# 扁平化为快速查找
_ALL_WORDS: dict[str, str] = {}  # word → category
for _cat, _words in SENSITIVE_RULES.items():
    for w in _words:
        _ALL_WORDS[w] = _cat


# ==================== 规则扫描 ====================

def scan_sensitive(full_text: str) -> list[dict]:
    """
    扫描全文，返回所有命中的敏感词及其位置。
    时间复杂度 O(n*m)，但 400 词 × 几千字档案 在 Python 中 < 50ms。
    """
    hits = []
    seen = set()  # 去重

    for word, category in _ALL_WORDS.items():
        idx = 0
        while True:
            idx = full_text.find(word, idx)
            if idx == -1:
                break
            key = f"{word}:{idx}"
            if key not in seen:
                seen.add(key)
                # 提取上下文（前后各 15 字）
                ctx_start = max(0, idx - 15)
                ctx_end = min(len(full_text), idx + len(word) + 20)
                hits.append({
                    "type": category,
                    "word": word,
                    "content": full_text[ctx_start:ctx_end],
                    "start_char": idx,
                    "end_char": idx + len(word),
                })
            idx += 1

    return hits


# ==================== 规则评分 ====================

# 各类敏感词的严重程度权重
CATEGORY_WEIGHT = {
    "国家秘密": 1.0,
    "历史敏感": 0.7,
    "违法犯罪": 0.8,
    "违纪违规": 0.6,
    "个人隐私": 0.5,
    "内部事项": 0.4,
    "未结论重大事项": 0.6,
    "上级来文": 0.3,
    "知识产权": 0.2,
    "限制利用": 0.3,
    "捐献未授权": 0.2,
    "其他敏感": 0.4,
}


def calculate_risk_score(rule_hits: list[dict]) -> tuple[float, str]:
    """
    基于规则命中计算风险评分和等级。

    评分逻辑：
    - 每个命中加权累加
    - 不同类别命中数影响整体风险
    - 上限 95（留 5 分给 LLM）
    """
    if not rule_hits:
        return 0.0, "低"

    # 各类别命中数
    cat_counts: dict[str, int] = {}
    for hit in rule_hits:
        cat = hit["type"]
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    # 加权评分
    score = 0.0
    for cat, count in cat_counts.items():
        weight = CATEGORY_WEIGHT.get(cat, 0.3)
        # 第一个命中权重高，后续递减
        score += weight * 15  # 首次命中基础分
        if count > 1:
            score += weight * min(count - 1, 5) * 3  # 额外命中加分，封顶

    # 多类别加成
    unique_cats = len(cat_counts)
    if unique_cats >= 3:
        score *= 1.2
    if unique_cats >= 5:
        score *= 1.3

    score = min(score, 95.0)
    score = round(score, 1)

    # 等级
    if score <= 20:
        level = "低"
    elif score <= 60:
        level = "中"
    else:
        level = "高"

    return score, level


# ==================== 双引擎融合 ====================

def hybrid_review(full_text: str, metadata: dict | None = None) -> dict:
    """
    双引擎融合审核：
    1. 规则引擎快速扫描敏感词
    2. LLM 语义理解（修正误报/补漏）
    3. 融合评分
    """
    from app.services.llm_client import llm_client

    # 第一层：规则引擎
    rule_hits = scan_sensitive(full_text)
    rule_score, rule_level = calculate_risk_score(rule_hits)

    # 第二层：LLM 语义审核
    llm_result = llm_client.review(full_text, metadata)
    llm_score = llm_result.get("risk_score", 0)
    llm_level = llm_result.get("risk_level", "中")

    # 第三层：融合 (规则 50% + LLM 50%——审核场景需偏保守)
    final_score = round(rule_score * 0.5 + llm_score * 0.5, 1)

    # 最终等级
    if final_score <= 20:
        final_level, suggestion = "低", "建议开放"
    elif final_score <= 60:
        final_level, suggestion = "中", "建议人工重点关注"
    else:
        final_level, suggestion = "高", "建议延期开放或不予开放"

    # 合并敏感项
    sensitive_items = llm_result.get("sensitive_items", [])
    llm_types = {s.get("type", "") for s in sensitive_items}
    for hit in rule_hits:
        if hit["type"] not in llm_types:
            sensitive_items.append({
                "type": hit["type"],
                "content": hit["content"],
                "start_char": hit["start_char"],
                "end_char": hit["end_char"],
                "source": "rule_engine",
            })

    # 只保留前 20 条，避免返回过大
    sensitive_items = sensitive_items[:20]

    return {
        "risk_score": final_score,
        "risk_level": final_level,
        "sensitive_items": sensitive_items,
        "suggestion": suggestion,
        "reason": llm_result.get("reason", _default_reason(final_score, rule_hits)),
        "rule_hits_count": len(rule_hits),
        "rule_categories": list(set(h["type"] for h in rule_hits)),
        "llm_raw_score": llm_score,
        "llm_confidence": llm_result.get("confidence", 0),
        "rule_raw_score": rule_score,
    }


def _default_reason(score: float, hits: list[dict]) -> str:
    """当 LLM 不可用时，基于规则命中生成理由"""
    if not hits:
        return "未检测到敏感信息，档案内容为常规管理文件，建议开放。"
    cats = list(set(h["type"] for h in hits))
    return f"检测到 {len(hits)} 处敏感信息，涉及 {', '.join(cats)}，建议人工复核。"
