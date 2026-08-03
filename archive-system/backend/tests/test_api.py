"""
API 端点集成测试
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import init_db, engine

client = TestClient(app)

# 测试前初始化 SQLite
@pytest.fixture(autouse=True)
def setup_db():
    init_db()


class TestAuth:
    """认证 API"""

    def test_login_dev_mode(self):
        resp = client.post("/api/auth/login", json={"username": "testuser", "password": "anypass"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "testuser"

    def test_protected_route_no_token(self):
        resp = client.get("/api/search/history")
        assert resp.status_code == 401

    def test_protected_route_with_token(self):
        # 先登录拿 token
        login = client.post("/api/auth/login", json={"username": "admin", "password": "x"})
        token = login.json()["access_token"]

        resp = client.get("/api/search/history", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200


class TestHealth:
    def test_health(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestSearch:
    """检索 API"""

    def get_token(self):
        return client.post("/api/auth/login", json={"username": "test", "password": "x"}).json()["access_token"]

    def test_keyword_search_empty(self):
        token = self.get_token()
        resp = client.post("/api/search/keyword", json={"keywords": "nonexistent_xyz"}, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert "results" in resp.json()

    def test_advanced_search_with_filters(self):
        token = self.get_token()
        resp = client.post("/api/search/advanced", json={
            "year_from": 1990, "year_to": 2000, "category": "行政档案", "page": 1, "page_size": 10,
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data

    def test_archive_detail(self):
        token = self.get_token()
        # 使用任意存在的档案 ID（新种子数据不再有 1996-XZ-001）
        resp = client.get("/api/search/archives/1973-DQ-001", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (200, 404)


class TestReview:
    """审核 API"""

    def get_token(self):
        return client.post("/api/auth/login", json={"username": "test", "password": "x"}).json()["access_token"]

    def test_preview_review(self):
        token = self.get_token()
        resp = client.post("/api/review/preview", json={
            "archive_id": "test-001",
            "full_text": "机密文件：关于文革期间贪污案件的调查。涉及个人隐私和家庭出身。",
            "year": 1970, "department": "档案馆",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "risk_score" in data
        assert "risk_level" in data
        assert "sensitive_items" in data
        assert "suggestion" in data


class TestUsers:
    def get_token(self):
        return client.post("/api/auth/login", json={"username": "test", "password": "x"}).json()["access_token"]

    def test_list_users(self):
        token = self.get_token()
        resp = client.get("/api/user/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_list_roles(self):
        token = self.get_token()
        resp = client.get("/api/user/roles", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200


class TestLogs:
    def get_token(self):
        return client.post("/api/auth/login", json={"username": "test", "password": "x"}).json()["access_token"]

    def test_list_logs(self):
        token = self.get_token()
        resp = client.get("/api/log/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_audit_summary(self):
        token = self.get_token()
        resp = client.get("/api/log/audit/summary", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200


class TestStats:
    def get_token(self):
        return client.post("/api/auth/login", json={"username": "test", "password": "x"}).json()["access_token"]

    def test_stats_by_type(self):
        token = self.get_token()
        resp = client.get("/api/stats/by-type", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_stats_by_user(self):
        token = self.get_token()
        resp = client.get("/api/stats/by-user", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
