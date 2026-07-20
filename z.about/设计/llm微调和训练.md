# AI 微调与训练 —— 完整实战方案

## 一、全景图：两条 AI 管线

```
┌──────────────────────────────────────────────────────────────────┐
│                    你的 AI 工作全景                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  管线一：OCR 文本识别                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────────────┐  │
│  │ 档案扫描件 │ → │ 图像预处理 │ → │ OCR 识别  │ → │ 全文索引库  │  │
│  │ (TIFF/JPG)│    │ 去噪增强  │    │ PaddleOCR │    │ES 入库     │  │
│  └──────────┘    └──────────┘    └──────────┘    └────────────┘  │
│                       ↑ 你的微调点                                │
│                                                                  │
│  管线二：AI 开放审核                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────────────┐  │
│  │ OCR 文本  │ → │ 敏感信息  │ → │ 风险评分  │ → │ 开放建议    │  │
│  │ + 元数据  │    │ 双引擎识别│    │ 综合打分  │    │ + 理由说明  │  │
│  └──────────┘    └──────────┘    └──────────┘    └────────────┘  │
│                  ↑ LLM + 规则引擎            ↑ 你的 LoRA 微调点   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 二、硬件环境 —— 你训练和推理的物理底座

```
机型：攀升坤龙 D-F3011-D（液冷一体机）
├── CPU：鲲鹏 920S（ARM 架构，32 核，2.6GHz）
├── NPU：昇腾 310P × 2（Atlas 300I Duo 卡 × 2）
├── 内存：64GB 或 128GB DDR4
├── 存储：按预算配置（建议 ≥2TB SSD）
├── 系统：openEuler / 麒麟 / Ubuntu（ARM 版）
└── 散热：全液冷，7×24h 满载无降频

关键约束：
- ARM 架构（aarch64）→ 软件包需 ARM 版本
- 昇腾 NPU → 需 CANN（Ascend 异构计算架构）+ MindSpore 或 PaddlePaddle 昇腾版
- 32B 模型 INT8 量化后可在双卡上推理
- LoRA 微调：32B + INT8 + LoRA 可在单卡上跑动
```

---

## 三、管线一：OCR 微调（PaddleOCR）

### 3.1 为什么需要微调？

通用 PaddleOCR 模型在标准印刷体上已经很好（~97%），但中南财经政法大学的档案存在以下特殊挑战：

| 挑战 | 通用模型表现 | 微调后期望 |
|------|-------------|-----------|
| 1950-1980 年代手写体（钢笔/毛笔） | 60-70% | ≥85% |
| 泛黄纸张 + 墨水褪色 | 70-80% | ≥90% |
| 表格混排（名册类：姓名/性别/年龄/籍贯） | 结构丢失 | 结构化输出 |
| 印章覆盖文字 | 识别失败 | 部分恢复 |
| 繁体字 / 异体字 | 识别错误 | 映射到简体 |
| 老旧印刷字体（铅字印刷） | 80-85% | ≥95% |

工作区 `static/名册/` 下的 13 张图就是这些难点的典型代表：

```
模糊名册系列    → 泛黄、低分辨率
手写名册系列    → 手写体（钢笔/毛笔），不同笔迹风格
有遮挡名册      → 印章覆盖
模糊的成绩单    → 铅字印刷 + 手写混合
稍清晰名册示例  → 印刷体，但表格密集
```

### 3.2 微调流程（完整步骤）

#### 第一步：数据准备与标注

```
数据收集清单：
├── 印刷体档案：200 页（不同年代：1950s / 1960s / 1970s / 1980s / 1990s）
├── 手写体档案：200 页（成绩单、名册、手写报告、批示件）
├── 表格档案：  100 页（名册、统计表、工资表）
├── 印章覆盖：   50 页
├── 破损/模糊：  50 页
└── 总计：约 600 页

标注工具：PPOCRLabel（PaddleOCR 官方标注工具）
标注内容：
  - 文本检测框（四点坐标）
  - 文本内容转录
  - 特殊标记：[illegible] 不可识别、[seal] 印章区域、[table] 表格区域
