# Bug 修复计划

> 日期：2026-08-XX
> 范围：验收测试提交的 bug list 中，已通过代码定位坐实的缺陷
> 方法：分批次修复，每批修复后进行前后端一致性审查，再提交节点进入下一批

---

## 一、修复批次总览

| 批次 | 级别 | 内容 | 涉及文件 |
| --- | --- | --- | --- |
| Batch 1 | P0 安全/数据完整性 | fpdf2 依赖、哈希链并发锁、权限 dev 放行门控 | requirements.txt、log_middleware.py、config.py、security.py |
| Batch 2 | P1 核心功能 | 批量预审回写 open_status、前端检查 res.data.error、检索排序接入 | review_tasks.py、OcrTaskList.vue、UserManagement.vue、SearchHome.vue |
| Batch 3 | P1 审计一致性 | 日志导出前后端契约、风险分布 task_id/键统一 | OperationLogs.vue、log.py、review.py、seed.py |

---

## 二、Batch 1 详细（P0）

### 1.1 fpdf2 依赖缺失 → PDF 导出 HTTP 500

- **根因**：`export_service.py` 的 `export_to_pdf` 首行 `from fpdf import FPDF`，但 `requirements.txt` 未声明 `fpdf`/`fpdf2`，部署后 ImportError 被全局异常处理器转成 500。
- **修复**：`requirements.txt` 文件处理段新增 `fpdf2==2.8.1`（`fpdf2` 包提供 `fpdf` 模块）。
- **验证**：`pip install fpdf2` 后调用 `/api/search/export`（format=pdf）与 `/api/review/export`（format=pdf）返回 `application/pdf`。

### 1.2 哈希链并发分叉 → 链校验误报 tampered

- **根因**：`log_middleware.py` 的 `_write_log_sync` 在独立线程执行「读最新 chain_hash → 计算 → 写入 → commit」，多线程并发时两条日志读到同一 prev，形成分叉；`/log/audit/chain-verify` 按 id 升序重算时在分叉处报 tampered。
- **修复**：新增模块级 `threading.Lock`，把「读 prev → 写 → commit」包进 `with _chain_lock` 串行化。
- **验证**：并发打接口后调用 `/api/log/audit/chain-verify`，`tampered` 应归 0。
- **残留风险**：Celery 独立进程写日志（sync/audit 任务）不受该线程锁约束，跨进程仍需 DB 级串行化（记入后续）。

### 1.3 权限 dev 放行 → reviewer 可访问管理接口

- **根因**：`security.py` 的 `require_role` / `require_permission` 在 `APP_ENV == "development"` 时直接 `return user`，默认环境即 development，导致所有角色放行。
- **修复**：新增配置 `DEV_PERMISSIVE`（默认 False=强制权限），两处 dev 放行改为 `if settings.APP_ENV == "development" and settings.DEV_PERMISSIVE:`。
- **验证**：reviewer token 访问 `/api/log/`、`/api/user/`、`/api/log/audit/summary` 应返回 403；system_admin 正常。开发需放行时在 `.env` 设 `DEV_PERMISSIVE=true`。

---

## 三、Batch 2 详细（P1）

### 2.1 批量预审不回写 open_status

- **根因**：`review_tasks.py` 批量生成 ReviewRecord 后不调用 `review.py` 的 `_sync_open_status`，`Archive.open_status` 未同步。
- **修复**：`process_review_task` 落库后调用 `_sync_open_status(db, archive.archive_id, result["suggestion"])`。

### 2.2 前端不检查 res.data.error → 假成功

- **根因**：后端 `ocr.py`/`user.py` 业务失败返回 `{"error": ...}` + HTTP 200，前端 `OcrTaskList.vue handleCreateTask`、`UserManagement.vue doCreate` 只 `await` 后直接 `ElMessage.success`。
- **修复**：两处创建成功后检查 `res.data.error`，命中则 `ElMessage.error` 并中止。

### 2.3 检索排序未接入重新检索

- **根因**：`SearchHome.vue` 的 `watch` 只监听 `[activeCat, yearFrom, yearTo, activeOpenStatus]`，不含 `sortBy`，排序下拉无 `@change` 重搜。
- **修复**：`sortBy` 下拉加 `@change="doSearch(false)"`（或把 `sortBy` 加入 watch）。

---

## 四、Batch 3 详细（P1）

### 3.1 日志导出前后端契约对齐

- **现状**：后端 `log.py export_logs(format: str = "excel", filters: dict = {})`；前端 `OperationLogs.vue handleExport` 传平铺 `{user_account, date_from, ...}` 作为 body。需实测确认 body 是否被正确绑定到 `filters`。
- **修复**：前端显式传 `{ format: 'excel', filters: {...} }`，后端同步改 `format` 从 body 读取（或保持 query），消除歧义；核对 `date_from/date_to` 归一化与 list 一致。

### 3.2 风险分布全 0

- **根因**：`review.py preview` 与 `seed.py _generate_seed_reviews` 落库的 ReviewRecord 不写 `task_id`，`_task_risk_dist` 按 `task_id` 过滤查不到；`get_review_task` 用中文键、`_task_risk_dist` 用英文键，不一致。
- **修复**：统一键名；seed 补一个示例 ReviewTask 并关联 seed 记录，使任务页开箱有分布。

---

## 五、审查要点（每批执行）

1. **前后端字段契约**：请求参数名、返回字段名、类型（int/str/bool）是否一致。
2. **参数传递**：GET 用 query、POST 用 body、`responseType: 'blob'` 是否与后端 FileResponse 匹配。
3. **错误分支**：后端 `{"error"}` vs HTTP 异常 vs 前端 catch 是否覆盖。
4. **权限消费**：`require_role`/`require_permission`/`apply_data_scope` 在改动路径上是否仍生效。
5. **回归**：`python -m pytest archive-system/backend/tests/ -v` 不引入新失败。

---

## 六、已知残留（本轮不修，记入后续）

- 哈希链跨进程（Celery worker）分叉 → 需 DB 级串行化（如 SELECT ... FOR UPDATE 链头行）。
- 日志操作类型三分类、`target_id` 全量覆盖（审计六要素补全）。
- SQLite `create_all` 不迁移旧库 → 需 ALTER TABLE ADD COLUMN 迁移脚本。
- 需求功能补全（目录树、日期选择器、锁定按钮、查档人员角色等）属前端批量工作，另立清单。
