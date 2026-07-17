"""LLM 客户端 — mock 模式返回模拟结果，real 模式调用 LLaMA-Factory API"""

import os
import json
import random
import hashlib
from typing import Optional

import requests

from app.core.config import settings

# Prompt 模板
SYSTEM_REVIEW = """你是中南财经政法大学档案馆的档案开放审核专家。审核档案全文，判断是否可以向社会开放。

【不予开放情形】
1.国家秘密(绝密/机密/秘密/国防/军事)→不予开放
2.未结论重大事项(待调查/审理中/未公开)→不予开放
3.学校内部事项(内部文件/内部会议/不对外公开)→不予开放
4.知识产权(专利/版权/商标)→不予开放
5.个人隐私(身份证号/家庭出身/政治面貌/成绩/处分/检讨)→不予或部分开放
6.上级来文/外收文(国务院/教育部/省委)→不予开放
7.捐献寄存未授权→不予开放

【可开放内容（降低风险评分）】
- 学校简介/领导班子/学科专业/规章制度/招生简章/就业质量
- 资产管理制度/捐赠情况
- 干部任免/人员招聘（不含个人隐私细节）
- 应急预案/整改情况/教学质量报告

输出 JSON: {"risk_score":0-100,"risk_level":"低|中|高","sensitive_items":[{"type":"...","content":"...","start_char":0,"end_char":0}],"suggestion":"建议开放|建议部分开放|建议延期开放|建议不予开放","reason":"...","confidence":0.0-1.0}
评分：0-20低/21-60中/61-100高。宁可假阳性不可假阴性。不确定时标注低置信度。"""

# LLaMA-Factory API 地址
LLAMAFACTORY_URL = getattr(settings, 'LLAMAFACTORY_URL', 'http://10.11.13.100:7860')


# 模拟敏感词列表（脱敏版，仅用于开发测试）
_MOCK_SENSITIVE_WORDS = [
    "个人隐私", "身份证号", "家庭出身", "健康信息",
    "上级来文", "外收文", "内部文件", "会议纪要(密)",
    "知识产权", "专利", "版权",
]

_MOCK_RISK_REASONS = {
    "low": "该档案为常规行政管理文件，不涉及国家秘密、商业秘密或个人隐私，建议开放。",
    "medium": "档案包含部分内部管理信息，建议人工复核后决定。",
    "high": "档案涉及上级来文引用及个人敏感信息，建议延期开放或不予开放。",
}


