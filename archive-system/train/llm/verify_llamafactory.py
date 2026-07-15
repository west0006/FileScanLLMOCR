"""
LLaMA-Factory API 验证脚本

验证王华哲老师部署的 LLaMA-Factory 实例是否可用：
  地址: http://10.11.13.100:7860/

用法:
  python train/llm/verify_llamafactory.py
"""

import requests
import json
import sys
import time

BASE_URL = "http://10.11.13.100:7860"

CHECKS = [
    {
        "name": "Web UI 主页",
        "method": "GET",
        "path": "/",
        "expect_status": 200,
        "expect_text": "LLaMA",
    },
    {
        "name": "API 文档",
        "method": "GET",
        "path": "/docs",
        "expect_status": 200,
    },
    {
        "name": "模型列表",
        "method": "GET",
        "path": "/api/models",
        "expect_status": 200,
    },
    {
        "name": "训练参数获取",
        "method": "GET",
        "path": "/api/train_args",
        "expect_status": 200,
    },
]


def check_server() -> dict:
    """检查 LLaMA-Factory 服务器"""
    results = {"url": BASE_URL, "checks": [], "available": False, "models": [], "issues": []}

    session = requests.Session()
    session.timeout = 10

    # 1. 基本连通性
    try:
        resp = session.get(f"{BASE_URL}/", timeout=5)
        results["available"] = True
    except requests.ConnectionError:
        results["issues"].append(f"无法连接 {BASE_URL} — 请确认网络/VPN 已连接")
        return results
    except requests.Timeout:
        results["issues"].append(f"连接 {BASE_URL} 超时")
        return results

    # 2. 各项检查
    for check in CHECKS:
        try:
            if check["method"] == "GET":
                resp = session.get(f"{BASE_URL}{check['path']}")
            else:
                resp = session.post(f"{BASE_URL}{check['path']}")

            ok = resp.status_code == check["expect_status"]
            detail = f"HTTP {resp.status_code}"

            # 检查响应内容
            if "expect_text" in check and ok:
                if check["expect_text"] not in resp.text:
                    ok = False
                    detail += f" (内容不包含 '{check['expect_text']}')"

            results["checks"].append({
                "name": check["name"],
                "ok": ok,
                "detail": detail,
            })

            # 模型列表特殊处理
            if check["name"] == "模型列表" and ok:
                try:
                    models = resp.json()
                    results["models"] = [m.get("name", str(m)) for m in models] if isinstance(models, list) else [str(models)]
                except:
                    results["models"] = ["(无法解析)"]

        except Exception as e:
            results["checks"].append({
                "name": check["name"],
                "ok": False,
                "detail": str(e),
            })

    return results


def print_report(results: dict):
    """打印检查报告"""
    print("=" * 60)
    print("  LLaMA-Factory 服务器验证")
    print(f"  地址: {results['url']}")
    print("=" * 60)

    if not results["available"]:
        print("  ❌ 服务器不可达")
        for issue in results["issues"]:
            print(f"     → {issue}")
        print()
        print("  可能原因:")
        print("  1. 校园 VPN 未连接 (服务器在内网)")
        print("  2. 服务器未开机")
        print("  3. LLaMA-Factory 服务未启动")
        return

    print("  ✅ 服务器可达\n")

    all_ok = True
    for check in results["checks"]:
        icon = "✅" if check["ok"] else "❌"
        print(f"  {icon} {check['name']}: {check['detail']}")
        if not check["ok"]:
            all_ok = False

    if results["models"]:
        print(f"\n  📦 可用模型 ({len(results['models'])} 个):")
        for m in results["models"]:
            print(f"     • {m}")

    print()
    if all_ok:
        print("  🎉 所有检查通过！LLaMA-Factory 就绪，可以开始微调。")
        print()
        print("  下一步:")
        print("  1. 上传训练数据: train/data/review_sft.json")
        print("  2. 在 Web UI 中注册数据集: archive_review")
        print("  3. 使用 train/llm/configs/lora_train.yaml 开始训练")
    else:
        print("  ⚠️ 部分检查未通过，请确认:")
        print("  1. LLaMA-Factory 是否为完整安装 (非仅 demo)")
        print("  2. 模型文件是否已下载到服务器")
        print("  3. 版本是否为最新 (支持 LoRA + Qwen)")


def test_inference():
    """测试推理 API — 发送一条审核请求"""
    print("=" * 60)
    print("  推理 API 测试")
    print("=" * 60)

    test_text = """关于一九九六年招生工作的总结报告
    
本年度招生工作在校党委的领导下顺利完成。共录取本科生1200人，研究生300人。
具体工作包括：制定招生计划、组织考试、录取审核等环节。
    
存在问题：部分专业报考人数不足，需进一步优化专业设置。"""

    payload = {
        "model": "qwen",
        "messages": [
            {"role": "system", "content": "你是档案开放审核专家。"},
            {"role": "user", "content": f"审核以下档案：\n{test_text}"},
        ],
        "temperature": 0.1,
        "max_tokens": 512,
    }

    try:
        resp = requests.post(
            f"{BASE_URL}/api/chat",
            json=payload,
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            print("  ✅ 推理 API 可用")
            print(f"  响应: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
        else:
            print(f"  ⚠️ 推理 API 返回 HTTP {resp.status_code}")
            print(f"  {resp.text[:300]}")
    except Exception as e:
        print(f"  ❌ 推理 API 调用失败: {e}")
        print("  (可能模型未加载或 API 路径不同)")


if __name__ == "__main__":
    results = check_server()
    print_report(results)

    if results["available"]:
        print()
        test_inference()
