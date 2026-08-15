"""
档案数据脱敏脚本 — 在 L3 昇腾机内网执行，输出脱敏后数据到 L2

用法：
  python scripts/desensitize.py --input raw_data.json --output train/data/desensitized.json

脱敏规则：
  - 中文姓名 → "张某某" "李某某"（保留姓）
  - 身份证号 → "420106********1234"
  - 电话号码 → "0***-*******"
  - 具体单位 → "某单位" "某部门"
  - 地址 → "某市某区..."
  - 保留文本长度和结构特征
"""

import argparse
import json
import re
import random
from pathlib import Path


# 常见中文姓氏
_SURNAMES = ["张", "李", "王", "刘", "陈", "杨", "黄", "赵", "周", "吴",
             "徐", "孙", "马", "朱", "胡", "郭", "何", "林", "罗", "高"]

# 替换用通用词
_DEPT_REPLACE = ["某单位", "某部门", "某处室", "某学院"]
_ADDR_REPLACE = ["某市某区某路", "某省某市", "某地"]


def desensitize_name(text: str) -> str:
    """中文姓名脱敏：保留姓 + 某某"""
    # 匹配 2-4 字中文姓名模式
    pattern = re.compile(r'(?<![a-zA-Z0-9])[' + ''.join(_SURNAMES) + r'][\u4e00-\u9fa5]{1,3}(?![a-zA-Z0-9])')
    used_names = set()

    def _replace(match):
        full = match.group(0)
        surname = full[0]
        key = surname
        counter = 0
        while key in used_names:
            counter += 1
            key = f"{surname}_{counter}"
        used_names.add(key)
        return surname + "某" * (len(full) - 1)

    return pattern.sub(_replace, text)


def desensitize_id_card(text: str) -> str:
    """身份证号脱敏（(?<!\d)(?!\d) 替代 \b，因汉字属 \w 使 \b 在中文语境失效）"""
    return re.sub(
        r'(?<!\d)\d{6}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dxX](?!\d)',
        lambda m: m.group(0)[:6] + '********' + m.group(0)[-4:],
        text,
    )


def desensitize_phone(text: str) -> str:
    """电话号码脱敏"""
    text = re.sub(r'(?<!\d)1[3-9]\d{9}(?!\d)', '1**********', text)
    text = re.sub(r'(?<!\d)0\d{2,3}-\d{7,8}(?!\d)', '0***-*******', text)
    return text


def desensitize_dept(text: str) -> str:
    """单位名称脱敏"""
    # 匹配 "XXX大学" "XXX学院" "XXX处" "XXX部"
    patterns = [
        (r'[\u4e00-\u9fa5]{2,6}(大学|学院|学校)', lambda m: '某大学'),
        (r'[\u4e00-\u9fa5]{2,8}(处|部|室|科|中心)', lambda m: random.choice(_DEPT_REPLACE)),
    ]
    for pat, repl in patterns:
        text = re.sub(pat, repl, text)
    return text


def desensitize_address(text: str) -> str:
    """地址脱敏"""
    pattern = re.compile(r'[\u4e00-\u9fa5]{2,10}(市|区|县|镇|路|街|巷|号|弄)[\u4e00-\u9fa5\d号栋单元室]*')
    return pattern.sub(lambda m: random.choice(_ADDR_REPLACE), text)


def desensitize_full(text: str) -> str:
    """全量脱敏"""
    if not text:
        return text
    text = desensitize_id_card(text)
    text = desensitize_phone(text)
    text = desensitize_name(text)
    text = desensitize_address(text)
    text = desensitize_dept(text)
    return text


def main():
    parser = argparse.ArgumentParser(description="档案数据脱敏")
    parser.add_argument("--input", "-i", required=True, help="原始 JSON 文件")
    parser.add_argument("--output", "-o", default="train/data/desensitized.json", help="输出路径")
    parser.add_argument("--fields", nargs="*", default=["full_text", "title", "notes"],
                        help="需要脱敏的字段名（默认: full_text title notes）")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ 文件不存在: {input_path}")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"📂 加载 {len(data)} 条记录")

    for i, record in enumerate(data):
        for field in args.fields:
            if field in record and record[field]:
                record[field] = desensitize_full(str(record[field]))
        if i % 100 == 0 and i > 0:
            print(f"  ⏳ 已处理 {i}/{len(data)}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 脱敏完成: {len(data)} 条 → {output_path}")


if __name__ == "__main__":
    main()
