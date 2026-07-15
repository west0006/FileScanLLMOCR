"""
LLaMA-Factory 真机测试脚本（零依赖，复制到学校主机直接跑）

用法（在学校主机上）:
  python test_llamafactory_on_host.py

这个脚本通过向日葵复制到学校主机后执行，
不需要安装任何第三方库（仅用 Python 标准库）。
"""

import json
import urllib.request
import urllib.error
import sys

BASE_URL = "http://10.11.13.100:7860"


def http_get(path: str):
    """GET 请求"""
    try:
        with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        return None, str(e.reason)
    except Exception as e:
        return None, str(e)


def http_post(path: str, data: dict):
    """POST 请求"""
    try:
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            f"{BASE_URL}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        return None, str(e.reason)
    except Exception as e:
        return None, str(e)


def main():
    print("=" * 60)
    print("  LLaMA-Factory 真机测试")
    print(f"  目标: {BASE_URL}")
    print("=" * 60)
    print()

    # ---- 1. 连通性 ----
    print("[1/4] 检查连通性...")
    status, body = http_get("/")
    if status == 200:
        print(f"  ✅ 服务器可达 (HTTP {status})")
        if "LLaMA" in body[:500]:
            print("  ✅ 确认为 LLaMA-Factory Web UI")
    else:
        print(f"  ❌ 无法连接: {body}")
        print()
        print("  可能原因:")
        print("  1. LLaMA-Factory 服务未启动")
        print("  2. 地址或端口不对")
        print("  3. 防火墙拦截")
        return
    print()

    # ---- 2. 模型列表 ----
    print("[2/4] 获取模型列表...")
    status, body = http_get("/api/models")
    if status == 200:
        try:
            models = json.loads(body)
            if isinstance(models, list):
                print(f"  ✅ 可用模型 ({len(models)} 个):")
                for m in models:
                    name = m.get("name") or m.get("id") or str(m)
                    print(f"     • {name}")
        except json.JSONDecodeError:
            print(f"  ⚠️ 无法解析响应: {body[:200]}")
    else:
        print(f"  ⚠️ HTTP {status}: {body[:200] if body else '无响应'}")
    print()

    # ---- 3. 推理测试 ----
    print("[3/4] 推理 API 测试...")
    test_payload = {
        "messages": [
            {"role": "system", "content": "你是档案审核专家。请用 JSON 回复。"},
            {"role": "user", "content": "审核以下档案：\n\n关于一九九六年招生工作的总结报告。本年度共录取本科生1200人。"},
        ],
        "temperature": 0.1,
        "max_tokens": 256,
    }
    status, body = http_post("/api/chat", test_payload)
    if status == 200:
        print("  ✅ 推理 API 可用")
        try:
            result = json.loads(body)
            content = (
                result.get("choices", [{}])[0].get("message", {}).get("content", "")
                or result.get("response", "")
            )
            print(f"  模型回复: {content[:300]}")
        except json.JSONDecodeError:
            print(f"  原始响应: {body[:300]}")
    else:
        print(f"  ⚠️ HTTP {status}: {body[:200] if body else '无响应'}")
        print("  (可能模型未加载，需先在 Web UI 中加载模型)")
    print()

    # ---- 4. 训练参数 ----
    print("[4/4] 训练参数...")
    status, body = http_get("/api/train_args")
    if status == 200:
        print("  ✅ 训练 API 可用")
    else:
        print(f"  ⚠️ HTTP {status}")

    print()
    print("=" * 60)
    print("  测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