```

标注格式（PPOCRLabel 导出格式）：
```
Label.txt 示例：
path/to/image1.jpg	[{"transcription": "中南财经大学", "points": [[12,34],[156,34],[156,68],[12,68]]}, ...]
path/to/image2.jpg	[{"transcription": "一九七三年招生工作总结", "points": [[...]]}, ...]
```

**工作量估算**：600 页 × 平均 15 个文本框 = 9000 个标注框。一个熟练标注员约 2-3 分钟/框 → 约 60-90 人天。建议 2 人同时标注，约 30-45 个工作日。

#### 第二步：图像预处理管线

在送入 OCR 之前，先过预处理管线：

```python
# 预处理管线（需针对档案特征调参）
import cv2
import numpy as np

def preprocess_archive_image(img_path):
    img = cv2.imread(img_path)

    # 1. 灰度化（如果是彩色扫描）
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 2. 去噪（针对档案扫描特有的椒盐噪声和底纹）
    denoised = cv2.fastNlMeansDenoising(gray, h=10)

    # 3. 自适应对比度增强（CLAHE），解决泛黄/褪色问题
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(denoised)

    # 4. 倾斜校正（基于文本行检测或霍夫变换）
    angle = detect_skew(enhanced)  # 自定义函数
    rotated = rotate_image(enhanced, angle)

    # 5. 二值化（自适应阈值，对光照不均的扫描件效果好）
    binary = cv2.adaptiveThreshold(
        rotated, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )

    # 6.（可选）超分辨率重建——针对极低分辨率模糊名册
    # 使用 Real-ESRGAN 或 BSRGAN 提升分辨率

    return binary
```

#### 第三步：模型微调

PaddleOCR 的识别模型基于 CRNN + CTC 或 SVTR 架构。微调策略：

```yaml
# PaddleOCR 微调配置要点 (config.yml)
Global:
  use_gpu: true
  epoch_num: 100
  log_smooth_window: 20
  print_batch_step: 10
  save_model_dir: ./output/rec_archive/
  save_epoch_step: 5
  eval_batch_step: [0, 500]
  pretrained_model: ./pretrain/rec_mv3_none_bilstm_ctc_v2.0_train/best_accuracy

Optimizer:
  name: Adam
  beta1: 0.9
  beta2: 0.999
  lr:
    name: Cosine
    learning_rate: 0.001        # 微调用较小学习率
    warmup_epoch: 5

Architecture:
  model_type: rec
  algorithm: SVTR_LCNet         # SVTR 对手写体效果好
  Transform: null
  Backbone:
    name: PPLCNetV3             # 轻量级，昇腾友好
    scale: 0.95
  Neck:
    name: SequenceEncoder
    encoder_type: svtr          # SVTR encoder 捕获长距离依赖
  Head:
    name: CTCHead
    fc_decay: 0.0004

Train:
  dataset:
    name: SimpleDataSet
    data_dir: ./train_data/archive/
    label_file_list: ["./train_data/archive/train.txt"]
    transforms:
      - DecodeImage:
          img_mode: BGR
          channel_first: false
      - CTCLabelEncode: null
      - RecResizeImg:
          image_shape: [3, 48, 320]  # 高度 48 适合中文
      - KeepKeys:
          keep_keys: ['image', 'label', 'length']
  loader:
    shuffle: true
    batch_size_per_card: 64
    drop_last: true
    num_workers: 4

Eval:
  dataset:
    name: SimpleDataSet
    data_dir: ./train_data/archive/
    label_file_list: ["./train_data/archive/val.txt"]
```

**微调技巧**：

| 技巧 | 说明 |
|------|------|
| 分阶段训练 | 先用印刷体训练 50 epoch → 冻结 backbone 前几层 → 加入手写体再训 50 epoch |
| 数据增强 | 随机模糊、随机亮度/对比度（模拟泛黄）、随机旋转 ±3°、随机缩放 |
| 自定义词典 | 注入档案术语（"案卷""归口""全宗""卷内"）、人名、机构名到字典 |
| 昇腾适配 | 使用 `paddlepaddle-aarch64` + `paddle-cann` 插件，确保 NPU 加速 |

#### 第四步：后处理与结构化输出

```
OCR 原始输出：
"姓名：张三性别：男年龄：22籍贯：湖北武汉"

