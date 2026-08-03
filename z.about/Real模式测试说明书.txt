============================================
  档案智能查询与开放审核系统
  Real 模式逐级验证说明书
  2026-08-05
============================================

本文档提供从 mock 开发环境切换到 real 模式的完整操作步骤，
每级验证可独立执行，建议按 L1→L2→L3 顺序推进。


============================================
L1 · Elasticsearch 全文检索
============================================

【影响范围】智能检索的全部功能
  - 关键词检索（IK 分词 + 字段加权 + 高亮）
  - 语义检索（LLM 理解意图 → ES DSL）
  - 高级检索（多条件组合 + range/term 过滤）
  - 同义词扩展、排序优化

【前提条件】
  - Docker Desktop 已安装运行
  - 或本地已有 ES 8.x 实例（端口 9200）

【操作步骤 — Docker 方式】

  1. 启动 ES 容器：
     docker compose up -d elasticsearch

  2. 等待 ES 就绪（约 30 秒），检查健康：
     curl http://localhost:9200/_cluster/health

  3. 创建索引：
     bash backend/scripts/init_es.sh
     （Windows 用 Git Bash 或 WSL 执行）

  4. 重启后端（后端启动时连接 ES）：
     docker compose restart backend
     或本地启动: .\start-dev.ps1 重启

  5. 验证：
     打开 http://localhost:8000/api/health
     → es_available: true, index_exists: true

  6. 索引种子数据：
     在检索页面执行任意关键词检索（如"招生"），
     后端首次查询时 ES 索引为空，需手动触发数据入 ES。
     
     临时方案 — 后端启动时会调用 seed() 插入 5 条档案，
     但不会自动入 ES。运行以下脚本批量导入：

     python -c "
     import sys; sys.path.insert(0, 'archive-system/backend')
     from app.core.database import SessionLocal
     from app.models.models import Archive
     from app.tasks.ocr_tasks import _update_es_index
     db = SessionLocal()
     for a in db.query(Archive).filter(Archive.ocr_text.isnot(None), Archive.ocr_text != '').all():
         _update_es_index(a)
         print(f'  ES indexed: {a.archive_id}')
     db.close()
     "

【操作步骤 — 本地 ES 方式（无 Docker）】

  1. 下载 ES 8.x：https://www.elastic.co/downloads/elasticsearch
  2. 解压后启动：bin/elasticsearch.bat（Windows）或 bin/elasticsearch（Linux）
  3. 改 .env：ES_HOST=localhost  ES_PORT=9200
  4. 创建索引：bash backend/scripts/init_es.sh
  5. 重启后端，验证 health 端点

【验证清单】
  □ health 端点返回 es_available: true
  □ 关键词"招生"能搜到 1996-XZ-001
  □ 检索结果有 highlight 高亮标签
  □ 高级检索「门类=行政档案」过滤生效
  □ 排序切换（相关度/时间）结果顺序变化

【回退 mock】
  停掉 ES 容器：docker compose stop elasticsearch
  后端自动降级 SQLite，无需改配置。


============================================
L2 · Ollama 本地 LLM
============================================

【影响范围】AI 预审的全部功能
  - 预审工作台 → AI 预审按钮
  - 预审任务批量审核
  - 语义检索的 LLM query 理解

【前提条件】
  - 已安装 Ollama（https://ollama.com/download）
  - 内存 ≥ 8GB（qwen2.5:3b 需 ~2GB）

【操作步骤】

  1. 拉取模型（首次约 2GB 下载）：
     ollama pull qwen2.5:3b

  2. 启动 Ollama 服务（如果未自动启动）：
     ollama serve

  3. 验证模型可用：
     ollama run qwen2.5:3b "你好，请用一句话介绍自己"

  4. 改 .env：
     LLM_MODE=ollama
     OLLAMA_URL=http://localhost:11434
     OLLAMA_MODEL=qwen2.5:3b

  5. 重启后端

  6. 验证：
     打开预审工作台 http://localhost:3000/review
     → 粘贴测试文本（如种子数据中的 1996-XZ-001 OCR 文本）
     → 点击「AI 预审」
     → 右侧面板应显示：
       - 风险评分（非 mock 的确定性值）
       - 敏感信息列表（LLM 实际标注）
       - 建议理由（非 mock 模板文字）

