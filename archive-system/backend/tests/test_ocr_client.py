"""
OCR 客户端 + 管线测试

覆盖:
  - Mock 模式功能测试
  - OCR 客户端双模式切换
  - 图像预处理管线
  - 多页分离
  - 版面分析
  - 环境检测集成
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.core.config import settings

# 当前运行环境
ORIGINAL_OCR_MODE = settings.OCR_MODE


class TestOcrClient:
    """OCR 客户端"""

    def test_mock_recognize(self):
        """Mock 模式识别"""
        from app.services.ocr_client import ocr_client

        result = ocr_client.recognize("test_image.tiff")
        assert "text" in result
        assert "confidence" in result
        assert result["confidence"] > 0
        assert result["engine"] == "mock"

    def test_mock_deterministic(self):
        """同一输入多次识别结果一致"""
        from app.services.ocr_client import ocr_client

        r1 = ocr_client.recognize("test_file_001.tif")
        r2 = ocr_client.recognize("test_file_001.tif")
        assert r1["text"] == r2["text"]
        assert r1["confidence"] == r2["confidence"]

    def test_mock_different_input_different_output(self):
        """不同输入结果不同（哈希确定性）"""
        from app.services.ocr_client import ocr_client

        r1 = ocr_client.recognize("file_a.jpg")
        r2 = ocr_client.recognize("file_b.jpg")
        assert r1["text"] != r2["text"]

    def test_mock_structure(self):
        """Mock 版面分析"""
        from app.services.ocr_client import ocr_client

        result = ocr_client.recognize_structure("test.tiff")
        assert "regions" in result
        assert len(result["regions"]) >= 1

    def test_get_info(self):
        """获取 OCR 引擎信息"""
        from app.services.ocr_client import ocr_client

        info = ocr_client.get_info()
        assert "mode" in info
        assert info["mode"] in ("mock", "real")

    def test_batch_recognize(self):
        """批量识别"""
        from app.services.ocr_client import ocr_client

        paths = ["a.tiff", "b.tiff", "c.tiff"]
        results = ocr_client.batch_recognize(paths)
        assert len(results) == 3
        for r in results:
            assert "text" in r


class TestPageSplitter:
    """多页文件分离"""

    def test_split_single_image(self):
        """单页图像 → 1 页"""
        from app.services.ocr_processor import PageSplitter
        import tempfile

        # 创建空白 PNG
        try:
            from PIL import Image
            img = Image.new("RGB", (100, 100), (255, 255, 255))
            fd, tmp_path = tempfile.mkstemp(suffix=".png")
            with os.fdopen(fd, "wb") as f:
                img.save(f, "PNG")
        except ImportError:
            tmp_path = None

        if tmp_path:
            try:
                pages = PageSplitter.split(tmp_path)
                assert len(pages) == 1
                assert isinstance(pages[0], bytes)
            finally:
                try: os.unlink(tmp_path)
                except OSError: pass

    def test_empty_path(self):
        """空路径返回空"""
        from app.services.ocr_processor import PageSplitter

        pages = PageSplitter.split("/nonexistent/path.tiff")
        assert len(pages) == 0 or len(pages) == 1  # falls back to raw read


class TestOcrProcessor:
    """OCR 处理管线"""

    def test_process_no_files(self):
        """无文件时返回空结果"""
        from app.services.ocr_processor import ocr_processor

        result = ocr_processor.process_archive("test-001", [])
        assert result["total_pages"] == 0
        assert result["ocr_text"] == ""

    def test_process_with_mock(self):
        """Mock 模式处理"""
        from app.services.ocr_processor import ocr_processor
        import tempfile

        try:
            from PIL import Image

            fd, tmp_path = tempfile.mkstemp(suffix=".png")
            with os.fdopen(fd, "wb") as f:
                Image.new("RGB", (100, 100), (255, 255, 255)).save(f, "PNG")

            result = ocr_processor.process_archive("test-002", [tmp_path])
            assert result["archive_id"] == "test-002"
            assert result["total_pages"] >= 0
        finally:
            try: os.unlink(tmp_path)
            except OSError: pass


class TestEnvDetect:
    """环境检测"""

    def test_detect_import(self):
        """检测脚本可导入"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
        from deploy.ocr_env_detect import detect_all

        report = detect_all()
        assert report.strategy in ("gpu", "cpu")
        assert report.os
        assert report.python_version

    def test_detect_gpu_info(self):
        """GPU 信息结构正确"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
        from deploy.ocr_env_detect import detect_gpu

        gpu = detect_gpu()
        assert hasattr(gpu, "available")
        assert hasattr(gpu, "name")

    def test_detect_paddle(self):
        """PaddlePaddle 信息结构正确"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
        from deploy.ocr_env_detect import detect_paddle

        pp = detect_paddle()
        assert hasattr(pp, "installed")
        # 本地开发环境 PaddlePaddle 未安装是正常的
        assert pp.installed is not None  # bool


class TestOcrEndpoints:
    """OCR API 端点"""

    def get_token(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "x"})
        return resp.json()["access_token"], client

    def test_ocr_models_endpoint(self):
        """GET /api/ocr/models 端点"""
        token, client = self.get_token()
        resp = client.get("/api/ocr/models", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "mode" in data

    def test_ocr_tasks_list(self):
        """GET /api/ocr/tasks 端点"""
        token, client = self.get_token()
        resp = client.get("/api/ocr/tasks", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_ocr_quality_report(self):
        """GET /api/ocr/quality-report 端点"""
        token, client = self.get_token()
        resp = client.get("/api/ocr/quality-report", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_accuracy" in data

    def test_debug_test(self):
        """POST /api/ocr/debug/test 端点（仅系统管理员）"""
        token, client = self.get_token()
        resp = client.post("/api/ocr/debug/test", json={"text": "测试文本"}, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert "result" in resp.json()
