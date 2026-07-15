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
from app.models.models import User, Role, Archive, ReviewRecord, OperationLog


def seed():
    """插入种子数据，已存在则跳过"""
    db = SessionLocal()
    try:
        # ---- 角色 ----
        if db.query(Role).count() == 0:
            db.add_all([
                Role(name="system_admin", description="系统管理员",
                     permissions={"all": True}, data_scope={"all": True}),
                Role(name="archive_admin", description="档案管理员",
                     permissions={"search": True, "ocr": True, "sync": True, "stats": True},
                     data_scope={"all": True}),
                Role(name="reviewer", description="审核员",
                     permissions={"search": True, "review": True},
                     data_scope={"departments": []}),
            ])

        # ---- 默认管理员 ----
        if db.query(User).filter(User.username == "admin").count() == 0:
            db.add(User(
                username="admin", name="系统管理员", department="档案馆",
                password_hash=hash_password("Admin@123456"),
                role="system_admin", is_active=True,
            ))

        # ---- 示例档案 ----
        if db.query(Archive).count() == 0:
            archives = [
                Archive(archive_id="1996-XZ-001", title="一九九六年招生工作总结",
                        year=1996, category="行政档案", department="学校办公室",
                        fonds_id="XZ", retention_period="永久", security_level="内部",
                        ocr_status="done", ocr_confidence=0.96, file_count=3,
                        ocr_text="关于一九九六年招生工作的总结报告\n\n本年度招生工作在校党委的领导下顺利完成。共录取本科生1200人，研究生300人。具体工作包括：制定招生计划、组织考试、录取审核等环节。\n\n存在问题：部分专业报考人数不足，需进一步优化专业设置。"),
                Archive(archive_id="1995-DQ-012", title="关于张某某同志任职的通知",
                        year=1995, category="党群档案", department="组织部",
                        fonds_id="DQ", retention_period="永久", security_level="内部",
                        ocr_status="done", ocr_confidence=0.93, file_count=1,
                        ocr_text="中南财经大学文件\n校党字[1995]第12号\n\n关于张某某同志任职的通知\n\n各党总支、直属党支部：\n经校党委常委会研究决定：任命张某某同志为会计系党总支副书记。\n\n该同志家庭出身工人，政治面貌中共党员…"),  # 含个人隐私
                Archive(archive_id="1973-JX-008", title="一九七三年教学计划安排",
                        year=1973, category="教学档案", department="教务处",
                        fonds_id="JX", retention_period="长期", security_level="内部",
                        ocr_status="done", ocr_confidence=0.88, file_count=5,
                        ocr_text="一九七三年教学计划安排\n\n根据国务院[1973]教字XX号文件精神，结合我校实际情况，制定本年度教学计划。\n\n一、政治理论课安排\n认真学习中央文件精神，深入开展批林批孔运动…"),  # 含上级来文+历史敏感
                Archive(archive_id="1988-CW-003", title="一九八八年财务预决算报告",
                        year=1988, category="财务档案", department="财务处",
                        fonds_id="CW", retention_period="永久", security_level="内部",
                        ocr_status="done", ocr_confidence=0.97, file_count=2,
                        ocr_text="中南财经大学一九八八年财务预决算报告\n\n一、年度预算执行情况\n总收入XXX万元，总支出XXX万元，结余XXX万元。\n二、重点支出项目\n1.教学楼建设XXX万元\n2.科研经费XXX万元"),
                Archive(archive_id="2000-RS-015", title="关于李某等同志退休的通知",
                        year=2000, category="人事档案", department="人事处",
                        fonds_id="RS", retention_period="永久", security_level="内部",
                        ocr_status="done", ocr_confidence=0.95, file_count=1,
                        ocr_text="关于李某等同志退休的通知\n\n根据国家有关规定，李某（身份证号42010619400101XXXX）、王某等同志已达到退休年龄，经研究决定…"),  # 含身份证号
            ]
            db.add_all(archives)
            db.commit()

        # ---- 示例预审记录 ----
        if db.query(ReviewRecord).count() == 0:
            db.add_all([
                ReviewRecord(archive_id="1996-XZ-001", risk_score=8, risk_level="低",
                             sensitive_items=[], suggestion="建议开放",
                             reason="常规招生工作总结，未涉及敏感信息。", confidence=0.95,
                             model_name="deepseek-32b-lora-v1", processing_time_ms=1200),
                ReviewRecord(archive_id="1995-DQ-012", risk_score=72, risk_level="高",
                             sensitive_items=[{"type": "个人隐私", "content": "家庭出身工人",
                                              "start_char": 80, "end_char": 86}],
                             suggestion="建议不予开放",
                             reason="涉及个人家庭出身等隐私信息。", confidence=0.91,
                             model_name="deepseek-32b-lora-v1", processing_time_ms=980),
                ReviewRecord(archive_id="1973-JX-008", risk_score=85, risk_level="高",
                             sensitive_items=[
                                 {"type": "上级来文", "content": "国务院[1973]教字XX号文件"},
                                 {"type": "历史敏感", "content": "批林批孔运动"},
                             ],
                             suggestion="建议延期开放",
                             reason="引用上级来文且包含特定历史时期内容。", confidence=0.88,
                             model_name="deepseek-32b-lora-v1", processing_time_ms=1450),
                ReviewRecord(archive_id="1988-CW-003", risk_score=12, risk_level="低",
                             sensitive_items=[], suggestion="建议开放",
                             reason="常规财务报告，不涉及敏感信息。", confidence=0.97,
                             model_name="deepseek-32b-lora-v1", processing_time_ms=870),
                ReviewRecord(archive_id="2000-RS-015", risk_score=68, risk_level="高",
                             sensitive_items=[{"type": "个人隐私", "content": "身份证号420106..."}],
                             suggestion="建议部分开放",
                             reason="包含身份证号，需遮盖后开放。", confidence=0.93,
                             model_name="deepseek-32b-lora-v1", processing_time_ms=1020),
            ])

        # ---- 示例操作日志 ----
        if db.query(OperationLog).count() == 0:
            db.add_all([
                OperationLog(user_id=1, username="admin", operation_type="login",
                             module="auth", description="用户登录", result="success"),
                OperationLog(user_id=1, username="admin", operation_type="search",
                             module="search", description="检索: 招生 1996", result="success"),
                OperationLog(user_id=1, username="admin", operation_type="review",
                             module="review", description="预审 1995-DQ-012", result="success"),
            ])

        db.commit()
        print("✅ 种子数据已插入")
        print("   默认管理员: admin / Admin@123456")
        print(f"   示例档案: {db.query(Archive).count()} 条")
        print(f"   预审记录: {db.query(ReviewRecord).count()} 条")

    except Exception as e:
        db.rollback()
        print(f"⚠️ 种子数据插入失败: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
