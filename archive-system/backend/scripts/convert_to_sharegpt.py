"""
标注数据格式转换 — 从审核记录 JSON 转为 LLM 微调 ShareGPT 格式

用法：
  python scripts/convert_to_sharegpt.py --input train/data/review_raw.json --output train/data/review_sft.json

输出格式（LLaMA-Factory 兼容）：
[
  {
    "messages": [
      {"role": "system", "content": "系统提示词"},
      {"role": "user", "content": "档案全文"},
      {"role": "assistant", "content": "{JSON 审核结果}"}
    ]
  }
]
"""

import argparse
import json
from pathlib import Path


SYSTEM_PROMPT = """你是中南财经政法大学档案馆的档案开放审核专家。任务是审核档案全文，判断是否可以向社会开放。

审核依据：
1. 涉及党和国家秘密的 → 不予开放
2. 涉及未结论的重大问题/事件 → 不予开放
3. 涉及学校内部不对外公开事项的 → 不予开放
4. 涉及知识产权的 → 不予开放
5. 涉及个人隐私（身份证号、家庭出身、成绩单、健康信息等） → 不开放或部分开放
6. 所有上级来文和外收文 → 不予开放
7. 捐献档案未得到权属人书面同意的 → 不予开放
8. 党和国家及学校有特别规定的 → 不予开放

请输出 JSON 格式审核结果，包含：
- risk_score: 0-100 风险评分
- risk_level: "低"/"中"/"高"
- sensitive_items: [{type, content, start_char, end_char}]
- suggestion: "建议开放"/"建议部分开放"/"建议延期开放"/"建议不开放"
- reason: 建议理由
- confidence: 0.0-1.0 置信度"""


def convert_record(record: dict) -> dict | None:
    """单条记录转换"""
    full_text = record.get("full_text") or record.get("ocr_text") or ""
    conclusion = record.get("review_conclusion", "")

    if not full_text:
        return None

    # 将人工审核结论映射为 AI 输出格式
    suggestion_map = {
        "建议开放": {"risk_score": 10, "risk_level": "低", "suggestion": "建议开放"},
        "建议部分开放": {"risk_score": 40, "risk_level": "中", "suggestion": "建议部分开放"},
        "建议延期开放": {"risk_score": 75, "risk_level": "高", "suggestion": "建议延期开放"},
        "建议不开放": {"risk_score": 90, "risk_level": "高", "suggestion": "建议不开放"},
    }

    mapped = suggestion_map.get(conclusion, {"risk_score": 30, "risk_level": "中", "suggestion": "建议人工复核"})

    assistant_output = {
        "risk_score": mapped["risk_score"],
        "risk_level": mapped["risk_level"],
        "sensitive_items": record.get("sensitive_items", []),
        "suggestion": mapped["suggestion"],
        "reason": record.get("sensitive_notes", "") or record.get("reason", ""),
        "confidence": 0.9,
    }

    user_content = f"""请审核以下档案：

档案编号：{record.get('archive_id', '')}
题名：{record.get('title', '')}
归口单位：{record.get('department', '')}
归档年度：{record.get('year', '')}

全文内容：
{full_text}"""

    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": json.dumps(assistant_output, ensure_ascii=False, indent=2)},
        ]
    }


def main():
    parser = argparse.ArgumentParser(description="标注数据 → ShareGPT 格式转换")
    parser.add_argument("--input", "-i", required=True, help="审核记录 JSON")
    parser.add_argument("--output", "-o", default="train/data/review_sft.json", help="输出路径")
    args = parser.parse_args()

    input_path = Path(args.input)
    with open(input_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    converted = []
    skipped = 0
    for r in records:
        c = convert_record(r)
        if c:
            converted.append(c)
        else:
            skipped += 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(converted, f, ensure_ascii=False, indent=2)

    print(f"📊 转换完成: {len(converted)} 条有效 | {skipped} 条跳过（无全文）")
    print(f"💾 已保存: {output_path}")
    print(f"\n下一步: 将此文件注册到 LLaMA-Factory data/dataset_info.json")
    print(f"  \"archive_review\": {{\"file_name\": \"{output_path}\", \"formatting\": \"sharegpt\"}}")


if __name__ == "__main__":
    main()
