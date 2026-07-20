# OCR 模块测试指南

## 一、测试环境

### 1.1 Mock 模式（无需安装 PaddleOCR）

```powershell
# .env 配置
OCR_MODE=mock

# 启动后端
.\start-dev.ps1
```

Mock 模式下所有 OCR 端点返回模拟数据，API 接口完全可用，但不会真实识别图像。

### 1.2 Real 模式（需安装 PaddleOCR）

```powershell
# 安装 PaddleOCR（首次含模型下载，约 500MB）
pip install paddlepaddle paddleocr

# .env 配置
OCR_MODE=real

# 启动后端
.\start-dev.ps1

# 另开终端启动 Celery Worker（批量任务用）
.venv\Scripts\python.exe -m celery -A app.tasks.celery_app worker --loglevel=info
```

---

## 二、测试端点

### 2.1 健康检查

```
GET http://localhost:8000/api/health
→ 返回 {"ocr_mode":"mock","status":"ok",...}
```

### 2.2 调试端点（同步识别，测试专用）

```
POST http://localhost:8000/api/ocr/debug/test
Content-Type: application/json

{
  "text": "关于一九九六年招生工作的总结报告。共录取本科生1200人。",
  "image_path": "test_samples/handwritten_1.jpg"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| text | 否 | Mock 模式下作为"识别结果"返回 |
| image_path | 否 | Real 模式下指定图像路径 |

**返回示例**：
```json
{
  "mode": "mock",
  "result": {
    "text": "关于一九九六年招生工作的总结报告...",
    "confidence": 0.964,
    "pages": 1,
    "processing_time_ms": 345,
    "engine": "mock"
  },
  "debug": {
    "ocr_available": false,
    "celery_available": false,
    "model_info": "mock mode - no real OCR engine loaded"
  }
}
```

### 2.3 创建 OCR 任务

```
POST http://localhost:8000/api/ocr/tasks
Authorization: Bearer <token>
Content-Type: application/json

{
  "task_name": "测试任务-招生档案",
  "category": "行政档案"
}
```

### 2.4 任务列表

```
GET http://localhost:8000/api/ocr/tasks?page=1&page_size=20
Authorization: Bearer <token>
```

### 2.5 任务详情

```
GET http://localhost:8000/api/ocr/tasks/{task_id}
Authorization: Bearer <token>
```

### 2.6 任务操作（暂停/恢复/取消）

```
PUT http://localhost:8000/api/ocr/tasks/{task_id}?action=pause
Authorization: Bearer <token>
```

### 2.7 识别结果

```
GET http://localhost:8000/api/ocr/results/{archive_id}
Authorization: Bearer <token>
```

---

## 三、自动化测试

```powershell
# 运行 OCR 相关测试
.venv\Scripts\python.exe -m pytest archive-system/backend/tests/test_e2e.py::TestFullFlow::test_22_ocr_tasks -v
```

---

## 四、测试用例

| 编号 | 场景 | 步骤 | 预期 |
|------|------|------|------|
| TC-OCR-01 | Mock 调试端点 | POST /api/ocr/debug/test {"text":"测试文本"} | 返回模拟结果，含 mode/debug 信息 |
| TC-OCR-02 | 创建任务（Mock） | POST /api/ocr/tasks | status=queued，任务被派发 |
| TC-OCR-03 | 任务列表 | GET /api/ocr/tasks | 返回任务列表 |
| TC-OCR-04 | 暂停任务 | PUT /api/ocr/tasks/1?action=pause | status=paused |
| TC-OCR-05 | 恢复任务 | PUT /api/ocr/tasks/1?action=resume | status=running |
| TC-OCR-06 | 取消任务 | PUT /api/ocr/tasks/1?action=cancel | status=cancelled |
| TC-OCR-07 | 识别结果（Mock） | GET /api/ocr/results/1996-XZ-001 | 返回 OCR 文本+置信度 |
| TC-OCR-08 | Real 健康检查 | 切换 OCR_MODE=real | /api/health 返回 ocr_mode=real |
| TC-OCR-09 | Real 调试端点 | POST /api/ocr/debug/test | 返回真实识别结果或错误信息 |
| TC-OCR-10 | Real 批量任务 | 安装 PaddleOCR+启动 Worker → 创建任务 | 任务自动执行，ES 索引更新 |

---

## 五、注意事项

1. **Mock 模式**下所有图像路径参数被忽略，返回基于文本哈希的确定性随机结果
2. **Real 模式**首次启动会加载 PaddleOCR 模型，耗时 2-5 秒
3. Celery Worker 需要 Redis（或降级为同步模式）
4. 调试端点 `/ocr/debug/test` **不需要 Token**（测试专用通道）
