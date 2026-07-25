# OCR 模块测试指南 (v2.0)

> 更新于 2026-07-24，覆盖 PaddleOCR-VL 双路部署方案

---

## 一、快速开始

### 1.1 Mock 模式（本地开发，零依赖）

```powershell
# .env 默认配置
OCR_MODE=mock

# 启动后端
.\start.ps1
```

所有 OCR 端点可用，返回基于文件路径 MD5 哈希的确定性模拟结果（同一输入多次调用结果一致）。

### 1.2 Real 模式（PaddleOCR 真实识别）

```powershell
# 一键部署 PaddleOCR-VL（自动检测 GPU/CUDA）
.\install.ps1 -WithOCR

# 切换到真实模式
$env:OCR_MODE = "real"
.\start.ps1
```

```bash
# Linux
bash deploy/ocr_deploy.sh
OCR_MODE=real bash start-dev.sh
```

### 1.3 Docker 部署（GPU 透传）

```bash
# 基础服务
docker compose up -d --build

# OCR 专用 Worker（自动使用 GPU）
docker compose --profile ocr up -d
```

---

## 二、环境检测与验证

### 2.1 环境检测

```bash
# 完整报告
python deploy/ocr_env_detect.py

# 仅输出部署策略 (gpu/cpu)
python deploy/ocr_env_detect.py --quiet

# JSON 输出（供脚本消费）
python deploy/ocr_env_detect.py --json
```

输出示例：
```
🎮 GPU: ✅
   型号: NVIDIA GeForce RTX 3060
   显存: 12288 MB
   驱动: 546.01
   CUDA: 12.4
   cuDNN: 8.9.7

📋 部署策略: 🚀 GPU 加速部署
```

### 2.2 功能验证

```bash
# 全部 6 项检查
python deploy/ocr_verify.py

# 快速验证（跳过性能基准）
python deploy/ocr_verify.py --quick
```

验证项目：
| # | 检查项 | 说明 |
|---|--------|------|
| 1 | PaddlePaddle 导入 | 版本 + GPU/CPU 模式 |
| 2 | 中文 OCR 识别 | PP-OCRv5 Server 印刷体识别 |
| 3 | 方向分类 | 旋转文本自动纠正 |
| 4 | 版面分析 | PP-StructureV2 标题/表格/段落 |
| 5 | GPU 加速 | CUDA 设备可见 + 推理利用率 |
| 6 | 性能基准 | 5 次推理取平均 ms/页 |

---

## 三、API 端点

### 3.1 引擎信息

```
GET http://localhost:8000/api/ocr/models
Authorization: Bearer <token>
```

返回：
```json
{
  "available": true,
  "gpu": true,
  "mode": "real",
  "ocr_mode": "real",
  "paddle_version": "3.0.0",
  "cuda_version": "12.0"
}
```

### 3.2 调试端点（同步识别，无需 Token）

```
POST http://localhost:8000/api/ocr/debug/test
Content-Type: application/json

{
  "text": "关于一九九六年招生工作的总结报告。共录取本科生1200人。",
  "image_path": "C:/archive_images/1996-XZ-001.tiff"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| text | 否 | Mock 模式下覆盖识别文本 |
| image_path | 否 | Real 模式下指定图像路径。支持 TIFF/JPG/PNG/PDF |

返回：
```json
{
  "mode": "real",
  "result": {
    "text": "关于一九九六年招生工作的总结报告\n本年度招生工作...",
    "confidence": 0.964,
    "pages": 1,
    "engine": "paddleocr",
    "gpu_used": true,
    "processing_time_ms": 345,
    "blocks": [
      {"text": "关于一九九六年...", "confidence": 0.98, "bbox": [[42,18],[380,18],[380,52],[42,52]]}
    ]
  },
  "debug": {
    "ocr_available": true,
    "celery_available": false
  }
}
```

### 3.3 版面分析

```
POST http://localhost:8000/api/ocr/detect?image_path=C:/archive_images/1996-XZ-001.tiff
Authorization: Bearer <token>
```

返回检测到的标题、表格、段落、印章区域。

### 3.4 创建 OCR 任务

```
POST http://localhost:8000/api/ocr/tasks
Authorization: Bearer <token>
Content-Type: application/json

{
  "task_name": "1996年行政档案批量OCR",
  "category": "行政档案",
  "year_from": 1996,
  "year_to": 1996,
  "engine": "paddleocr",
  "enable_preprocess": true,
  "priority": 1
}
```

| 字段 | 说明 |
|------|------|
| task_name | 任务名称 |
| year_from/year_to | 归档年度范围 |
| category | 门类筛选（可选） |
| department | 归口单位筛选（可选） |
| engine | `paddleocr` / `mock` |
| enable_preprocess | 是否启用去噪/CLAHE 预处理 |
| priority | 0=普通, 1=高, 2=紧急 |

### 3.5 任务管理

```
GET    /api/ocr/tasks?page=1&page_size=20&status=running
GET    /api/ocr/tasks/{task_id}
PUT    /api/ocr/tasks/{task_id}?action=start|pause|resume|cancel
```

任务列表返回含 `priority` 字段。

### 3.6 识别结果

```
GET http://localhost:8000/api/ocr/results/{archive_id}
Authorization: Bearer <token>
```

返回：
```json
{
  "archive_id": "1996-XZ-001",
  "ocr_text": "关于一九九六年招生工作...",
  "confidence": 0.964,
  "status": "done"
}
```

### 3.7 质量报告

```
GET http://localhost:8000/api/ocr/quality-report?task_id=1
Authorization: Bearer <token>
```

返回含低置信度档案列表及 OCR 文本前 200 字预览：
```json
{
  "overall_accuracy": 0.934,
  "total": 120,
  "low_confidence_count": 3,
  "low_confidence_ids": [
    {"archive_id": "1973-JX-008", "title": "...", "confidence": 0.62, "ocr_preview": "一九七三年教学..."}
  ],
  "failed_count": 1,
  "common_errors": [{"type": "低置信度", "count": 3}]
}
```

---

## 四、自动化测试

```powershell
# 全部测试（82 个用例）
pytest archive-system/backend/tests/ -v

