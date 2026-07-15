"""
审核规则引擎测试
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.services.review_service import scan_sensitive, calculate_risk_score


class TestScanSensitive:
    """敏感词扫描"""

    def test_empty_text(self):
        assert scan_sensitive("") == []

    def test_no_sensitive(self):
        hits = scan_sensitive("关于教学管理的常规工作报告")
        assert len(hits) == 0

    def test_single_sensitive_word(self):
        hits = scan_sensitive("该档案涉及国家秘密事项")
        assert len(hits) >= 1
        assert any(h["type"] == "国家秘密" for h in hits)

    def test_multiple_categories(self):
        text = "该文件为机密档案，涉及文革时期记录，包含贪污案件和个人隐私信息。"
        hits = scan_sensitive(text)
        categories = {h["type"] for h in hits}
        assert "国家秘密" in categories  # 机密
        assert "历史敏感" in categories  # 文革
        assert "违法犯罪" in categories  # 贪污
        assert "个人隐私" in categories  # 个人隐私

    def test_sensitive_position_correct(self):
        text = "关于张三的处分决定"
        hits = scan_sensitive(text)
        for h in hits:
            word = h["word"]
            assert text[h["start_char"]:h["end_char"]] == word

    def test_long_text(self):
        """5000 字长文本扫描性能"""
        import time
        text = "关于教学管理的常规工作报告。" * 250  # ~5000 chars
        text += "机密文件涉及国家秘密。"  # 末尾加敏感词
        t0 = time.time()
        hits = scan_sensitive(text)
        elapsed = time.time() - t0
        assert len(hits) >= 2  # 机密 + 国家秘密
        assert elapsed < 0.2  # 200ms 内完成


class TestCalculateRiskScore:
    """风险评分算法"""

    def test_no_hits(self):
        score, level = calculate_risk_score([])
        assert score == 0.0
        assert level == "低"

    def test_single_hit_low_weight(self):
        hits = [{"type": "知识产权", "word": "专利", "content": "...", "start_char": 0, "end_char": 2}]
        score, level = calculate_risk_score(hits)
        assert score <= 20  # 知识产权权重低

    def test_single_hit_high_weight(self):
        hits = [{"type": "国家秘密", "word": "机密", "content": "...", "start_char": 0, "end_char": 2}]
        score, level = calculate_risk_score(hits)
        assert 10 <= score <= 25  # 国家秘密权重大

    def test_multi_category_bonus(self):
        """多类别触发加成"""
        hits = [
            {"type": "国家秘密"},
            {"type": "历史敏感"},
            {"type": "违法犯罪"},
            {"type": "个人隐私"},
            {"type": "违纪违规"},
        ]
        score, level = calculate_risk_score(hits)
        assert score >= 60  # 5 类应触发多类别加成
        assert level == "高"

    def test_score_capped_at_95(self):
        """评分上限 95"""
        hits = [{"type": "国家秘密"}] * 50
        score, _ = calculate_risk_score(hits)
        assert score <= 95.0