class LLMClient:
    """
    LLM 审核客户端

    模式切换：
    - LLM_MODE=mock → 本地开发，返回模拟结果（默认）
    - LLM_MODE=real → 调用 LLaMA-Factory API（需在学校内网）

    ⚠️ real 模式需要向日葵远程学校主机 → 访问 10.11.13.100:7860
       本地开发机器无法直连，请保持 mock 模式
    """

    def __init__(self):
        self.mode = settings.LLM_MODE
        self._reachable: bool | None = None

    def _check_reachable(self) -> bool:
        """检测 LLaMA-Factory 是否可达"""
        if self._reachable is not None:
            return self._reachable
        try:
            resp = requests.get(f"{LLAMAFACTORY_URL}/", timeout=3)
            self._reachable = resp.status_code == 200
        except Exception:
            self._reachable = False
        return self._reachable

    def review(self, full_text: str, metadata: Optional[dict] = None) -> dict:
        if self.mode == "mock":
            return self._mock_review(full_text, metadata)
        else:
            return self._real_review(full_text, metadata)

    def _mock_review(self, full_text: str, metadata: Optional[dict] = None) -> dict:
        """模拟审核：基于文本内容中的关键词生成假结果"""
        # 用文本哈希生成确定性随机，同一个文本多次调用结果一致
        seed = int(hashlib.md5(full_text.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)

        # 统计命中敏感词（模拟）
        hits = []
        for word in _MOCK_SENSITIVE_WORDS:
            if word in full_text:
                hits.append({
                    "type": word,
                    "content": f"[MOCK] 检测到疑似{word}相关内容",
                    "start_char": full_text.find(word) if word in full_text else -1,
                    "end_char": full_text.find(word) + len(word) if word in full_text else -1,
                })

        # 风险评分
        if not hits:
            risk_score = rng.randint(0, 15)
            risk_level = "低"
            suggestion = "建议开放"
        elif len(hits) <= 2:
            risk_score = rng.randint(20, 55)
            risk_level = "中"
            suggestion = "建议人工重点关注"
        else:
            risk_score = rng.randint(60, 95)
            risk_level = "高"
            suggestion = "建议延期开放或不予开放"

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "sensitive_items": hits,
            "suggestion": suggestion,
            "reason": _MOCK_RISK_REASONS[{"低": "low", "中": "medium", "高": "high"}[risk_level]],
            "confidence": round(rng.uniform(0.75, 0.98), 2),
        }

    def _real_review(self, full_text: str, metadata: Optional[dict] = None) -> dict:
        """真实 LLM 推理 — 调用 LLaMA-Factory API"""
        user_prompt = f"请审核以下档案：\n\n档案编号：{metadata.get('archive_id', '')}\n题名：{metadata.get('title', '')}\n归口单位：{metadata.get('department', '')}\n归档年度：{metadata.get('year', '')}\n\n全文内容：\n{full_text[:3000]}"

        result = self._call_llm(SYSTEM_REVIEW, user_prompt)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {
                "risk_score": 50, "risk_level": "中",
                "sensitive_items": [],
                "suggestion": "建议人工复核",
                "reason": f"LLM 返回非 JSON 格式: {result[:200]}",
                "confidence": 0.5,
            }

    def understand_query(self, query: str) -> dict:
        """语义检索 — query 理解"""
        if self.mode == "mock":
            return self._mock_understand_query(query)
        else:
            return self._real_understand_query(query)

    def _mock_understand_query(self, query: str) -> dict:
        """模拟 query 理解"""
        keywords = query.split()
        entities = []
        time_range = None
        for kw in keywords:
            if kw.isdigit() and len(kw) == 4:
                time_range = [int(kw), int(kw)]
                entities.append({"name": kw, "type": "YEAR"})
        return {
            "intent": "topic_research" if len(keywords) > 2 else "exact_lookup",
            "entities": entities,
            "keywords": keywords,
            "synonyms": [],
            "time_range": time_range,
            "suggest_fields": ["title^3", "full_text"],
        }

    def _real_understand_query(self, query: str) -> dict:
        """真实 query 理解 — 调用 LLaMA-Factory API"""
        system = "你是档案检索意图分析助手。用户输入查询，你输出 JSON: {\"intent\":\"exact_lookup|topic_research|person_lookup|stat_query\",\"entities\":[],\"keywords\":[],\"synonyms\":[],\"time_range\":null,\"suggest_fields\":[\"title^3\",\"full_text\"]}"
        user = f'用户查询："{query}"\n\n仅输出 JSON。'

        result = self._call_llm(system, user)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {
                "intent": "keyword_search", "entities": [], "time_range": None,
                "keywords": query.split(), "synonyms": [],
                "suggest_fields": ["title^3", "full_text"],
            }

    # ==================== 底层 API 调用 ====================

    def _call_llm(self, system: str, user: str, temperature: float = 0.1, max_tokens: int = 1024) -> str:
        """调用 LLaMA-Factory /chat API"""
        try:
            resp = requests.post(
                f"{LLAMAFACTORY_URL}/api/chat",
                json={
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=60,
            )
            if resp.status_code == 200:
                data = resp.json()
                return (
                    data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    or data.get("response", "")
                    or str(data)
                )
            return f"HTTP {resp.status_code}: {resp.text[:300]}"
        except requests.ConnectionError:
            return '{"risk_score":50,"risk_level":"中","suggestion":"建议人工复核","reason":"LLM 服务不可达","confidence":0.3}'
        except Exception as e:
            return f'{{"risk_score":50,"risk_level":"中","suggestion":"建议人工复核","reason":"{str(e)[:80]}","confidence":0.3}}'


# 全局单例
llm_client = LLMClient()
