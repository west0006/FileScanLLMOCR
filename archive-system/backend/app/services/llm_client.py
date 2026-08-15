"""
LLM 客户端 — mock / ollama / LLaMA-Factory 三模式

模式切换 (.env):
  LLM_MODE=mock    → 本地模拟（默认）
  LLM_MODE=ollama  → 本地 Ollama（需先启动: ollama serve）
  LLM_MODE=real    → 学校 LLaMA-Factory API（需向日葵）

Ollama 快速启动:
  # 安装 Ollama: https://ollama.com/download
  ollama pull qwen2.5:3b
  ollama serve
  # .env 设 LLM_MODE=ollama 即可
"""

import json
import logging
import os
import random
import hashlib
from typing import Optional

import requests

from app.core.config import settings

logger = logging.getLogger("llm_client")

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

输出 JSON: {"risk_score":0-100,"risk_level":"低|中|高","sensitive_items":[{"type":"...","content":"...","start_char":0,"end_char":0}],"suggestion":"建议开放|建议部分开放|建议延期开放|建议不开放","reason":"...","confidence":0.0-1.0}
评分：0-20低(建议开放)/21-45中(建议部分开放)/46-70中(建议延期开放)/71-100高(建议不开放)。宁可假阳性不可假阴性。不确定时标注低置信度。"""

SYSTEM_QUERY = "你是档案检索意图分析助手。用户输入查询，你输出 JSON: {\"intent\":\"exact_lookup|topic_research|person_lookup|stat_query\",\"entities\":[],\"keywords\":[],\"synonyms\":[],\"time_range\":null,\"suggest_fields\":[\"title^3\",\"full_text\"]}"

# LLaMA-Factory 地址（可通过 .env 配置）
LLAMAFACTORY_URL = settings.LLAMAFACTORY_URL

_MOCK_REASONS = {
    "low": "该档案为常规行政管理文件，不涉及国家秘密、商业秘密或个人隐私，建议开放。",
    "medium": "档案包含部分内部管理信息，建议人工复核后决定。",
    "high": "档案涉及上级来文引用及个人敏感信息，建议不开放。",
}


class LLMClient:
    """
    LLM 审核客户端
    LLM_MODE=mock   → 确定性模拟（开发调试）
    LLM_MODE=ollama → Ollama 本地模型（推荐，无需网络）
    LLM_MODE=real   → LLaMA-Factory（学校主机）
    """

    def __init__(self):
        self.mode = settings.LLM_MODE

    # ============================================================
    # 审核
    # ============================================================

    def review(self, full_text: str, metadata: Optional[dict] = None) -> dict:
        if self.mode == "ollama":
            return self._ollama_review(full_text, metadata)
        elif self.mode == "real":
            return self._real_review(full_text, metadata)
        else:
            return self._mock_review(full_text, metadata)

    def _mock_review(self, full_text: str, metadata: Optional[dict] = None) -> dict:
        seed = int(hashlib.md5(full_text.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        # 复用规则引擎的敏感词扫描（400+ 词按 9 类组织），
        # 保证 mock 与规则引擎口径一致，消除双引擎词库不一致
        from app.services.review_service import scan_sensitive
        rule_hits = scan_sensitive(full_text)
        hits = [
            {"type": h["type"], "content": f"[MOCK] {h['type']}: {h['word']}",
             "start_char": h["start_char"], "end_char": h["end_char"]}
            for h in rule_hits
        ]
        if not hits:
            risk_score = rng.randint(0, 15); risk_level = "低"; suggestion = "建议开放"
        elif len(hits) <= 1:
            risk_score = rng.randint(20, 40); risk_level = "中"; suggestion = "建议部分开放"
        elif len(hits) <= 3:
            risk_score = rng.randint(45, 65); risk_level = "中"; suggestion = "建议延期开放"
        else:
            risk_score = rng.randint(70, 95); risk_level = "高"; suggestion = "建议不开放"
        return {
            "risk_score": risk_score, "risk_level": risk_level, "sensitive_items": hits,
            "suggestion": suggestion, "confidence": round(rng.uniform(0.75, 0.98), 2),
            "reason": _MOCK_REASONS[{"低":"low","中":"medium","高":"high"}[risk_level]],
        }

    def _ollama_review(self, full_text: str, metadata: Optional[dict] = None) -> dict:
        """调用 Ollama 本地模型审核"""
        user_prompt = f"请审核以下档案：\n\n"
        if metadata:
            user_prompt += f"档案编号：{metadata.get('archive_id','')}\n题名：{metadata.get('title','')}\n归口单位：{metadata.get('department','')}\n归档年度：{metadata.get('year','')}\n\n"
        user_prompt += f"全文内容：\n{full_text[:3000]}"

        return self._call_ollama(SYSTEM_REVIEW, user_prompt, temperature=0.1, max_tokens=1024)

    def _real_review(self, full_text: str, metadata: Optional[dict] = None) -> dict:
        """调用 LLaMA-Factory API"""
        user_prompt = f"请审核以下档案：\n\n档案编号：{metadata.get('archive_id','')}\n题名：{metadata.get('title','')}\n归口单位：{metadata.get('department','')}\n归档年度：{metadata.get('year','')}\n\n全文内容：\n{full_text[:3000]}"
        result = self._call_llamafactory(SYSTEM_REVIEW, user_prompt)
        try: return json.loads(result)
        except json.JSONDecodeError:
            return {"risk_score": 50, "risk_level": "中", "sensitive_items": [],
                    "suggestion": "建议人工复核", "reason": f"LLM 返回非 JSON: {result[:200]}", "confidence": 0.5, "llm_available": False}

    # ============================================================
    # Query 理解（语义检索）
    # ============================================================

    def understand_query(self, query: str) -> dict:
        if self.mode == "ollama":
            return self._ollama_understand_query(query)
        elif self.mode == "real":
            return self._real_understand_query(query)
        else:
            return self._mock_understand_query(query)

    def _mock_understand_query(self, query: str) -> dict:
        keywords = query.split()
        entities = []
        time_range = None
        for kw in keywords:
            if kw.isdigit() and len(kw) == 4:
                time_range = [int(kw), int(kw)]
                entities.append({"name": kw, "type": "YEAR"})
        return {"intent": "topic_research" if len(keywords)>2 else "exact_lookup",
                "entities": entities, "keywords": keywords, "synonyms": [],
                "time_range": time_range, "suggest_fields": ["title^3","full_text"]}

    def _ollama_understand_query(self, query: str) -> dict:
        user = f'用户查询："{query}"\n\n仅输出 JSON。'
        result = self._call_ollama(SYSTEM_QUERY, user, temperature=0.0, max_tokens=256)
        # _call_ollama 已返回 dict（经 _parse_llm_json），无需再 json.loads
        if isinstance(result, dict):
            return result
        try:
            return json.loads(result)
        except (json.JSONDecodeError, TypeError):
            return {"intent":"keyword_search","entities":[],"time_range":None,
                    "keywords":query.split(),"synonyms":[],"suggest_fields":["title^3","full_text"]}

    def _real_understand_query(self, query: str) -> dict:
        user = f'用户查询："{query}"\n\n仅输出 JSON。'
        result = self._call_llamafactory(SYSTEM_QUERY, user)
        try: return json.loads(result)
        except json.JSONDecodeError:
            return {"intent":"keyword_search","entities":[],"time_range":None,
                    "keywords":query.split(),"synonyms":[],"suggest_fields":["title^3","full_text"]}

    # ============================================================
    # Ollama API
    # ============================================================

    def _call_ollama(self, system: str, user: str, temperature: float = 0.1, max_tokens: int = 1024) -> dict:
        """调用 Ollama /api/chat，自动解析 JSON 返回"""
        url = f"{settings.OLLAMA_URL}/api/chat"
        try:
            resp = requests.post(url, json={
                "model": settings.OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }, timeout=120)
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("message", {}).get("content", "")
                return self._parse_llm_json(content)

            logger.error(f"Ollama HTTP {resp.status_code}: {resp.text[:200]}")
            return self._fallback_result(f"Ollama HTTP {resp.status_code}")
        except requests.ConnectionError:
            logger.warning(f"Ollama 不可达 ({settings.OLLAMA_URL})，降级 mock")
            return self._fallback_result("Ollama 服务未启动")
        except Exception as e:
            logger.error(f"Ollama 调用失败: {e}")
            return self._fallback_result(str(e)[:80])

    # ============================================================
    # LLaMA-Factory API
    # ============================================================

    def _call_llamafactory(self, system: str, user: str, temperature: float = 0.1, max_tokens: int = 1024) -> str:
        try:
            resp = requests.post(f"{LLAMAFACTORY_URL}/api/chat", json={
                "messages": [{"role":"system","content":system}, {"role":"user","content":user}],
                "temperature": temperature, "max_tokens": max_tokens,
            }, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("choices",[{}])[0].get("message",{}).get("content","") or data.get("response","") or str(data)
            return f"HTTP {resp.status_code}: {resp.text[:300]}"
        except requests.ConnectionError:
            return '{"risk_score":50,"risk_level":"中","suggestion":"建议人工复核","reason":"LLM 服务不可达","confidence":0.3,"llm_available":false}'
        except Exception as e:
            return f'{{"risk_score":50,"risk_level":"中","suggestion":"建议人工复核","reason":"{str(e)[:80]}","confidence":0.3,"llm_available":false}}'

    # ============================================================
    # 工具方法
    # ============================================================

    def _parse_llm_json(self, content: str) -> dict:
        """从 LLM 返回内容中提取 JSON"""
        # 去掉 markdown 代码块
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:]) if len(lines) > 1 else content
            if content.endswith("```"):
                content = content[:-3]
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # 尝试提取 { ... }
            start = content.find("{")
            end = content.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(content[start:end+1])
                except json.JSONDecodeError:
                    pass
            return self._fallback_result("JSON 解析失败")

    def _fallback_result(self, reason: str) -> dict:
        return {
            "risk_score": 50, "risk_level": "中",
            "sensitive_items": [],
            "suggestion": "建议人工复核",
            "reason": reason,
            "confidence": 0.5,
            "llm_available": False,
        }


# 全局单例
llm_client = LLMClient()