后处理 → 结构化：
{
  "name": "张三",
  "gender": "男",
  "age": 22,
  "hometown": "湖北武汉"
}
```

对于表格类档案（名册），需要额外的**表格结构识别模型**（PaddleOCR 的 `table_master` 或 `SLANet`），输出 HTML 或 JSON 格式的表格结构。

---

## 四、管线二：LLM 微调——开放审核模型

这是你工作的重中之重，也是最需要攻克的难点。

### 4.1 方案书中的定位

```
方案书关键段落（6.5.2 节）：
"基于大语言模型进行领域微调，训练模型识别学校提供的判别规则。"
"模型推理过程在本地工作站上完成，无需连接外部网络。"

附录术语表：
"LoRA：Low-Rank Adaptation，一种参数高效的 LLM 微调方法。
本方案使用 LoRA 对大语言模型进行档案领域适应性微调。"
```

### 4.2 基座模型选择

```
方案一（优先）：DeepSeek-R1-Distill-Qwen-32B
  优势：推理能力强（R1 蒸馏），中文好，开源可商用
  昇腾适配：需 MindIE 或 vLLM-ascend 推理框架

方案二（备选）：Qwen3-32B-Instruct
  优势：原生昇腾适配（MindSpore），指令遵循好
  风险：可能更依赖 prompt 而非微调
```

### 4.3 微调架构：LoRA

**为什么 LoRA？**

全量微调 32B 模型需要 ~128GB 显存，昇腾 310P 单卡只有 24GB。LoRA 只训练低秩适配器，显存需求下降到 ~20-30GB，双卡可以跑。

```
LoRA 原理（简化版）：
原始权重 W (frozen) + 低秩增量 ΔW = A × B

W 维度: [4096, 4096]  → 16M 参数（冻结）
A 维度: [4096, 16]     → 65K 参数（训练）
B 维度: [16, 4096]     → 65K 参数（训练）
─────────────────────────────────
总训练参数: 0.8%       → 仅 ~260M 参数可训
显存节省: ~90%
```

### 4.4 微调执行方案

#### 步骤一：训练数据构建（决定天花板）

这是整个项目最重要、最耗时的一步。你需要构建 **审核标注数据集**。

**数据来源**：

```
源1：中南财经大学 1996 年审核工作用表（工作区已有）
  └── 9 个归口单位（保卫部、档案馆、工会、纪委、人事处、统战部、学校办公室、组织部 + 汇总表）
  └── 这些是已经人工审核过的档案！是黄金训练数据

源2：按件整理的党群档案 + 行政档案 Excel（工作区已有）
  └── 包含档案元数据 + 原文路径

源3：档案控制使用范围文档（工作区已有）
  └── 9 类不予开放情形 + 4 类校外开放范围
  └── 这是标注标准
```

**标注数据格式**（每条一个 JSON）：

```json
{
  "id": "train-001",
  "archive_id": "1973-XZ-032-011",
  "title": "一九七三年武汉地区招生工作总结",
  "full_text": "根据国务院有关招生工作的指示...（档案OCR全文，可能几千字）...",
  "metadata": {
    "year": 1973,
    "category": "行政档案",
    "department": "学校办公室",
    "security_level": "内部"
  },
  "labels": {
    "risk_score": 35,
    "risk_level": "中",
    "sensitive_items": [
      {
        "type": "上级来文引用",
        "content": "国务院有关招生工作指示",
        "start_char": 2,
        "end_char": 13,
        "rule_ref": "一(七)所有上级来文和外收文"
      },
      {
        "type": "个人隐私",
        "content": "学生张三，家庭出身地主...",
        "start_char": 450,
        "end_char": 478,
        "rule_ref": "一(五)涉及个人隐私的"
      }
    ],
    "suggestion": "建议部分开放",
    "reason": "档案引用了国务院上级来文（不开放部分），且包含学生家庭出身等个人隐私信息，其余招生工作总结内容可开放",
    "reviewer_notes": "需对涉密上级来文段落做遮盖处理后开放"
  }
}
```

**数据构建策略**：

```
阶段 A：利用已有审核表（第 1-3 周）
  1. 解析 9 个归口单位的 1996 年审核工作用表 .xls
     提取：档案编号 + 题名 + 原文路径 + 人工审核结论
  2. 匹配对应的档案全文（从 OCR 结果或原始文本获取）
  3. 由标注人员在原文中标注敏感片段的具体位置
  4. 估算产出：50-80 条高质量标注

