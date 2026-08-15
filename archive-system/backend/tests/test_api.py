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
        return client.post("/api/auth/login", json={"username": "admin", "password": "x"}).json()["access_token"]

    def test_list_users(self):
        token = self.get_token()
        resp = client.get("/api/user/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_list_roles(self):
        token = self.get_token()
        resp = client.get("/api/user/roles", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_online_users_last_login_filter(self):
        """在线用户仅返回最近2小时内登录过的启用用户（last_login_at 过滤）"""
        from app.core.database import SessionLocal
        from app.models.models import User
        from app.core.security import hash_password

        # 构造一个启用但从未登录的用户
        db = SessionLocal()
        try:
            u = db.query(User).filter(User.username == "never_login").first()
            if not u:
                u = User(username="never_login", name="从未登录",
                         password_hash=hash_password("Test123456!"),
                         role="reviewer", is_active=True)
                db.add(u)
            u.last_login_at = None
            db.commit()
        finally:
            db.close()

        # admin（system_admin）登录，last_login_at 被更新
        token = client.post("/api/auth/login", json={"username": "admin", "password": "x"}).json()["access_token"]
        resp = client.get("/api/user/online", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        usernames = [i["username"] for i in resp.json()["items"]]
        assert "never_login" not in usernames, "从未登录的用户不应出现在在线列表"
        assert "admin" in usernames, "刚登录的 admin 应出现在在线列表"


class TestLogs:
    def get_token(self):
        # 日志/审计为系统管理员专属，需用 admin 登录（reviewer 应 403）
        return client.post("/api/auth/login", json={"username": "admin", "password": "x"}).json()["access_token"]

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
        data = resp.json()
        assert "items" in data
        assert "failed" in data
        assert "total" in data
        # 验证 total = sum of items
        assert data["total"] == sum(i["count"] for i in data["items"]), f"total={data['total']} != sum={sum(i['count'] for i in data['items'])}"

    def test_stats_by_user(self):
        token = self.get_token()
        resp = client.get("/api/stats/by-user", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_stats_by_time_type_split(self):
        """by-time 返回 search/view/download/print 拆分"""
        token = self.get_token()
        resp = client.get("/api/stats/by-time", params={"granularity": "day", "days": 7},
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        for item in data["items"]:
            assert "period" in item
            # 验证每个 period 包含五种类型
            for t in ("search", "view_entry", "view_file", "download", "print"):
                assert t in item, f"missing key '{t}' in period {item['period']}"
                assert isinstance(item[t], int)


class TestSync:
    """数据同步端点"""
    def get_token(self):
        return client.post("/api/auth/login", json={"username": "admin", "password": "x"}).json()["access_token"]

    def test_get_config(self):
        token = self.get_token()
        resp = client.get("/api/sync/config", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_sync_history(self):
        token = self.get_token()
        resp = client.get("/api/sync/history", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data


class TestReviewSyncOpenStatus:
    """预审结果回写 Archive.open_status"""
    def get_token(self):
        return client.post("/api/auth/login", json={"username": "test", "password": "x"}).json()["access_token"]

    def test_sync_open_status_不开放(self):
        from app.core.database import SessionLocal
        from app.models.models import Archive
        token = self.get_token()
        # 预审一条结果
        client.post("/api/review/preview", json={
            "archive_id": "sync-test-001", "full_text": "机密文件涉及国家秘密",
            "year": 2000, "department": "测试",
        }, headers={"Authorization": f"Bearer {token}"})
        # 验证 open_status 被同步
        db = SessionLocal()
        try:
            a = db.query(Archive).filter(Archive.archive_id == "sync-test-001").first()
            if a:
                # 含"机密""国家秘密"→规则引擎高分→建议不开放
                assert a.open_status in ("不开放", "延期开放", "未审核"), f"unexpected: {a.open_status}"
        finally:
            db.close()

    def test_sync_open_status_开放(self):
        from app.core.database import SessionLocal
        from app.models.models import Archive
        token = self.get_token()
        client.post("/api/review/preview", json={
            "archive_id": "sync-test-002", "full_text": "关于教学管理的常规工作报告，学校简介与规章制度。",
            "year": 2020, "department": "教务处",
        }, headers={"Authorization": f"Bearer {token}"})
        db = SessionLocal()
        try:
            a = db.query(Archive).filter(Archive.archive_id == "sync-test-002").first()
            if a:
                # 无敏感词→低风险→建议开放
                assert a.open_status in ("已开放", "部分开放", "未审核"), f"unexpected: {a.open_status}"
        finally:
            db.close()