【一键部署脚本】
  .\deploy\ollama_setup.ps1
  （自动检测 Ollama → 拉取 qwen2.5:3b → 验证 → 提示配置 .env）

【验证清单】
  □ ollama list 显示 qwen2.5:3b
  □ curl http://localhost:11434/api/tags 返回模型列表
  □ 预审结果不含 [MOCK] 标记
  □ 预审结果 confidence 非固定值（多次审核同一文本有微小差异）
  □ 建议理由为自然语言而非模板

【性能参考（qwen2.5:3b）】
  - 单次审核耗时: 2-5 秒
  - 内存占用: ~2GB
  - 如需更高精度: ollama pull qwen2.5:7b（~4GB）
  - 如需更高速度: ollama pull qwen2.5:1.5b（~1GB）

【回退 mock】
  .env 改 LLM_MODE=mock，重启后端。


============================================
L3 · PaddleOCR 真实识别
============================================

【影响范围】OCR 识别全部功能
  - OCR 任务创建 & 批量处理
  - 档案原文文字识别
  - 识别结果 = 全文检索数据源

【前提条件】
  - 已部署 PaddleOCR（.\deploy\ocr_deploy.ps1）
  - sync_data/ 下有真实图像文件
  - GPU 推荐但 CPU 也可（首次推理较慢）

【操作步骤】

  A. 一键部署

  1. 运行部署脚本（自动检测 GPU/CPU）：
     .\deploy\ocr_deploy.ps1
     （或强制 CPU：.\deploy\ocr_deploy.ps1 -Cpu）

  2. 功能验证：
     .\deploy\ocr_deploy.ps1 -Verify
     → 6 项检查全部通过

  B. 准备图像文件

  1. 按「年度/门类/」目录结构放入 sync_data/：
     sync_data/
     ├── 1996/
     │   └── 行政档案/
     │       └── 1996-XZ-001.tiff  ← 真实扫件
     ├── 1995/
     │   └── 党群档案/
     │       └── 1995-DQ-012.tiff
     ...

  2. 支持的格式：TIFF / JPG / PNG / PDF

  C. 配置 & 验证

  1. 改 .env：
     OCR_MODE=real

  2. 重启后端

  3. 验证引擎状态：
     打开 OCR 任务页面 http://localhost:3000/ocr
     → 引擎标签应显示「PaddleOCR GPU」或「PaddleOCR CPU」
     → 不再显示「Mock 模式」

  4. 单条验证：
     curl -X POST http://localhost:8000/api/ocr/debug/test \
       -H "Authorization: Bearer <token>" \
       -H "Content-Type: application/json" \
       -d '{"image_path": "sync_data/1996/行政档案/1996-XZ-001.tiff"}'
     → engine: "paddleocr", confidence > 0

  5. 批量验证：
     OCR 任务页面 → 创建任务 → 设置筛选条件 → 提交
     → 任务状态变为 processing → completed
     → 详情显示已处理页数、置信度

【性能参考】
  - GPU (CUDA): 500-2000 页/分钟（取决于图像大小）
  - CPU: 20-50 页/分钟
  - 模型下载: 首次运行自动拉取 ~80MB

【验证清单】
  □ ocr_deploy.ps1 -Verify 全部通过
  □ OCR 页面引擎标签非 Mock
  □ 创建任务后 status 从 pending→running→completed
  □ 识别结果文本非 [MOCK OCR 结果]
  □ confidence > 0 且每次不同图像不同值
  □ 批量任务进度条正常更新
  □ 多页 TIFF 自动分离逐页识别

【回退 mock】
  .env 改 OCR_MODE=mock，重启后端。