阶段 B：基于敏感词库自动标注 + 人工校验（第 3-6 周）
  1. 用 400+ 敏感词库对档案全文跑关键词匹配
  2. 命中的档案标记为"候选敏感"
  3. 标注员逐条确认：是真正的敏感（真阳性）还是误报（假阳性）
  4. 对命中位置进行精细化标注
  5. 估算产出：200-300 条

阶段 C：主动学习采样 + 人工标注（第 6-10 周）
  1. 用初版模型预测剩余未标注档案
  2. 选择模型最不确定的样本（confidence < 0.7）优先标注
  3. 估算产出：200-300 条

总计目标：500-800 条高质量训练数据
```

#### 步骤二：训练脚本（基于 LLaMA-Factory）

LLaMA-Factory 是目前最成熟的 LLM 微调框架，支持 Qwen/DeepSeek + LoRA + 昇腾。

```bash
# 环境准备（ARM + 昇腾）
# 安装 CANN (Ascend 异构计算框架)
# 安装 torch-npu / mindspore

pip install llamafactory
```

训练配置（`train_config.yaml`）：

```yaml
### model
model_name_or_path: /data/models/DeepSeek-R1-Distill-Qwen-32B
trust_remote_code: true

### method
stage: sft                          # 监督微调
do_train: true
finetuning_type: lora
lora_target: all                    # 或 [q_proj, k_proj, v_proj, o_proj]
lora_rank: 32                       # rank 越高容量越大，16-64 之间
lora_alpha: 64                      # 缩放因子，通常 = 2×rank
lora_dropout: 0.1

### dataset
dataset: archive_review             # 自定义数据集名
template: qwen                      # Qwen 系对话模板
cutoff_len: 4096                    # 档案文本较长，需要较大上下文
overwrite_cache: true
preprocessing_num_workers: 8

### output
output_dir: /data/models/lora-archive-review-v1
logging_steps: 10
save_steps: 200
plot_loss: true

### train
per_device_train_batch_size: 2      # 32B 模型 LoRA，双卡，batch=2
gradient_accumulation_steps: 8      # 等效 batch = 2×2×8 = 32
learning_rate: 2.0e-4
num_train_epochs: 3
lr_scheduler_type: cosine
warmup_ratio: 0.1
bf16: false
fp16: false
use_npu: true                       # 昇腾 NPU

### eval
val_size: 0.1
per_device_eval_batch_size: 2
eval_steps: 200
```

#### 步骤三：训练数据注册

在 LLaMA-Factory 的 `data/dataset_info.json` 中注册：

```json
{
  "archive_review": {
    "file_name": "/data/train/archive_review_train.json",
    "formatting": "sharegpt",
    "columns": {
      "messages": "messages"
    }
  }
}
```

训练数据格式（ShareGPT 格式，适配审核任务）：

```json
[
  {
    "messages": [
      {
        "role": "system",
        "content": "你是中南财经政法大学档案馆的档案开放审核专家。你的任务是审核档案全文，判断是否可以向社会开放。\n\n审核依据：\n1. 涉及党和国家秘密的 → 不予开放\n2. 涉及未结论的重大问题/事件 → 不予开放\n3. 涉及学校内部不对外公开事项的 → 不予开放\n4. 涉及知识产权 → 不予开放\n5. 涉及个人隐私（身份证号、家庭出身、成绩、健康等） → 不予开放或部分开放\n6. 上级来文和外收文 → 不予开放\n7. 捐献档案未得权属人同意 → 不予开放\n\n请输出 JSON 格式的审核结果，包含 risk_score(0-100)、risk_level(低/中/高)、sensitive_items、suggestion、reason。"
      },
      {
        "role": "user",
        "content": "请审核以下档案：\n\n档案编号：1973-XZ-032-011\n题名：一九七三年武汉地区招生工作总结\n归口单位：学校办公室\n归档年度：1973\n\n全文内容：\n（此处放入档案 OCR 全文）"
      },
      {
        "role": "assistant",
        "content": "{\n  \"risk_score\": 35,\n  \"risk_level\": \"中\",\n  \"sensitive_items\": [\n    {\"type\": \"上级来文引用\", \"content\": \"国务院有关招生工作指示\", \"start_char\": 2, \"end_char\": 13},\n    {\"type\": \"个人隐私\", \"content\": \"张三，家庭出身地主。父亲张某某...\", \"start_char\": 450, \"end_char\": 490}\n  ],\n  \"suggestion\": \"建议部分开放\",\n  \"reason\": \"档案引用了国务院上级来文（属于不开放范围），且包含学生家庭出身等个人隐私信息，需对相关段落做遮盖处理。其余招生工作总结内容不涉及敏感信息，可以开放。\",\n  \"confidence\": 0.89\n}"
      }
    ]
  }
]
```

#### 步骤四：启动训练

```bash
# 在昇腾一体机上执行
llamafactory-cli train train_config.yaml

