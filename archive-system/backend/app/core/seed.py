"""
种子数据 — 首次启动自动插入演示数据

包含：
- 默认管理员账号
- 示例档案（覆盖不同年代/门类/归口单位）
- 示例 OCR 文本
- 示例预审记录
"""

from datetime import datetime

from app.core.database import SessionLocal, Base, engine
from app.core.security import hash_password
from app.models.models import User, Role, Archive, ReviewRecord, ReviewTask, OperationLog


def seed(force: bool = False):
    """插入种子数据，已存在则跳过。force=True 时先清空再重建。"""
    db = SessionLocal()
    try:
        if force:
            # 清空所有业务数据（保留表结构）
            for table in [ReviewRecord, OperationLog, Archive, User, Role]:
                db.query(table).delete()
            db.commit()
            print("🗑️  已清空旧种子数据")

        # ---- 角色 ----
        if db.query(Role).count() == 0:
            db.add_all([
                Role(name="system_admin", description="系统管理员",
                     permissions={"all": True}, data_scope={"all": True}),
                Role(name="archive_admin", description="档案管理员",
                     permissions={
                         "search": {"view": True, "download": True, "print": True},
                         "ocr": True, "sync": True, "stats": True,
                     },
                     data_scope={"all": True}),
                Role(name="reviewer", description="审核员",
                     permissions={
                         "search": {"view": True, "download": False, "print": False},
                         "review": {"view": True, "export": False},
                     },
                     data_scope={"departments": []}),
            ])

        # ---- 默认管理员（始终确保为 system_admin） ----
        admin_user = db.query(User).filter(User.username == "admin").first()
        if admin_user:
            # 已存在但可能被 dev 模式误创建为 reviewer → 修正
            if admin_user.role != "system_admin":
                admin_user.role = "system_admin"
                db.commit()
        else:
            db.add(User(
                username="admin", name="系统管理员", department="档案馆",
                password_hash=hash_password("Admin@123456"),
                role="system_admin", is_active=True,
            ))

        # ---- 示例档案（60+ 条，覆盖 8 门类 × 6 部门 × 5 年度区间） ----
        if db.query(Archive).count() == 0:
            archives = _generate_seed_archives()
            db.add_all(archives)
            db.commit()

        # ---- 示例用户（除 admin 外，各角色测试用户，不存在则创建） ----
        _ensure_test_user(db, "reviewer1", "王建国", "学校办公室", "reviewer")
        _ensure_test_user(db, "reviewer2", "赵静", "教务处", "reviewer")
        _ensure_test_user(db, "reviewer3", "李芳", "人事处", "reviewer")
        _ensure_test_user(db, "archivist", "陈小红", "档案馆", "archive_admin")

        # ---- 示例预审记录（为部分档案生成，覆盖各风险等级） ----
        if db.query(ReviewRecord).count() == 0:
            review_records = _generate_seed_reviews()
            # 关联到一个示例预审任务，使「预审任务」页开箱即显示风险分布
            if db.query(ReviewTask).count() == 0:
                demo_task = ReviewTask(
                    task_name="示例批量预审任务",
                    batch_name="演示批次",
                    status="completed",
                    total_count=len(review_records),
                    completed_count=len(review_records),
                    created_by=1,
                    finished_at=datetime.utcnow(),
                )
                db.add(demo_task)
                db.flush()  # 获取 demo_task.id
                for r in review_records:
                    r.task_id = demo_task.id
            db.add_all(review_records)
            db.commit()

        # ---- 示例操作日志（多样化的最近操作） ----
        if db.query(OperationLog).count() == 0:
            logs = _generate_seed_logs()
            db.add_all(logs)
            db.commit()

        db.commit()
        print("✅ 种子数据已插入")
        print("   默认管理员: admin / Admin@123456")
        print(f"   示例档案: {db.query(Archive).count()} 条")
        print(f"   预审记录: {db.query(ReviewRecord).count()} 条")

        # ---- 生成模拟档案文件（供下载/预览测试） ----
        _seed_mock_files()

    except Exception as e:
        db.rollback()
        print(f"⚠️ 种子数据插入失败: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()


# ==================== 种子数据生成器 ====================

# 门类 → 部门 映射
_CAT_DEPT = {
    "行政档案": ["学校办公室", "发展规划部", "人事部"],
    "党群档案": ["组织部", "宣传部", "纪委", "工会"],
    "教学档案": ["教务处", "研究生院", "招生办公室"],
    "科研档案": ["科研处"],
    "人事档案": ["人事处"],
    "财务档案": ["财务处"],
    "基建档案": ["基建处"],
    "声像档案": ["档案馆"],
}

# 门类 → 全宗号
_CAT_FONDS = {
    "行政档案": "XZ", "党群档案": "DQ", "教学档案": "JX",
    "科研档案": "KY", "人事档案": "RS", "财务档案": "CW",
    "基建档案": "JJ", "声像档案": "SX",
}

# 各类档案的标题模板
_TITLES = {
    "行政档案": [
        "{year}年{dept}工作总结", "{year}年校长办公会纪要（第{seq}期）",
        "关于{dept}年度考核的通知", "{year}年{dept}工作计划",
        "关于印发《{dept}管理规定》的通知", "关于成立{dept}工作小组的决定",
        "{year}年行政办公会议记录",
    ],
    "党群档案": [
        "关于{name}同志{action}的决定", "{year}年党委常委会会议纪要",
        "关于表彰{year}年度优秀党员的通知", "{dept}年度工作总结",
        "关于{name}等同志职务任免的通知", "关于印发《党建工作要点》的通知",
        "{year}年纪委工作会议纪要",
    ],
    "教学档案": [
        "{year}年{dept}教学计划", "关于修订本科培养方案的通知",
        "{year}年招生录取工作总结", "关于{name}等同学学籍处理的决定",
        "{year}届毕业生就业质量报告", "{year}年教学检查情况通报",
        "关于{dept}组织开展期末考试的通知",
    ],
    "科研档案": [
        "{year}年科研项目立项汇总", "关于申报国家社科基金项目的通知",
        "科研成果{year}年度统计表", "{dept}学术委员会会议纪要",
        "{year}年科研经费分配方案", "关于表彰优秀科研成果的决定",
    ],
    "人事档案": [
        "关于{name}同志退休的通知", "{year}年教职工年度考核结果",
        "关于{name}等同志任职的通知", "{year}年教师招聘工作方案",
        "关于{name}同志调动工作的通知", "关于调整教职工工资标准的通知",
        "{year}年人事统计年报",
    ],
    "财务档案": [
        "{year}年财务预决算报告", "关于{dept}经费使用情况的审计报告",
        "{year}年专项资金使用情况", "关于调整收费标准的通知",
        "{year}年固定资产清查报告", "财务管理制度汇编",
    ],
    "基建档案": [
        "{year}年{dept}项目立项批复", "关于教学楼修缮工程的招标文件",
        "{dept}竣工验收报告", "校园基础设施建设{year}年度计划",
        "关于学生公寓建设项目的请示",
    ],
    "声像档案": [
        "{year}年毕业典礼影像资料", "校庆{year}周年活动照片集",
        "校园建设{year}s历史照片", "{year}年重要外事活动影像",
        "学校{year}年代校园风貌记录",
    ],
}

# 敏感度档位 — 决定 OCR 文本中是否嵌入敏感词
_SENSITIVITY = {
    "clean": [],  # 无敏感
    "mild": ["内部文件"],  # 轻度
    "moderate": ["上级来文", "知识产权", "个人隐私"],  # 中度
    "high": ["国家秘密", "历史敏感", "违法犯罪"],  # 高度
}

_COMMON_NAMES = ["张建国", "李明", "王芳", "刘伟", "陈静", "杨涛", "赵敏", "周强", "吴丽", "孙磊"]


def _generate_seed_archives() -> list[Archive]:
    """生成 60+ 条示例档案，覆盖 8 门类 × 多部门 × 5 年度区间"""
    import random
    rng = random.Random(42)  # 固定种子，每次生成一致

    archives = []
    seq_counter: dict[str, int] = {}

    years_pool = list(range(1970, 2026))
    # 确保每年至少有档案
    sampled_years = (
        [1973, 1978, 1982, 1985] +  # 1970s-80s
        [1990, 1992, 1995, 1996, 1998] +  # 1990s
        [2000, 2002, 2005, 2008] +  # 2000s
        [2010, 2012, 2015, 2018] +  # 2010s
        [2020, 2021, 2022, 2023, 2024, 2025]  # 2020s
    )
    # 补充：允许重复，因为每个档案必须有独立年份槽位
    while len(sampled_years) < 80:
        sampled_years.append(rng.choice(years_pool))

    ocr_statuses = ["done"] * 8 + ["done"] * 2 + ["low_quality"]  # 80% done, 20% low_quality

    for cat, depts in _CAT_DEPT.items():
        for dept in depts:
            # 每个部门 3-5 条（确保总量 ≥50）
            count = rng.randint(3, 5)
            for _ in range(count):
                # 优先用预选年份（确保覆盖均匀），耗尽后随机
                if sampled_years:
                    year = sampled_years.pop(0)
                else:
                    year = rng.randint(1970, 2025)
                fonds = _CAT_FONDS.get(cat, "XX")
                key = f"{cat}-{dept}"
                seq_counter[key] = seq_counter.get(key, 0) + 1
                seq = seq_counter[key]
                archive_id = f"{year}-{fonds}-{seq:03d}"

                # 选标题模板
                titles = _TITLES.get(cat, _TITLES["行政档案"])
                tpl = rng.choice(titles)
                title = tpl.format(
                    year=year, dept=dept, seq=seq,
                    name=rng.choice(_COMMON_NAMES),
                    action=rng.choice(["任职", "免职", "表彰", "处分"]),
                )

                # 选敏感度 — 约 30% 含敏感，70% 正常
                sensitivity = rng.choices(
                    ["clean", "clean", "clean", "mild", "moderate", "moderate", "high"],
                    k=1
                )[0]

                ocr_text = _generate_ocr_text(cat, dept, year, title, sensitivity, rng)
                ocr_status = rng.choice(ocr_statuses)
                confidence = round(rng.uniform(0.82, 0.99), 2)

                # 开放状态分布
                open_status = rng.choices(
                    ["未审核"] * 5 + ["已开放"] * 2 + ["部分开放"] * 2 + ["不开放"],
                    k=1
                )[0]

                archives.append(Archive(
                    archive_id=archive_id, title=title,
                    year=year, category=cat, department=dept,
                    fonds_id=fonds,
                    retention_period=rng.choice(["永久", "长期", "短期"]),
                    security_level=rng.choice(["内部", "普通"]),
                    level="file",
                    open_status=open_status,
                    ocr_status=ocr_status,
                    ocr_confidence=confidence,
                    ocr_text=ocr_text,
                    file_count=rng.randint(1, 8),
                    ocr_engine="mock" if ocr_status == "done" else "mock",
                    ocr_model_version="mock-v1",
                    ocr_duration_ms=rng.randint(200, 2000),
                ))

    return archives


def _generate_ocr_text(cat: str, dept: str, year: int, title: str, sensitivity: str, rng) -> str:
    """根据敏感度档位生成模拟 OCR 文本"""
    import random as _random

    base = f"中南财经政法大学文件\n\n{title}\n\n"
    base += f"归档年度：{year}年\n门类：{cat}\n归口单位：{dept}\n\n"

    # 正文段落
    if sensitivity == "clean":
        paras = [
            f"经学校研究决定，现将{year}年度相关工作安排通知如下。",
            f"各部门应严格按照学校规章制度执行，确保各项工作有序推进。",
            f"本年度重点任务包括：学科建设、人才培养、师资队伍建设等方面。",
            f"请各单位认真组织学习，结合实际情况贯彻落实。",
        ]
    elif sensitivity == "mild":
        paras = [
            f"根据学校内部管理规定，现将有关事项通知如下。",
            f"本文件为内部文件，请各部门在规定范围内传达。",
            f"相关工作安排已经校长办公会审议通过，现予以印发。",
            f"请各单位按照要求落实，并将执行情况及时反馈。",
        ]
    elif sensitivity == "moderate":
        paras = [
            f"根据国务院[{year}]教字XX号文件精神，结合我校实际，制定本方案。",
            f"涉及教职工个人隐私信息（身份证号420106{year%100}0101XXXX）的请按保密规定处理。",
            f"本通知涉及知识产权相关内容，未经授权不得对外公开。",
            f"请各单位高度重视，严格管理，确保工作质量。",
        ]
    else:  # high
        paras = [
            f"本文件为机密文件，涉及国家秘密事项，请严格控制知悉范围。",
            f"相关内容可能与特定历史时期事件有关，需结合上下文谨慎研判。",
            f"文件中提到的案件正在调查审理中，尚未得出最终结论。",
            f"依据《中华人民共和国保守国家秘密法》，未经批准不得公开或传播。",
        ]

    base += "\n".join(paras)
    base += f"\n\n{dept}\n{year}年{rng.randint(1,12)}月{rng.randint(1,28)}日"

    return base[:800]  # 限制 800 字


def _generate_seed_reviews() -> list[ReviewRecord]:
    """为部分档案生成预审记录"""
    import random
    rng = random.Random(42)

    # 只给大约 1/3 的档案生成预审记录
    review_ids = [
        "1973-DQ-001", "1982-JX-001", "1990-XZ-001", "1995-CW-001",
        "1996-DQ-002", "1998-RS-001", "2000-JX-002", "2002-KY-001",
        "2005-XZ-002", "2008-RS-002", "2010-CW-001", "2012-DQ-001",
        "2015-JX-001", "2018-XZ-001", "2020-KY-001", "2021-CW-002",
        "2022-RS-001", "2023-JX-001", "2024-DQ-001", "2025-XZ-001",
    ]

    suggestions_pool = [
        ("建议开放", 8, 20, "低"),
        ("建议部分开放（脱敏后）", 25, 45, "中"),
        ("建议延期开放", 50, 70, "中"),
        ("建议不开放", 75, 95, "高"),
    ]

    reviews = []
    for aid in review_ids:
        sug, lo, hi, level = rng.choice(suggestions_pool)
        score = rng.randint(lo, hi)
        reviews.append(ReviewRecord(
            archive_id=aid,
            risk_score=score, risk_level=level,
            sensitive_items=[],
            suggestion=sug,
            reason=f"AI 模拟审核：档案经规则引擎+LLM 双引擎融合评估，风险评分 {score} 分。",
            confidence=round(rng.uniform(0.75, 0.98), 2),
            model_name="deepseek-32b-lora-v1",
            processing_time_ms=rng.randint(500, 2000),
        ))

    return reviews


def _generate_seed_logs() -> list[OperationLog]:
    """生成多样化的操作日志"""
    from datetime import timedelta
    import random
    rng = random.Random(42)
    import hashlib

    user_ops = [
        ("admin", "系统管理员"),
        ("reviewer1", "王建国"),
        ("reviewer2", "赵静"),
        ("archivist", "陈小红"),
    ]

    op_templates = [
        ("login", "auth", "用户登录", "success"),
        ("search", "search", "关键词检索: 招生", "success"),
        ("search", "search", "高级检索: 年度1996 门类行政档案", "success"),
        ("view", "search", "查看档案详情: 1996-XZ-001", "success"),
        ("download", "search", "下载档案原文: 1995-DQ-012", "success"),
        ("review", "review", "AI预审: 2000-RS-015", "success"),
        ("review", "review", "批量预审任务提交", "success"),
        ("admin", "user", "创建用户: reviewer3", "success"),
        ("login", "auth", "用户登录", "failure"),
        ("search", "search", "语义检索: 近三年教学改革方面的档案", "success"),
        ("view", "search", "查看知识图谱: 1996-XZ-001", "success"),
        ("ocr", "ocr", "创建OCR任务: 2025年度行政档案", "success"),
        ("sync", "sync", "文件增量同步完成", "success"),
        ("admin", "user", "修改用户权限", "success"),
        ("logout", "auth", "用户登出", "success"),
    ]

    logs = []
    now = datetime.utcnow()
    prev_hash = "0" * 64

    for i in range(60):
        uname, name = rng.choice(user_ops)
        op_type, module, desc_tpl, result = rng.choice(op_templates)
        days_ago = rng.randint(0, 30)
        hours_ago = rng.randint(0, 23)
        ts = now - timedelta(days=days_ago, hours=hours_ago)

        desc = desc_tpl
        if op_type == "search" and result == "success":
            keywords = ["招生", "教学", "财务", "人事", "基建", "科研", "档案", "管理"]
            desc = f"关键词检索: {rng.choice(keywords)} {rng.randint(1970,2025)}"

        # 从描述中提取操作对象标识（如档案编号），补齐审计七要素
        import re as _re
        _m = _re.search(r'\d{4}-[A-Z]{2,3}-\d{3}', desc)
        target_id = _m.group(0) if _m else ""

        content = f"{uname}|{op_type}|{module}|{desc}|{target_id}|{result}"
        chain_hash = hashlib.sha256(f"{prev_hash}{content}".encode()).hexdigest()

        logs.append(OperationLog(
            user_id=1, username=uname,
            operation_type=op_type, module=module,
            description=desc,
            target_id=target_id,
            ip_address=f"192.168.1.{rng.randint(10,99)}",
            result=result,
            chain_hash=chain_hash,
            created_at=ts,
        ))
        prev_hash = chain_hash

    return logs


def _ensure_test_user(db, username: str, name: str, dept: str, role: str):
    """确保测试用户存在，不存在则创建"""
    existing = db.query(User).filter(User.username == username).first()
    if not existing:
        db.add(User(
            username=username, name=name, department=dept,
            password_hash=hash_password("Test123456!"), role=role, is_active=True,
        ))
        db.commit()


def _seed_mock_files():
    """生成模拟档案 TIFF 文件供下载/预览测试"""
    import os

    sync_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "sync_data",
    )

    mock_files = {
        "1996-XZ-001": "1996/行政档案",
        "1995-DQ-012": "1995/党群档案",
        "2000-RS-015": "2000/人事档案",
    }

    try:
        from PIL import Image, ImageDraw, ImageFont

        for archive_id, subdir in mock_files.items():
            target_dir = os.path.join(sync_dir, subdir)
            os.makedirs(target_dir, exist_ok=True)
            filepath = os.path.join(target_dir, f"{archive_id}.tiff")

            if os.path.exists(filepath):
                continue  # 已存在，跳过

            # 生成模拟文档图像
            img = Image.new("RGB", (800, 600), (255, 255, 248))
            draw = ImageDraw.Draw(img)

            font = None
            for fp in [
                "C:\\Windows\\Fonts\\simsun.ttc",
                "C:\\Windows\\Fonts\\simhei.ttf",
                "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            ]:
                if os.path.exists(fp):
                    try: font = ImageFont.truetype(fp, 18); break
                    except: pass

            lines = [
                "中南财经政法大学档案",
                f"档案编号: {archive_id}",
                "",
                "（此为系统自动生成的模拟档案文件，",
                "用于测试原文下载和在线预览功能。）",
            ]
            y = 40
            for line in lines:
                draw.text((40, y), line, fill=(30, 30, 30), font=font)
                y += 36

            img.save(filepath, "TIFF")
            print(f"  📄 模拟文件: {filepath}")

    except ImportError:
        # Pillow 不可用，创建空标记文件
        for archive_id, subdir in mock_files.items():
            target_dir = os.path.join(sync_dir, subdir)
            os.makedirs(target_dir, exist_ok=True)
            filepath = os.path.join(target_dir, f"{archive_id}.tiff")
            if not os.path.exists(filepath):
                with open(filepath, "w") as f:
                    f.write("mock")
                print(f"  📄 占位文件: {filepath}")