============================================
L4 · 全栈 Real（所有组件联动验证）
============================================

【前提】L1 + L2 + L3 全部通过

【全链路测试流程】

  1. 确认 .env 三项均为 real：
     LLM_MODE=ollama          （或 real 连 LLaMA-Factory）
     OCR_MODE=real
     ES_HOST=localhost        （确保 ES 运行）

  2. 确认 health 端点返回正确：
     curl http://localhost:8000/api/health
     → status: ok
     → db_mode: sqlite（本地）或 mysql（Docker）
     → llm_mode: ollama 或 real
     → ocr_mode: real
     → es_available: true

  3. 完整流程验证：

     a. OCR 识别（L3）
        创建 OCR 任务 → 等待完成 → 查看识别文本

     b. 智能检索（L1）
        在检索页搜索 OCR 识别出的文本关键词
        → ES 返回高亮结果 → 点击结果进详情页

     c. AI 预审（L2）
        从详情页点「送审」→ 预审工作台
        → 点击「AI 预审」
        → 真实 LLM 分析敏感信息、生成建议

     d. 预审记录
        查看预审记录 → 筛选/导出 → 确认数据完整

  4. 运行测试套件（all-real 模式下部分测试因环境差异可能不通过）：
     python -m pytest archive-system/backend/tests/ -v

【已知差异（real vs mock）】
  - LLM 审核结果非确定性（同一文本两次可能不同）
  - OCR 识别耗时显著长于 mock（从毫秒→秒级）
  - ES 首次查询需建索引，首请求较慢
  - Celery 需要 Redis 才走异步（无 Redis 时同步执行，可能超时）


============================================
故障排查
============================================

【ES 连接失败】
  现象: health 端点显示 es_available: false
  检查: docker ps | findstr elasticsearch
  修复: docker compose up -d elasticsearch
       等待 30 秒后重试

【Ollama 连接失败】
  现象: 预审返回 "Ollama 服务未启动"，LLM 降级 mock
  检查: curl http://localhost:11434/api/tags
  修复: ollama serve
       确保 11434 端口未被占用

【Ollama 响应极慢（>30 秒）】
  现象: 预审一直 loading
  原因: CPU 推理 3B 模型较慢
  方案: ollama pull qwen2.5:1.5b（更小模型）
       或用 GPU 版 Ollama

【PaddleOCR 未安装】
  现象: OCR 识别降级 mock
  检查: python -c "import paddleocr; print('OK')"
  修复: .\deploy\ocr_deploy.ps1 -Cpu

【PaddleOCR GPU 不可用】
  现象: GPU 检测失败，自动降级 CPU
  检查: nvidia-smi
  修复: 安装 CUDA 11.8+ 和 cuDNN
       pip install paddlepaddle-gpu==3.0.0

【图像文件找不到】
  现象: OCR 任务 completed 但失败数=总数
  原因: sync_data/ 下无对应图像
  修复: 按「年度/门类/档案编号.tiff」结构放入文件

【Celery 不执行】
  现象: 任务一直 pending
  原因: Redis 不可用，Celery 降级
  方案: Docker 启 Redis → docker compose up -d redis
       或等待 memory:// 同步执行（可能较慢）


============================================
LLaMA-Factory 远端 LLM（需向日葵）
============================================

【仅在学校主机可访问时使用】

  1. 向日葵连接学校主机
     识别码: 238426546
     验证码: 单次（联系王华哲老师获取）

  2. 浏览器打开 http://10.11.13.100:7860
     确认 LLaMA-Factory Web UI 可访问
     确认模型已加载（查看模型列表）

  3. 改 .env：
     LLM_MODE=real
     LLAMAFACTORY_URL=http://10.11.13.100:7860

  4. 重启后端，预审时调用远端 LLaMA-Factory

【注意事项】
  - 学校主机可能未 7×24 开机
  - 网络延迟较 Ollama 本地高
  - 如不可达，LLM 自动降级 mock 并返回 confidence=0.5
