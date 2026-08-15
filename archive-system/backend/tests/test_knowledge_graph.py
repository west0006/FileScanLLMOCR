"""
实体抽取 + 知识图谱测试
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.services.entity_extractor import (
    extract_entities, extract_entity_summary, find_shared_entities,
)


class TestEntityExtractor:
    """实体抽取引擎"""

    def test_empty_text(self):
        assert extract_entities("") == []
        assert extract_entities(None) == []

    def test_person_extraction(self):
        text = "经研究决定：任命张某某同志为会计系党总支副书记。"
        entities = extract_entities(text)
        persons = [e for e in entities if e["type"] == "PERSON"]
        assert len(persons) >= 1
        assert any("张" in p["name"] for p in persons)

    def test_org_extraction(self):
        text = "中南财经大学人事处关于教职工考核的通知。抄送：教务处、财务处。"
        entities = extract_entities(text)
        orgs = [e for e in entities if e["type"] == "ORG"]
        assert len(orgs) >= 2

    def test_date_extraction(self):
        text = "一九九六年招生工作于1996年3月开始，至1996.09.01完成。2000年1月5日总结。"
        entities = extract_entities(text)
        dates = [e for e in entities if e["type"] == "DATE"]
        assert len(dates) >= 3

    def test_doc_id_extraction(self):
        text = "根据校党字[1995]第12号文件和国务院[1973]教字XX号文件精神。"
        entities = extract_entities(text)
        doc_ids = [e for e in entities if e["type"] == "DOC_ID"]
        assert len(doc_ids) >= 1

    def test_event_extraction(self):
        text = "开展招生工作，组织入学考试。对违纪人员进行处分。"
        entities = extract_entities(text)
        events = [e for e in entities if e["type"] == "EVENT"]
        assert len(events) >= 2

    def test_position_correct(self):
        text = "任命张某某为处长"
        entities = extract_entities(text)
        for e in entities:
            name = e["name"]
            assert text[e["start"]:e["end"]] == name

    def test_extract_entity_summary(self):
        entities = [
            {"type": "PERSON", "name": "张三", "start": 0, "end": 2},
            {"type": "PERSON", "name": "李四", "start": 10, "end": 12},
            {"type": "ORG", "name": "人事处", "start": 20, "end": 23},
        ]
        summary = extract_entity_summary(entities)
        assert summary["PERSON"] == ["张三", "李四"]
        assert summary["ORG"] == ["人事处"]

    def test_find_shared_entities(self):
        a = [
            {"type": "PERSON", "name": "张三", "start": 0, "end": 2},
            {"type": "ORG", "name": "人事处", "start": 10, "end": 13},
        ]
        b = [
            {"type": "PERSON", "name": "张三", "start": 5, "end": 7},
            {"type": "ORG", "name": "财务处", "start": 20, "end": 23},
        ]
        shared = find_shared_entities(a, b)
        assert len(shared) == 1
        assert shared[0]["name"] == "张三"

    def test_real_ocr_text(self):
        """用种子数据真实文本测试"""
        text = (
            "关于张某某同志任职的通知\n\n"
            "经校党委常委会研究决定：任命张某某同志为会计系党总支副书记。\n"
            "该同志家庭出身工人，政治面貌中共党员。"
            "抄送：组织部、人事处。1995年3月15日。"
        )
        entities = extract_entities(text)
        types = {e["type"] for e in entities}
        assert "PERSON" in types
        assert "ORG" in types
        assert "DATE" in types
        assert "EVENT" in types


class TestKnowledgeGraphEndpoint:
    """知识图谱 API"""

    def get_token(self):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.database import init_db

        client = TestClient(app)
        init_db()
        try:
            from app.core.seed import seed; seed()
        except: pass
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "x"})
        return resp.json()["access_token"], client

    def test_knowledge_graph_endpoint(self):
        """GET /search/archives/{id}/knowledge-graph"""
        token, client = self.get_token()
        # 从种子数据获取第一个有 OCR 文本的档案 ID
        from app.core.database import SessionLocal
        from app.models.models import Archive
        db = SessionLocal()
        try:
            first = db.query(Archive).filter(Archive.ocr_text.isnot(None), Archive.ocr_text != "").first()
            aid = first.archive_id if first else "1973-DQ-001"
        finally:
            db.close()
        resp = client.get(
            f"/api/search/archives/{aid}/knowledge-graph",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data
        assert "center_summary" in data

    def test_knowledge_graph_not_found(self):
        """不存在的档案返回空"""
        token, client = self.get_token()
        resp = client.get(
            "/api/search/archives/NONEXIST/knowledge-graph",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["nodes"] == []