# OCR 专项（17 个用例）
pytest archive-system/backend/tests/test_ocr_client.py -v

# 单测
pytest archive-system/backend/tests/test_ocr_client.py::TestOcrEndpoints::test_debug_test -v
```

OCR 测试覆盖：

| 测试类 | 用例数 | 内容 |
|--------|--------|------|
| TestOcrClient | 6 | Mock 识别/一致性/差异/版面/信息/批量 |
| TestPageSplitter | 2 | 单页分离/空路径处理 |
| TestOcrProcessor | 2 | 无文件/管线处理 |
| TestEnvDetect | 3 | 导入/GPU信息/PaddlePaddle检测 |
| TestOcrEndpoints | 4 | models/tasks/quality-report/debug 端点 |

---

## 五、手动测试用例

| 编号 | 场景 | 步骤 | 预期 |
|------|------|------|------|
| TC-01 | 环境检测 | `python deploy/ocr_env_detect.py` | 输出 GPU/CUDA/PaddlePaddle 状态 + 部署策略 |
| TC-02 | 功能验证 | `python deploy/ocr_verify.py --quick` | 6 项全部 PASS 或 SKIP |
| TC-03 | Mock 调试 | POST /api/ocr/debug/test `{"text":"测试"}` | 返回 mock 结果，engine=mock |
| TC-04 | Real 调试 | 切换 OCR_MODE=real → POST /api/ocr/debug/test | 返回真实 OCR 或降级提示 |
| TC-05 | 引擎信息 | GET /api/ocr/models | 返回 available/gpu/mode/paddle_version |
| TC-06 | 版面分析 | POST /api/ocr/detect?image_path=... | 返回 regions + tables |
| TC-07 | 创建任务 | POST /api/ocr/tasks `{"task_name":"测试","priority":1}` | status=queued |
| TC-08 | 任务列表 | GET /api/ocr/tasks | 含 priority 字段 |
| TC-09 | 暂停/恢复 | PUT /api/ocr/tasks/1?action=pause → resume | status 切换 |
| TC-10 | 识别结果 | GET /api/ocr/results/1996-XZ-001 | 返回 ocr_text + confidence + status |
| TC-11 | 质量报告 | GET /api/ocr/quality-report | 含 low_confidence_ids + ocr_preview |
| TC-12 | 原文下载 | GET /api/search/archives/1996-XZ-001/download | Content-Disposition: attachment |
| TC-13 | 图像预览 | GET /api/search/archives/1996-XZ-001/image | 返回 TIFF→PNG 转码 URL |
| TC-14 | GPU Docker | `docker compose -f deploy/docker/docker-compose.ocr.yml --profile gpu up -d` | 容器启动，nvidia-smi 可见 |
| TC-15 | CPU Docker | `docker compose -f deploy/docker/docker-compose.ocr.yml --profile cpu up -d` | 容器启动，CPU 模式运行 |

---

## 六、原文图像测试

### 6.1 准备测试图像

将档案扫描件放入对应目录：
```
archive-system/sync_data/
├── 1996/
│   ├── XZ/1996-XZ-001.tiff    # 行政档案
│   └── XZ/1996-XZ-002.png     # 支持多种格式
├── 1995/
│   └── DQ/1995-DQ-012.tiff    # 党群档案
└── 2000/
    └── RS/2000-RS-015.tiff    # 人事档案
```

### 6.2 种子模拟文件

系统首次启动自动生成 3 个模拟 TIFF 文件到上述目录，可直接用于下载/预览测试。

### 6.3 格式支持

| 格式 | Mock 模式 | Real 模式 |
|------|-----------|-----------|
| TIFF/TIF | ✅ 直接返回 | ✅ 逐页分离→PNG→OCR |
| JPG/PNG | ✅ 直接返回 | ✅ 直接 OCR |
| PDF | ✅ 直接返回 | ✅ 转图像→OCR（需 pdf2image） |

---

## 七、GPU vs CPU 性能对比（参考）

| 场景 | CPU (i7-12700) | GPU (RTX 3060) |
|------|---------------|-----------------|
| 单页 OCR (A4 印刷体) | ~800ms | ~120ms |
| 批量 100 页 | ~80s | ~12s |
| 版面分析 | ~1500ms | ~300ms |

---

## 八、注意事项

1. **Mock 模式确定性**：同一图像路径的识别结果始终一致（MD5 哈希种子），适合自动化测试断言
2. **Real 模式首次启动**：自动下载 PP-OCRv5 模型权重（~80MB），耗时 10-30 秒
3. **GPU 显存要求**：PP-OCRv5 Server 模型约需 2GB 显存，GTX 1660 (6GB) 及以上可正常运行
4. **Celery 依赖**：OCR 批量任务需要 Redis（开发环境自动降级为同步模式）
5. **调试端点**：`/api/ocr/debug/test` 无需 Token，方便 Postman/curl 直接测试
6. **图像预处理**：默认启用去噪+CLAHE 对比度增强+自适应二值化，泛黄/褪色档案识别率显著提升
7. **安全**：`/api/sync/files/{path}` 有路径穿越防护（检查必须在 SYNC_DATA_DIR 内）
