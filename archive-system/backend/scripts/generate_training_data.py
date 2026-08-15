"""
规则引擎批量标注 — 生成 LoRA 微调训练集

流程:
  1. 取种子数据 5 条档案的 OCR 全文（已有）
  2. 运行 hybrid_review() 规则引擎 → 得到自动审核结果
  3. 人工审核结论（来自种子数据）作为 ground truth
  4. 生成 ShareGPT 格式 review_sft.json

用法:
  python backend/scripts/generate_training_data.py
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.review_service import hybrid_review, scan_sensitive, calculate_risk_score
from app.core.database import SessionLocal
from app.models.models import Archive, ReviewRecord


# ============================================================
# 种子数据的 OCR 文本（来自 seed.py，已有完整全文）
# ============================================================

SEED_ARCHIVES = [
    {
        "archive_id": "1996-XZ-001",
        "title": "一九九六年招生工作总结",
        "year": 1996,
        "department": "学校办公室",
        "category": "行政档案",
        "ocr_text": (
            "关于一九九六年招生工作的总结报告\n\n"
            "本年度招生工作在校党委的领导下顺利完成。"
            "共录取本科生1200人，研究生300人。"
            "具体工作包括：制定招生计划、组织考试、录取审核等环节。\n\n"
            "存在问题：部分专业报考人数不足，需进一步优化专业设置。"
        ),
        "human_label": "建议开放",
    },
    {
        "archive_id": "1995-DQ-012",
        "title": "关于张某某同志任职的通知",
        "year": 1995,
        "department": "组织部",
        "category": "党群档案",
        "ocr_text": (
            "中南财经大学文件\n校党字[1995]第12号\n\n"
            "关于张某某同志任职的通知\n\n"
            "各党总支、直属党支部：\n"
            "经校党委常委会研究决定：任命张某某同志为会计系党总支副书记。\n\n"
            "该同志家庭出身工人，政治面貌中共党员…"
        ),
        "human_label": "建议不开放",
    },
    {
        "archive_id": "1973-JX-008",
        "title": "一九七三年教学计划安排",
        "year": 1973,
        "department": "教务处",
        "category": "教学档案",
        "ocr_text": (
            "一九七三年教学计划安排\n\n"
            "根据国务院[1973]教字XX号文件精神，"
            "结合我校实际情况，制定本年度教学计划。\n\n"
            "一、政治理论课安排\n"
            "认真学习中央文件精神，深入开展批林批孔运动…"
        ),
        "human_label": "建议延期开放",
    },
    {
        "archive_id": "1988-CW-003",
        "title": "一九八八年财务预决算报告",
        "year": 1988,
        "department": "财务处",
        "category": "财务档案",
        "ocr_text": (
            "中南财经大学一九八八年财务预决算报告\n\n"
            "一、年度预算执行情况\n"
            "总收入XXX万元，总支出XXX万元，结余XXX万元。\n"
            "二、重点支出项目\n"
            "1.教学楼建设XXX万元\n2.科研经费XXX万元"
        ),
        "human_label": "建议开放",
    },
    {
        "archive_id": "2000-RS-015",
        "title": "关于李某等同志退休的通知",
        "year": 2000,
        "department": "人事处",
        "category": "人事档案",
        "ocr_text": (
            "关于李某等同志退休的通知\n\n"
            "根据国家有关规定，李某（身份证号42010619400101XXXX）、"
            "王某等同志已达到退休年龄，经研究决定…"
        ),
        "human_label": "建议部分开放",
    },
]


# ============================================================
# 数据增强：基于不同档案类型的模板文本
# ============================================================

AUGMENTED_TEXTS = [
    # 行政档案（低风险）
    {
        "archive_id": "AUG-XZ-001",
        "title": "二〇〇〇年行政工作总结",
        "year": 2000,
        "department": "学校办公室",
        "category": "行政档案",
        "ocr_text": (
            "中南财经大学二〇〇〇年行政工作总结\n\n"
            "本年度在学校党委的领导下，各项工作有序推进。"
            "完成了教学评估、学科建设、师资引进等重点工作。"
            "全校师生团结奋进，取得了显著成绩。"
        ),
    },
    {
        "archive_id": "AUG-XZ-002",
        "title": "关于加强校园管理的通知",
        "year": 2005,
        "department": "学校办公室",
        "category": "行政档案",
        "ocr_text": (
            "关于加强校园管理的通知\n\n"
            "为进一步规范校园秩序，保障师生安全，"
            "经学校研究决定，自即日起实施以下管理措施："
            "一、严格门禁制度\n二、规范车辆停放\n三、加强夜间巡逻"
        ),
    },
    # 党群档案（中/高风险）
    {
        "archive_id": "AUG-DQ-001",
        "title": "关于王某同志违纪问题的调查报告",
        "year": 1998,
        "department": "纪委",
        "category": "党群档案",
        "ocr_text": (
            "关于王某同志违纪问题的调查报告\n\n"
            "根据群众举报，纪委对王某同志涉嫌贪污问题进行了调查。"
            "经查，王某在担任财务处副处长期间，涉嫌挪用公款。"
            "调查中发现该同志存在受贿、弄虚作假等问题。"
            "建议给予纪律处分并移送司法机关。"
        ),
    },
    {
        "archive_id": "AUG-DQ-002",
        "title": "关于组织学习中央文件的通知",
        "year": 2003,
        "department": "组织部",
        "category": "党群档案",
        "ocr_text": (
            "关于组织学习中央文件精神的通知\n\n"
            "各党总支、直属党支部：\n"
            "根据上级要求，请各单位组织全体党员认真学习文件精神，"
            "深入领会，结合实际抓好贯彻落实。"
        ),
    },
    # 历史档案（高风险）
    {
        "archive_id": "AUG-LS-001",
        "title": "关于贯彻上级指示的意见",
        "year": 1968,
        "department": "学校办公室",
        "category": "行政档案",
        "ocr_text": (
            "关于贯彻上级指示的意见\n\n"
            "根据省革命委员会文件精神，结合我校实际情况，"
            "对当前文化大革命运动提出以下意见："
            "一、深入开展批斗改运动\n"
            "二、红卫兵组织要进一步发挥作用\n"
            "三、清理阶级队伍，揪出走资派\n"
            "四、加强对工宣队的领导"
        ),
    },
    {
        "archive_id": "AUG-LS-002",
        "title": "大跃进时期工作总结",
        "year": 1959,
        "department": "学校办公室",
        "category": "行政档案",
        "ocr_text": (
            "一九五九年大跃进工作总结\n\n"
            "在总路线、大跃进、人民公社三面红旗指引下，"
            "我校师生积极响应党的号召，大炼钢铁，赶英超美。"
            "全年共炼钢XX吨，超额完成上级下达的任务。"
            "但也存在浮夸风、瞎指挥等问题。"
        ),
    },
    # 人事档案（中风险 - 含个人隐私）
    {
        "archive_id": "AUG-RS-001",
        "title": "教职工年度考核表",
        "year": 2010,
        "department": "人事处",
        "category": "人事档案",
        "ocr_text": (
            "教职工年度考核表\n\n"
            "姓名：李某某\n身份证号：42010619780501XXXX\n"
            "家庭出身：工人\n政治面貌：中共党员\n\n"
            "年度考核结果：优秀\n备注：该同志工作认真负责。"
        ),
    },
    {
        "archive_id": "AUG-RS-002",
        "title": "关于引进高层次人才的报告",
        "year": 2015,
        "department": "人事处",
        "category": "人事档案",
        "ocr_text": (
            "关于引进高层次人才的报告\n\n"
            "根据学校学科建设需要，拟引进计算机科学领域"
            "博士研究生导师一名。经面试考核，候选人学术水平"
            "符合要求，建议予以引进。年薪标准参照相关规定执行。"
        ),
    },
    # 财务档案（低风险）
    {
        "archive_id": "AUG-CW-001",
        "title": "二〇一〇年度财务报告",
        "year": 2010,
        "department": "财务处",
        "category": "财务档案",
        "ocr_text": (
            "中南财经大学二〇一〇年度财务报告\n\n"
            "一、收入情况：本年度总收入XX万元\n"
            "二、支出情况：教学支出XX万元，科研支出XX万元\n"
            "三、结余情况：年度结余XX万元\n"
            "本报告已经审计处审核，数据真实有效。"
        ),
    },
    # 教学档案（低风险）
    {
        "archive_id": "AUG-JX-001",
        "title": "关于修订本科培养方案的通知",
        "year": 2018,
        "department": "教务处",
        "category": "教学档案",
        "ocr_text": (
            "关于修订本科培养方案的通知\n\n"
            "各学院：\n"
            "根据教育部最新文件精神，现启动2020版本科培养方案修订工作。"
            "请各学院于本学期末完成初稿，下学期开学前提交终稿。"
        ),
    },
]


SYSTEM_PROMPT = """你是中南财经政法大学档案馆的档案开放审核专家。任务是审核档案全文，判断是否可以向社会开放。

