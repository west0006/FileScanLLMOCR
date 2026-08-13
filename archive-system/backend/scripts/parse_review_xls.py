"""
解析 1996 年审核工作用表 (.xls) → 提取训练数据结构

用法（在 L3 昇腾机或内网环境执行）：
  python scripts/parse_review_xls.py --input "z.about/相关文档/开放审核相关数据及模板/按卷整理原始数据样例及分类结果/中南财经大学1996（分类及统计结果）/" --output train/data/review_raw.json

输出 JSON 格式：
[
  {
    "archive_id": "1996-XZ-001",
    "title": "...",
    "year": 1996,
    "department": "保卫部",
    "category": "行政档案",
    "review_conclusion": "建议开放",  // 或 "建议不开放" "建议部分开放"
    "sensitive_notes": "...",         // 审核员备注
    "source_file": "1996中南财经大学档案开放审核工作用表（表2一表3）保卫部.xls"
  }
]
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import xlrd
except ImportError:
    print("请安装 xlrd: pip install xlrd")
    sys.exit(1)


def parse_xls_file(filepath: str, department: str = "") -> list[dict]:
    """解析单个 .xls 审核工作用表"""
    workbook = xlrd.open_workbook(filepath)
    records = []

    for sheet_idx in range(workbook.nsheets):
        sheet = workbook.sheet_by_index(sheet_idx)
        if sheet.nrows < 2:
            continue

        # 尝试自动检测表头行
        header_row = _find_header_row(sheet)
        if header_row is None:
            continue

        headers = [str(sheet.cell_value(header_row, c)).strip() for c in range(sheet.ncols)]

        # 映射列名到字段
        col_map = _map_columns(headers)

        for row_idx in range(header_row + 1, sheet.nrows):
            row_vals = [sheet.cell_value(row_idx, c) for c in range(sheet.ncols)]

            # 跳过空行
            if all(v == "" or v is None for v in row_vals):
                continue

            record = {
                "archive_id": _get_col(row_vals, col_map, "archive_id", ""),
                "title": _get_col(row_vals, col_map, "title", ""),
                "year": _get_col(row_vals, col_map, "year", 1996),
                "department": department or _get_col(row_vals, col_map, "department", ""),
                "category": _get_col(row_vals, col_map, "category", ""),
                "review_conclusion": _get_col(row_vals, col_map, "conclusion", ""),
                "sensitive_notes": _get_col(row_vals, col_map, "notes", ""),
                "source_file": os.path.basename(filepath),
                "source_sheet": sheet.name,
            }
            records.append(record)

    return records


def _find_header_row(sheet) -> int | None:
    """自动检测表头行——包含'序号'或'题名'或'档号'的列为表头"""
    for r in range(min(10, sheet.nrows)):
        row_text = " ".join(str(sheet.cell_value(r, c)) for c in range(sheet.ncols))
        if any(kw in row_text for kw in ["序号", "题名", "档号", "档案编号", "案卷号"]):
            return r
    # 回退：第一行
    return 0


def _map_columns(headers: list[str]) -> dict:
    """将列名映射到标准字段"""
    mapping = {}
    for i, h in enumerate(headers):
        h_lower = h.lower().replace(" ", "")
        if any(kw in h_lower for kw in ["序号", "档号", "编号", "案卷号", "archive_id"]):
            mapping["archive_id"] = i
        elif any(kw in h_lower for kw in ["题名", "标题", "名称", "title"]):
            mapping["title"] = i
        elif any(kw in h_lower for kw in ["年度", "年份", "归档年度", "year"]):
            mapping["year"] = i
        elif any(kw in h_lower for kw in ["单位", "归口", "部门", "department"]):
            mapping["department"] = i
        elif any(kw in h_lower for kw in ["门类", "类别", "category"]):
            mapping["category"] = i
        elif any(kw in h_lower for kw in ["审核结论", "开放建议", "审核意见", "conclusion", "建议"]):
            mapping["conclusion"] = i
        elif any(kw in h_lower for kw in ["备注", "说明", "敏感", "notes"]):
            mapping["notes"] = i
    return mapping


def _get_col(row: list, col_map: dict, key: str, default):
    """安全取列值"""
    idx = col_map.get(key)
    if idx is None or idx >= len(row):
        return default
    val = row[idx]
    if isinstance(val, float) and val == int(val):
        return int(val)
    return str(val).strip() if val else default


def extract_department_name(filename: str) -> str:
    """从文件名提取归口单位——如 '...保卫部.xls' → '保卫部'"""
    name = os.path.splitext(filename)[0]
    # 常见命名模式
    for dept in ["保卫部", "档案馆", "工会", "纪委", "人事处", "统战部", "学校办公室", "组织部", "财务处", "教务处"]:
        if dept in name:
            return dept
    return ""


def main():
    parser = argparse.ArgumentParser(description="解析审核工作用表 .xls")
    parser.add_argument("--input", "-i", required=True, help="输入目录（含 .xls 文件）")
    parser.add_argument("--output", "-o", default="train/data/review_raw.json", help="输出 JSON 路径")
    parser.add_argument("--glob", default="*.xls", help="文件匹配模式")
    args = parser.parse_args()

    input_dir = Path(args.input)
    if not input_dir.exists():
        print(f"❌ 目录不存在: {input_dir}")
        sys.exit(1)

    all_records = []
    xls_files = sorted(input_dir.rglob(args.glob))

    print(f"📂 找到 {len(xls_files)} 个 .xls 文件")

    for f in xls_files:
        dept = extract_department_name(f.name)
        print(f"  📄 {f.name} → 归口: {dept or '(自动检测)'}")
        try:
            records = parse_xls_file(str(f), dept)
            all_records.extend(records)
            print(f"     ✅ 提取 {len(records)} 条记录")
        except Exception as e:
            print(f"     ❌ 解析失败: {e}")

    # 输出
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    print(f"\n📊 总计: {len(all_records)} 条审核记录")
    print(f"💾 已保存: {output_path}")

    # 统计
    conclusions = {}
    for r in all_records:
        c = r.get("review_conclusion", "未知")
        conclusions[c] = conclusions.get(c, 0) + 1
    print(f"📋 审核结论分布: {conclusions}")


if __name__ == "__main__":
    main()