# 训练监控
# - Loss 收敛：预期 3 epoch 后 loss 降到 0.5 以下
# - 显存监控：npu-smi info 查看 NPU 使用率
```

### 4.5 规则引擎 + LLM 双引擎融合

光靠 LLM 不够，方案书明确要求"审核规则引擎"作为辅助。正确的架构是：

```
┌──────────────────────────────────────────────┐
│              双引擎审核架构                    │
├──────────────────────────────────────────────┤
│                                              │
│  档案全文 ──┬── 规则引擎（快速扫描层）         │
│            │   ├── 敏感词匹配（400+ 词）       │
│            │   ├── 正则规则（身份证/电话/...） │
│            │   ├── 模式规则（上级来文格式）     │
│            │   └── 输出：命中词列表 + 位置      │
│            │                                  │
│            └── LLM 语义引擎（深度理解层）      │
│                ├── 上下文理解（是真的敏感？）    │
│                ├── 意图分析（恶意还是引用？）    │
│                ├── 整体风险评分                  │
│                └── 输出：风险评分 + 建议 + 理由  │
│                                              │
│  融合层：                                     │
│    规则命中数 × 权重 + LLM 风险评分 × 权重     │
│    → 最终风险评分 + 等级 + 建议                │
│                                              │
└──────────────────────────────────────────────┘
```

融合逻辑的代码骨架：

```python
def hybrid_review(full_text: str, llm_client, rule_engine) -> dict:
    # 第一层：规则引擎快速扫描
    rule_hits = rule_engine.scan(full_text)
    # rule_hits = [{"word": "文革", "category": "政治运动", "count": 3}, ...]

    # 第二层：LLM 语义审核
    llm_result = llm_client.review(full_text)
    # llm_result = {"risk_score": 35, "sensitive_items": [...], ...}

    # 第三层：融合
    rule_risk = calculate_rule_risk(rule_hits)
    # 规则命中 0 个 → 0 分，1-3 个 → 20 分，4-8 个 → 40 分，>8 个 → 60 分

    final_score = 0.4 * rule_risk + 0.6 * llm_result["risk_score"]

    # 风险等级映射（与方案书一致）
    if final_score <= 20:
        level = "低"
        suggestion = "建议开放"
    elif final_score <= 60:
        level = "中"
        suggestion = "建议人工重点关注"
    else:
        level = "高"
        suggestion = "建议延期开放或不予开放"

    return {
        "risk_score": final_score,
        "risk_level": level,
        "sensitive_items": deduplicate(rule_hits + llm_result["sensitive_items"]),
        "suggestion": suggestion,
        "reason": llm_result.get("reason", ""),
        "rule_hits": rule_hits,
        "llm_confidence": llm_result.get("confidence", 0)
    }