审核依据：
1. 涉及党和国家秘密的（绝密/机密/秘密/国防/军事）→ 不予开放
2. 涉及未结论重大问题/事件（待调查/审理中）→ 不予开放
3. 涉及学校内部不对外公开事项的 → 不予开放
4. 涉及知识产权的 → 不予开放
5. 涉及个人隐私（身份证号、家庭出身、政治面貌、成绩单、健康信息等）→ 不开放或部分开放
6. 所有上级来文和外收文（国务院/教育部/省委/省政府）→ 不予开放
7. 捐献档案未得到权属人书面同意的 → 不予开放
8. 涉及历史敏感词汇（文革/大跃进/反右等）→ 需结合上下文判断

请输出 JSON 格式审核结果，包含：
- risk_score: 0-100 风险评分
- risk_level: "低"/"中"/"高"
- sensitive_items: [{type, content, start_char, end_char}]
- suggestion: "建议开放"/"建议部分开放"/"建议延期开放"/"建议不开放"
- reason: 建议理由（100字以内）
- confidence: 0.0-1.0 置信度"""


# 建议 → (risk_score, risk_level, reason) 一致性映射，避免人工标签与规则评分冲突
_LABEL_MAP = {
    "建议开放": (10, "低", "未检测到敏感信息，档案内容为常规管理文件，建议开放。"),
    "建议部分开放": (35, "中", "档案包含部分敏感信息，建议对相关段落脱敏后部分开放。"),
    "建议延期开放": (55, "中", "档案涉及上级来文或未结论事项，建议延期开放。"),
    "建议不开放": (85, "高", "档案涉及国家秘密或个人隐私，建议不开放。"),
}


def _label_consistent(suggestion: str):
    """返回与 suggestion 一致的 (risk_score, risk_level, reason)"""
    return _LABEL_MAP.get(suggestion, (10, "低", "未检测到敏感信息，档案内容为常规管理文件，建议开放。"))


def main():
    # 1. 种子数据 → 规则引擎标注
    print("=" * 60)
    print("  规则引擎批量标注")
    print("=" * 60)

    train_data = []
    total = len(SEED_ARCHIVES) + len(AUGMENTED_TEXTS)

    # 种子数据
    for item in SEED_ARCHIVES:
        print(f"\n  📄 {item['archive_id']}: {item['title'][:30]}...")

        # 规则引擎审核
        result = hybrid_review(item["ocr_text"], {
            "archive_id": item["archive_id"],
            "title": item["title"],
            "year": item["year"],
            "department": item["department"],
        })

        # 用人工标签覆盖规则引擎建议（以人工为准）—— 同步校正 score/level/reason，避免样本自相矛盾
        suggestion = item.get("human_label", result["suggestion"])
        score, level, reason = _label_consistent(suggestion)

        assistant_output = {
            "risk_score": score,
            "risk_level": level,
            "sensitive_items": result["sensitive_items"],
            "suggestion": suggestion,
            "reason": reason,
            "confidence": 0.85,
        }

        user_content = f"""请审核以下档案：

