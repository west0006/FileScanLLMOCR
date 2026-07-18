"""
通用 Excel 导出工具

用法:
  from app.services.export import export_to_excel
  path = export_to_excel("搜索结果", [{"档案编号":"x","题名":"y"}], ["档案编号","题名"])
"""

import io
import os
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side


def export_to_excel(title: str, rows: list[dict], columns: list[str], output_dir: str = "/tmp") -> str:
    """生成 Excel 文件，返回文件路径"""
    wb = Workbook()
    ws = wb.active
    ws.title = title[:31]  # sheet 名最长 31 字符

    # 标题行
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(columns))
    title_cell = ws.cell(row=1, column=1, value=title)
    title_cell.font = Font(size=14, bold=True, color="1E2130")
    title_cell.alignment = Alignment(horizontal="center")
    ws.row_dimensions[1].height = 30

    # 副标题（导出时间）
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(columns))
    time_cell = ws.cell(row=2, column=1, value=f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}   共 {len(rows)} 条")
    time_cell.font = Font(size=10, color="9CA3AF")
    time_cell.alignment = Alignment(horizontal="center")

    # 表头
    header_fill = PatternFill(start_color="F5F6FA", end_color="F5F6FA", fill_type="solid")
    header_font = Font(size=11, bold=True, color="6B7280")
    thin_border = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0"),
    )
    for col_idx, col_name in enumerate(columns, 1):
        cell = ws.cell(row=4, column=col_idx, value=col_name)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[4].height = 24

    # 数据行
    data_font = Font(size=11, color="1E2130")
    for row_idx, row in enumerate(rows, 5):
        for col_idx, col_name in enumerate(columns, 1):
            val = row.get(col_name, "")
            if isinstance(val, list):
                val = ", ".join(str(v) for v in val)
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = data_font
            cell.border = thin_border

    # 列宽自适应
    for col_idx in range(1, len(columns) + 1):
        max_len = max(
            len(str(ws.cell(row=r, column=col_idx).value or ""))
            for r in range(4, 5 + min(len(rows), 100))
        )
        ws.column_dimensions[ws.cell(row=4, column=col_idx).column_letter].width = min(max_len + 4, 50)

    # 保存
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{title}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    filepath = os.path.join(output_dir, filename)
    wb.save(filepath)
    return filepath
