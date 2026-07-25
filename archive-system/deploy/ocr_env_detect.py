#!/usr/bin/env python3
"""
OCR 环境检测 — GPU/CUDA/cuDNN/PaddlePaddle 状态分析

输出:
  - 部署策略: GPU / CPU
  - 硬件信息: GPU 型号、显存、CUDA 版本、cuDNN 版本
  - 已安装组件: PaddlePaddle 版本、PaddleOCR 版本
  - 推荐配置: pip install 命令

用法:
  python deploy/ocr_env_detect.py          # 标准检测
  python deploy/ocr_env_detect.py --json   # JSON 输出（供脚本消费）
  python deploy/ocr_env_detect.py --quiet  # 仅输出策略 (gpu/cpu)
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from typing import Optional


# ============================================================
# 数据结构
# ============================================================

@dataclass
class GpuInfo:
    name: str = ""
    memory_mb: int = 0
    driver_version: str = ""
    cuda_version: str = ""
    cudnn_version: str = ""
    available: bool = False


@dataclass
class PaddleInfo:
    installed: bool = False
    version: str = ""
    gpu_support: bool = False
    cuda_version: str = ""


@dataclass
class PaddleOcrInfo:
    installed: bool = False
    version: str = ""
    models_available: bool = False


@dataclass
class OcrEnvReport:
    os: str = ""
    python_version: str = ""
    gpu: GpuInfo = field(default_factory=GpuInfo)
    paddle: PaddleInfo = field(default_factory=PaddleInfo)
    paddleocr: PaddleOcrInfo = field(default_factory=PaddleOcrInfo)
    strategy: str = "cpu"            # "gpu" | "cpu"
    install_command: str = ""        # 推荐的 pip install 命令
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


# ============================================================
# 检测函数
# ============================================================

def _run(cmd: str | list[str], timeout: int = 10) -> tuple[int, str, str]:
    """执行命令，返回 (returncode, stdout, stderr)"""
    if isinstance(cmd, str):
        cmd = ["cmd", "/c", cmd] if platform.system() == "Windows" else ["bash", "-c", cmd]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return -1, "", ""


def detect_gpu() -> GpuInfo:
    """检测 NVIDIA GPU 和 CUDA 环境"""
    info = GpuInfo()

    # --- 1. nvidia-smi ---
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        rc, stdout, stderr = _run([nvidia_smi, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"])
        if rc == 0 and stdout:
            info.available = True
            parts = [p.strip() for p in stdout.split(",")]
            if len(parts) >= 3:
                info.name = parts[0]
                try: info.memory_mb = int(parts[1])
                except ValueError: pass
                info.driver_version = parts[2]
    else:
        # 尝试 pynvml
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            info.name = pynvml.nvmlDeviceGetName(handle)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            info.memory_mb = mem.total // (1024 * 1024)
            info.driver_version = pynvml.nvmlSystemGetDriverVersion()
            info.available = True
            pynvml.nvmlShutdown()
        except Exception:
            pass

    if not info.available:
        return info

    # --- 2. CUDA 版本 (nvcc) ---
    nvcc = shutil.which("nvcc")
    if nvcc:
        rc, stdout, _ = _run([nvcc, "--version"])
        if rc == 0 and "release" in stdout.lower():
            for line in stdout.split("\n"):
                if "release" in line.lower():
                    info.cuda_version = line.split("release")[-1].strip().split(",")[0].strip()
                    break
    else:
        # 从 nvidia-smi 输出推断（显示的是驱动支持的最高 CUDA 版本）
        rc, stdout, _ = _run([nvidia_smi], timeout=5) if nvidia_smi else (-1, "", "")
        if "CUDA Version:" in stdout:
            info.cuda_version = stdout.split("CUDA Version:")[-1].strip().split()[0]

    # --- 3. cuDNN ---
    # 检查常见 cuDNN 头文件路径
    cudnn_paths = [
        "/usr/include/cudnn_version.h",
        "/usr/include/cudnn.h",
        "/usr/local/cuda/include/cudnn_version.h",
        "/usr/local/cuda/include/cudnn.h",
    ]
    if platform.system() == "Windows":
        cudnn_paths = [
            os.path.join(os.environ.get("CUDA_PATH", "C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA"), "include", "cudnn_version.h"),
        ]

    for p in cudnn_paths:
        if os.path.exists(p):
            try:
                with open(p) as f:
                    content = f.read()
                import re
                major = re.search(r"CUDNN_MAJOR\s+(\d+)", content)
                minor = re.search(r"CUDNN_MINOR\s+(\d+)", content)
                patch = re.search(r"CUDNN_PATCHLEVEL\s+(\d+)", content)
                if major:
                    info.cudnn_version = f"{major.group(1)}.{minor.group(1) if minor else '0'}.{patch.group(1) if patch else '0'}"
                    break
            except Exception:
                pass

    return info


def detect_paddle() -> PaddleInfo:
    """检测 PaddlePaddle 安装状态"""
    info = PaddleInfo()
    try:
        import paddle
        info.installed = True
        info.version = paddle.__version__
        info.gpu_support = paddle.is_compiled_with_cuda()
        if info.gpu_support:
            info.cuda_version = paddle.version.cuda()
    except ImportError:
        pass
    return info


def detect_paddleocr() -> PaddleOcrInfo:
    """检测 PaddleOCR 安装状态"""
    info = PaddleOcrInfo()
    try:
        import paddleocr
        info.installed = True
        info.version = getattr(paddleocr, "__version__", "unknown")
        # 检查模型是否已下载
        model_dir = os.path.expanduser("~/.paddleocr/whl")
        if os.path.isdir(model_dir):
            info.models_available = any(f.endswith((".pdparams", ".pdopt", ".pdiparams"))
                                         for f in os.listdir(model_dir) if os.path.isfile(os.path.join(model_dir, f)))
    except ImportError:
        pass
    return info


def determine_strategy(gpu: GpuInfo, paddle: PaddleInfo) -> str:
    """决定 GPU 还是 CPU 部署"""
    if gpu.available and gpu.memory_mb >= 2000:
        # GPU 存在且显存 >= 2GB，推荐 GPU 方案
        return "gpu"
    if paddle.installed and paddle.gpu_support:
        return "gpu"  # 已有 GPU 版 PaddlePaddle
    return "cpu"


def build_install_command(gpu: GpuInfo, strategy: str) -> tuple[str, list[str]]:
    """构建推荐的安装命令"""
    issues = []
    commands = []

    if strategy == "gpu":
        # 检查 CUDA 版本兼容性
        cuda_ver = gpu.cuda_version or "12.0"
        major = cuda_ver.split(".")[0]

        if major == "11":
            # CUDA 11.x → paddlepaddle-gpu
            commands.append("pip install paddlepaddle-gpu==3.0.0 -f https://www.paddlepaddle.org.cn/whl/linux/cuda11/stable.html")
            cuda_tag = "11.8"
        elif major == "12":
            commands.append("pip install paddlepaddle-gpu==3.0.0 -f https://www.paddlepaddle.org.cn/whl/linux/cuda12/stable.html")
            cuda_tag = "12.0"
        else:
            issues.append(f"CUDA {cuda_ver} 版本未在官方支持列表中，尝试 CUDA 12 版本")
            commands.append("pip install paddlepaddle-gpu==3.0.0 -f https://www.paddlepaddle.org.cn/whl/linux/cuda12/stable.html")
            cuda_tag = "12.0"

        if not gpu.cudnn_version:
            issues.append("cuDNN 未检测到 — GPU 训练/推理可能降级或失败，请安装 cuDNN 8.9+ for CUDA " + cuda_tag)
    else:
        commands.append("pip install paddlepaddle==3.0.0")

    # PaddleOCR + 结构分析
    commands.append("pip install paddleocr>=2.9.0")
    commands.append("pip install paddleclas")  # PP-StructureV2 依赖

    # 图像处理依赖
    commands.append("pip install opencv-python-headless>=4.9.0 shapely pyclipper imgaug lmdb tqdm")

    # 模型权重下载
    commands.append("python -c \"from paddleocr import PaddleOCR; ocr = PaddleOCR(lang='ch', use_angle_cls=True); print('Models OK')\"")

    install_cmd = " && ".join(commands)
    return install_cmd, issues


# ============================================================
# 主入口
# ============================================================

def detect_all() -> OcrEnvReport:
    """完整环境检测"""
    report = OcrEnvReport()
    report.os = f"{platform.system()} {platform.release()}"
    report.python_version = sys.version.split()[0]

    # 检测链
    report.gpu = detect_gpu()
    report.paddle = detect_paddle()
    report.paddleocr = detect_paddleocr()

    # 决策
    report.strategy = determine_strategy(report.gpu, report.paddle)
    report.install_command, report.issues = build_install_command(report.gpu, report.strategy)

    # 建议
    recs = report.recommendations
    if not report.paddle.installed:
        recs.append(f"PaddlePaddle 未安装 → 执行: {report.install_command.split(' && ')[0]}")
    elif report.strategy == "gpu" and not report.paddle.gpu_support:
        recs.append("已安装 CPU 版 PaddlePaddle — 建议卸载后安装 GPU 版以获得加速")
    if not report.paddleocr.installed:
        recs.append("PaddleOCR 未安装 → 执行部署脚本或 pip install paddleocr")
    if report.strategy == "gpu" and report.gpu.memory_mb < 4000:
        recs.append(f"GPU 显存较小 ({report.gpu.memory_mb}MB)，建议使用 batch_size=1 避免 OOM")
    if report.gpu.available and not report.gpu.cudnn_version:
        recs.append("建议安装 cuDNN 8.9+ 以启用 GPU 推理加速")

    return report


def print_report(report: OcrEnvReport, quiet: bool = False):
    """打印人类可读报告"""
    if quiet:
        print(report.strategy)
        return

    gpu = report.gpu
    pp = report.paddle
    ocr = report.paddleocr

    print("=" * 60)
    print("  PaddleOCR 环境检测报告")
    print("=" * 60)
    print()

    # 系统
    print(f"  🖥️  OS:              {report.os}")
    print(f"  🐍 Python:          {report.python_version}")
    print()

    # GPU
    icon = "✅" if gpu.available else "❌"
    print(f"  🎮 GPU:             {icon}")
    if gpu.available:
        print(f"     型号:            {gpu.name}")
        print(f"     显存:            {gpu.memory_mb} MB")
        print(f"     驱动:            {gpu.driver_version}")
        print(f"     CUDA:            {gpu.cuda_version or '(未检测到)'}")
        print(f"     cuDNN:           {gpu.cudnn_version or '(未检测到)'}")
    print()

    # PaddlePaddle
    icon = "✅" if pp.installed else "❌"
    gpu_tag = "GPU" if pp.gpu_support else "CPU"
    print(f"  🏓 PaddlePaddle:    {icon} {pp.version + ' ' + gpu_tag if pp.installed else ''}")
    print()

    # PaddleOCR
    icon = "✅" if ocr.installed else "❌"
    models_tag = "(模型已下载)" if ocr.models_available else "(需下载模型)"
    print(f"  📄 PaddleOCR:       {icon} {ocr.version + ' ' + models_tag if ocr.installed else ''}")
    print()

    # 策略
    strategy_label = {"gpu": "🚀 GPU 加速部署", "cpu": "💻 CPU 部署"}
    print(f"  📋 部署策略:        {strategy_label.get(report.strategy, report.strategy)}")
    print()

    # 问题
    if report.issues:
        print("  ⚠️  注意:")
        for issue in report.issues:
            print(f"     • {issue}")
        print()

    # 建议
    if report.recommendations:
        print("  💡 建议:")
        for rec in report.recommendations:
            print(f"     • {rec}")
        print()

    # 安装命令
    if report.install_command:
        print("  📦 一键安装命令:")
        for i, cmd in enumerate(report.install_command.split(" && "), 1):
            print(f"     {i}. {cmd}")
        print()


def main():
    parser = argparse.ArgumentParser(description="OCR 环境检测")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    parser.add_argument("--quiet", "-q", action="store_true", help="仅输出 gpu/cpu")
    args = parser.parse_args()

    report = detect_all()

    if args.json:
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    elif args.quiet:
        print(report.strategy)
    else:
        print_report(report)


if __name__ == "__main__":
    main()