档案编号：{item['archive_id']}
题名：{item['title']}
归口单位：{item['department']}
归档年度：{item['year']}
门类：{item.get('category', '')}

全文内容：
{item['ocr_text']}"""

        train_data.append({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": json.dumps(assistant_output, ensure_ascii=False)},
            ]
        })

        print(f"     规则评分: {result['risk_score']} ({result['risk_level']}) | 人工标签: {suggestion}")

    # 数据增强
    for item in AUGMENTED_TEXTS:
        print(f"\n  📄 {item['archive_id']}: {item['title'][:30]}...")

        result = hybrid_review(item["ocr_text"], {
            "archive_id": item["archive_id"],
            "title": item["title"],
            "year": item["year"],
            "department": item["department"],
        })

        assistant_output = {
            "risk_score": result["risk_score"],
            "risk_level": result["risk_level"],
            "sensitive_items": result["sensitive_items"],
            "suggestion": result["suggestion"],
            "reason": result["reason"],
            "confidence": 0.8,
        }

        user_content = f"""请审核以下档案：

档案编号：{item['archive_id']}
题名：{item['title']}
归口单位：{item['department']}
归档年度：{item['year']}
门类：{item.get('category', '')}

全文内容：
{item['ocr_text']}"""

        train_data.append({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": json.dumps(assistant_output, ensure_ascii=False)},
            ]
        })

        print(f"     规则评分: {result['risk_score']} ({result['risk_level']}) | {result['suggestion']}")

    # 写入文件
    output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "train", "data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "review_sft.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(train_data, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"  ✅ 生成 {len(train_data)} 条训练数据")
    print(f"  💾 {output_path}")
    print(f"\n  标签分布:")
    labels = {}
    for d in train_data:
        assistant = json.loads(d["messages"][2]["content"])
        s = assistant["suggestion"]
        labels[s] = labels.get(s, 0) + 1
    for k, v in sorted(labels.items(), key=lambda x: -x[1]):
        bar = "█" * v
        print(f"    {k}: {v} {bar}")
    print(f"\n  下一步: 上传到 LLaMA-Factory http://10.11.13.100:7860")
    print(f"  注册数据集名: archive_review")


if __name__ == "__main__":
    main()