```

---

## 五、语义检索中的 LLM 应用（不需微调，需 Prompt Engineering）

### 5.1 Query Understanding 模块

用户输入自然语言查询 → LLM 解析意图 → 生成 ES 查询 DSL：

```python
QUERY_UNDERSTANDING_PROMPT = """你是档案检索意图分析助手。用户输入自然语言查询，你分析并输出 JSON。

用户查询："{query}"

请分析：
1. intent: 查询意图类型（精确查找某档案 / 主题研究 / 人员查找 / 统计汇总）
2. entities: 提取的实体 [{name, type}]  type ∈ [PERSON, ORG, YEAR, EVENT, DOC_TYPE]
3. keywords: 核心检索关键词列表
4. synonyms: 同义词扩展（如 "学生"→"学籍"→"在校生"）
5. time_range: 时间范围（如果有），格式 [start_year, end_year] 或 null
6. suggest_fields: 建议重点检索的 ES 字段 ["title^2", "full_text", "department"]

仅输出 JSON，不要其他内容。"""

# 调用 LLM 后，用解析结果构造 Elasticsearch bool query
```

这个模块用 **base model（不需微调）+ 好的 Prompt** 就够了，因为它本质是意图分类和实体抽取，不需要专业领域知识。

---

## 六、评估体系

### 6.1 OCR 评估

```python
# 字符准确率（Character Accuracy）
def char_accuracy(pred_text: str, gt_text: str) -> float:
    correct = sum(1 for p, g in zip(pred_text, gt_text) if p == g)
    return correct / max(len(pred_text), len(gt_text))

# 编辑距离归一化
from Levenshtein import distance
def norm_edit_distance(pred, gt):
    return distance(pred, gt) / max(len(pred), len(gt))

# 评估维度
评估维度          目标    测试方法
印刷体准确率      ≥99%    随机抽样 200 页，人工校对
手写体准确率      ≥85%    随机抽样 100 页，人工校对
复杂版式准确率    ≥90%    含表格/印章 50 页
```

### 6.2 AI 审核评估

```python
# 混淆矩阵
真实\预测    建议开放    建议部分开放    建议延期/不开放
建议开放       TP                       FN
建议部分开放               TP
建议延期                            TP

# 核心指标
准确率 = (TP_开放 + TP_部分 + TP_延期) / 总数    → 目标 ≥85%
召回率(敏感) = 真实敏感中被 AI 识别为敏感的      → 目标 ≥90%
精确率(敏感) = AI 标敏感中真正敏感的             → 目标 ≥80%
F1 = 2×召回×精确 / (召回+精确)                   → 目标 ≥85%
```

---

## 七、持续迭代闭环

```
┌─────────────────────────────────────────────────────┐
│              持续优化飞轮                              │
├─────────────────────────────────────────────────────┤
│                                                     │
│   ① 系统上线 → ② 人工复核发现 AI 错判 →             │
│   ③ 错判样本入库 → ④ 每月用新数据重训 →              │
│   ⑤ 模型更新部署 → ⑥ 准确率提升 → ① 循环            │
│                                                     │
│   主动学习加速环：                                    │
│   - 对 AI confidence < 0.7 的样本优先送人工标注       │
│   - 每批 50 条高价值样本重新训练                      │
│   - 预期：6 个月内准确率从 85% 提升到 92%+            │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 八、120 天时间线 —— AI 工作分解

| 周次 | 阶段 | AI 工作 |
|------|------|---------|
| 1-3 | 需求调研 | 收集档案样本（扫不同年代/门类）；分析 1996 年审核工作用表结构 |
| 4-6 | 数据标注 I | OCR 样本标注（200 页）；解析审核表 Excel → 提取训练数据雏形 |
| 7-10 | 数据标注 II | 基于敏感词库自动标注 + 人工校验；LLM 训练数据达到 300 条 |
| 9-12 | OCR 微调 | 第一轮 PaddleOCR fine-tune；在验证集上评估 |
| 11-14 | LLM 微调 | 第一轮 LoRA SFT；Baseline 评估；Prompt 优化 |
| 13-16 | 模型联调 | OCR + LLM + 规则引擎集成；端到端测试 |
| 15-18 | 效果优化 | 第二/三轮迭代微调；达到验收指标 |
| 17-20 | 部署上线 | 模型导出（ONNX/MindIR）、量化、部署到昇腾一体机 |

**关键建议**：标注工作（第 4-10 周）和开发工作（前后端 API）可以并行——你写 API 时后端接口已经定义好，标注员独立标注数据。不要等开发完成才开始标注，那是最大风险。

---

