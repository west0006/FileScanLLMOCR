"""
解析档案审核原始数据 (.xls) → 提取训练数据结构

真实审核结论数据源为「系统原始数据」案卷级 xls（含「开放标识」列：延期开放/开放；
「分类号」列：DQ→党群档案 / XZ→行政档案 等）。旧版指向的「中南财经大学1996（分类及统计结果）」
目录是工作任务表，无审核结论列，解析产物字段全脏，已弃用。

用法（在 L3 昇腾机或内网环境执行）：
  python scripts/parse_review_xls.py --input "z.about/相关文档/开放审核相关数据及模板/按卷整理原始数据样例及分类结果/系统原始数据（按卷整理的档案，系统导出表格版本）/" --output train/data/review_raw.json

输出 JSON 格式：
[
  {
    "archive_id": "1996-XZ-001",
    "title": "...",
    "year": 1996,
    "department": "保卫部",
    "category": "行政档案",
    "review_conclusion": "建议开放",  // 由「开放标识」列映射而来（开放/延期开放/不开放/部分开放）
    "sensitive_notes": "...",         // 备注列
    "source_file": "1财大文书档案-传统案卷级.xls"
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


# 分类号前 2 位 → 中文门类（与 seed.py _CAT_FONDS 反向映射一致）
_CATEGORY_CODE_MAP = {
    "DQ": "党群档案",
    "XZ": "行政档案",
    "JX": "教学档案",
    "KY": "科研档案",
    "RS": "人事档案",
    "CW": "财务档案",
    "JJ": "基建档案",
    "SX": "声像档案",
}

# 开放标识 → 建议枚举（对齐清单 RV-003 四档）
_CONCLUSION_MAP = {
    "开放": "建议开放",
    "延期开放": "建议延期开放",
    "不开放": "建议不开放",
    "部分开放": "建议部分开放",
    "建议开放": "建议开放",
    "建议部分开放": "建议部分开放",
    "建议延期开放": "建议延期开放",
    "建议不开放": "建议不开放",
}


def _map_category(raw) -> str:
    """分类号（如 DQ12 / XZ11）→ 中文门类；非编码值原样返回"""
    raw = str(raw).strip()
    code = raw[:2].upper()
    return _CATEGORY_CODE_MAP.get(code, raw)


def _map_conclusion(raw) -> str:
    """开放标识 → 建议枚举；非标准值原样返回"""
    raw = str(raw).strip()
    return _CONCLUSION_MAP.get(raw, raw)


def _to_int(v):
    """year 列可能是 float（1997.0）→ 转 int；非数值原样返回"""
    if isinstance(v, float) and v == int(v):
        return int(v)
    return v


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

        # 无「档号」或「题名」列的表（如纯汇总表）无法产出记录，跳过
        if "archive_id" not in col_map and "title" not in col_map:
            continue

        for row_idx in range(header_row + 1, sheet.nrows):
            row_vals = [sheet.cell_value(row_idx, c) for c in range(sheet.ncols)]

            # 跳过空行
            if all(v == "" or v is None for v in row_vals):
                continue

            archive_id = str(_get_col(row_vals, col_map, "archive_id", "")).strip()
            title = str(_get_col(row_vals, col_map, "title", "")).strip()
            # 档号与题名均空 → 表头残留行，跳过
            if not archive_id and not title:
                continue

            raw_cat = _get_col(row_vals, col_map, "category", "")
            raw_conclusion = _get_col(row_vals, col_map, "conclusion", "")

            record = {
                "archive_id": archive_id,
                "title": title,
                "year": _to_int(_get_col(row_vals, col_map, "year", "")),
                "department": department or str(_get_col(row_vals, col_map, "department", "")).strip(),
                "category": _map_category(raw_cat),
                "review_conclusion": _map_conclusion(raw_conclusion),
                "sensitive_notes": str(_get_col(row_vals, col_map, "notes", "")).strip(),
                "source_file": os.path.basename(filepath),
                "source_sheet": sheet.name,
            }
            records.append(record)

    return records


def _find_header_row(sheet) -> int | None:
    """自动检测表头行——含真实列名的行。找不到返回 None（不再 fallback 到标题行，
    避免把「表1：...年度...」这类标题误当表头、把标题里的「年度」误判为列名）。"""
    header_keywords = ["档号", "题名", "标题", "开放标识", "分类号", "责任者", "序号", "案卷号", "文件编号"]
    for r in range(min(10, sheet.nrows)):
        row_text = " ".join(str(sheet.cell_value(r, c)) for c in range(sheet.ncols))
        if any(kw in row_text for kw in header_keywords):
            return r
    return None


def _map_columns(headers: list[str]) -> dict:
    """将列名映射到标准字段。

    注意「档号」才是 archive_id，「序号」是行号不是档号，二者必须区分；
    「开放标识」才是审核结论，「分类号」是门类编码。"""
    mapping = {}
    for i, h in enumerate(headers):
        h_lower = h.lower().replace(" ", "")
        if any(kw in h_lower for kw in ["档号", "档案编号", "archive_id"]):
            mapping["archive_id"] = i
        elif any(kw in h_lower for kw in ["题名", "标题", "名称", "title"]):
            mapping["title"] = i
        elif any(kw in h_lower for kw in ["年度", "年份", "归档年度", "year"]):
            mapping["year"] = i
        elif any(kw in h_lower for kw in ["责任者", "归口", "单位", "部门", "department"]):
            mapping["department"] = i
        elif any(kw in h_lower for kw in ["分类号", "门类", "类别", "category"]):
            mapping["category"] = i
        elif any(kw in h_lower for kw in ["开放标识", "审核结论", "开放建议", "审核意见", "conclusion"]):
            mapping["conclusion"] = i
        elif any(kw in h_lower for kw in ["备注", "说明", "notes"]):
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
