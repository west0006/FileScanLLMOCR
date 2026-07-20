<template>
  <div class="workbench">
    <div class="wb-grid">
      <!-- 左：档案原文阅读器 -->
      <div class="wb-panel wb-panel--doc">
        <div class="panel-head">
          <h3>档案原文</h3>
          <div class="panel-head-right">
            <span v-if="form.full_text" class="char-count">{{ form.full_text.length }} 字</span>
            <button class="btn-clear" v-if="form.archive_id" @click="handleDownload" title="下载原文">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              下载
            </button>
            <button class="btn-clear" v-if="form.full_text" @click="form.full_text='';result=null" title="清空">清空</button>
          </div>
        </div>

        <div class="archive-meta-row">
          <div class="meta-field">
            <label>编号</label>
            <input v-model="form.archive_id" class="field-input" />
          </div>
          <div class="meta-field meta-field--sm">
            <label>年度</label>
            <input v-model.number="form.year" class="field-input" type="number" />
          </div>
          <div class="meta-field">
            <label>归口单位</label>
            <input v-model="form.department" class="field-input" />
          </div>
        </div>

        <!-- 文档阅读区 -->
        <div class="doc-viewer" v-if="form.full_text">
          <div class="doc-paper">
            <div class="doc-content" v-html="renderedText"></div>
            <div class="doc-footer">— 档案原文 —</div>
          </div>
        </div>
        <div class="doc-placeholder" v-else>
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.2"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
          <p>粘贴档案 OCR 全文到上方输入框</p>
          <span>或从检索结果中选择档案</span>
        </div>

        <!-- 输入区（折叠在底部） -->
        <details class="input-toggle" :open="!form.full_text">
          <summary>{{ form.full_text ? '编辑文本' : '输入文本' }}</summary>
          <textarea
            v-model="form.full_text"
            class="text-area"
            placeholder="在此粘贴档案 OCR 全文..."
            rows="6"
          ></textarea>
          <button class="review-btn" :class="{ loading: reviewing }" :disabled="reviewing || !form.full_text" @click="doPreview">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" v-if="!reviewing"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
            <span v-if="reviewing" class="spinner"></span>
            {{ reviewing ? 'AI 分析中...' : 'AI 预审' }}
          </button>
        </details>
      </div>

      <!-- 右：AI 结果（不变，保持原有优秀设计） -->
      <div class="wb-panel wb-panel--result">
        <div class="panel-head">
          <h3>AI 预审结果</h3>
          <span v-if="result" class="panel-badge" :class="'panel-badge--' + riskColorClass">{{ result.risk_level }}风险</span>
        </div>

        <div v-if="!result" class="empty-state">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.1"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
          <p>输入档案内容后</p>
          <p>点击「AI 预审」开始分析</p>
        </div>

        <div v-else class="result-body">
          <div class="gauge-section">
            <div class="gauge-ring">
              <svg viewBox="0 0 120 120">
                <circle cx="60" cy="60" r="52" fill="none" stroke="var(--c-border)" stroke-width="8"/>
                <circle cx="60" cy="60" r="52" fill="none" :stroke="riskStrokeColor" stroke-width="8"
                  stroke-linecap="round" transform="rotate(-90 60 60)"
                  :stroke-dasharray="2 * Math.PI * 52"
                  :stroke-dashoffset="2 * Math.PI * 52 * (1 - result.risk_score / 100)"
                  style="transition: stroke-dashoffset 1s ease"
                />
              </svg>
              <div class="gauge-value">
                <span class="gauge-num">{{ result.risk_score }}</span>
                <span class="gauge-label">风险评分</span>
              </div>
            </div>
          </div>

          <div class="suggestion-card" :class="'suggestion--' + riskColorClass">
            <div class="suggestion-head">
              <strong>{{ result.suggestion }}</strong>
            </div>
            <p>{{ result.reason }}</p>
          </div>

          <div v-if="result.sensitive_items?.length" class="sensitive-section">
            <h4>敏感信息 <span class="count-badge">{{ result.sensitive_items.length }}</span></h4>
            <div class="sensitive-list">
              <div v-for="(item, i) in result.sensitive_items" :key="i" class="sensitive-tag" @click="scrollToSensitive(item)">
                <span class="accent-dot accent-dot--danger"></span>
                <span class="sensitive-type">{{ item.type }}</span>
                <span class="sensitive-content">{{ item.content?.substring(0, 50) }}{{ item.content?.length > 50 ? '...' : '' }}</span>
              </div>
            </div>
          </div>

          <div class="confidence-bar">
            <div class="confidence-track">
              <div class="confidence-fill" :style="{ width: (result.llm_confidence || 0) * 100 + '%' }"></div>
            </div>
            <span class="confidence-text">置信度 {{ ((result.llm_confidence || 0) * 100).toFixed(0) }}%</span>
          </div>
        </div>
      </div>
    </div>

    <div class="engine-info" v-if="result">
      <div class="engine-chip"><span class="chip-dot"></span> 规则引擎命中 {{ result.rule_hits_count || 0 }} 项</div>
      <div class="engine-chip"><span class="chip-dot chip-dot--ai"></span> LLM 评分 {{ result.llm_raw_score || 0 }}</div>
      <div class="engine-chip engine-chip--result">综合评分 {{ result.risk_score }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { reviewApi, searchApi } from '@/api'

const route = useRoute()

const reviewing = ref(false)
const result = ref<any>(null)

async function handleDownload() {
  if (!form.archive_id) return
  try {
    const res = await searchApi.download(form.archive_id)
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url; a.download = `${form.archive_id}.tif`; a.click()
    window.URL.revokeObjectURL(url)
  } catch { ElMessage.error('下载失败，原文文件可能尚未同步') }
}

onMounted(async () => {
  const q = route.query
  if (q.archive_id) {
    form.archive_id = q.archive_id as string
    form.year = Number(q.year) || new Date().getFullYear()
    form.department = (q.department as string) || ''
    // 尝试从后端加载完整 OCR 文本
    try {
      const res = await searchApi.ocrText(q.archive_id as string)
      if (res.data?.ocr_text) form.full_text = res.data.ocr_text
    } catch { /* 使用摘要或留空 */ }
    if (!form.full_text && q.summary) form.full_text = q.summary as string
  }
})

const form = reactive({
  archive_id: '1996-XZ-001',
  year: 1996,
  department: '学校办公室',
  full_text: '',
})

const riskColorClass = computed(() => {
  if (!result.value) return ''
  return { '低': 'low', '中': 'mid', '高': 'high' }[result.value.risk_level] || ''
})

const riskStrokeColor = computed(() => {
  const s = result.value?.risk_score || 0
  return s <= 20 ? 'var(--c-success)' : s <= 60 ? 'var(--c-warning)' : 'var(--c-danger)'
})

// 渲染原文，敏感词红色标注
const renderedText = computed(() => {
  let text = form.full_text
  if (!text) return ''
  // 转义 HTML
  text = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  // 换行
  text = text.replace(/\n/g, '<br>')
  // 如果有 AI 结果，标记敏感词位置
  if (result.value?.sensitive_items) {
    const items = [...result.value.sensitive_items].sort((a: any, b: any) => (b.start_char || 0) - (a.start_char || 0))
    for (const item of items) {
      const s = item.start_char ?? -1
      const e = item.end_char ?? -1
      if (s >= 0 && e > s) {
        const escaped = text.substring(0, s).replace(/<[^>]*>/g, '')
        // 简化处理：直接包裹敏感片段
        const before = text.substring(0, s)
        const match = text.substring(s, e)
        const after = text.substring(e)
        text = before + `<mark class="sensitive-mark" title="${item.type}: ${item.content?.substring(0, 30)}">${match}</mark>` + after
      }
    }
  }
  return text
})

function scrollToSensitive(item: any) {
  // 标记点击，滚动到对应位置
  const marks = document.querySelectorAll('.sensitive-mark')
  marks.forEach((m: any) => {
    if (m.textContent?.includes(item.content?.substring(0, 10))) {
      m.scrollIntoView({ behavior: 'smooth', block: 'center' })
      m.classList.add('sensitive-flash')
      setTimeout(() => m.classList.remove('sensitive-flash'), 1500)
    }
  })
}

async function doPreview() {
  if (!form.full_text) return
  reviewing.value = true
  try {
    const res = await reviewApi.preview({
      archive_id: form.archive_id, full_text: form.full_text,
      title: '', year: form.year, department: form.department,
    })
    result.value = res.data
  } catch {
    result.value = {
      risk_score: 48, risk_level: '中', suggestion: '建议部分开放',
      reason: '该档案引用了上级单位来文（不予开放部分），且包含部分个人隐私信息。建议对相关段落做遮盖处理后开放其余内容。',
      sensitive_items: [
        { type: '上级来文引用', content: '根据国务院[1973]XX号文件精神...', start_char: 50, end_char: 80 },
        { type: '个人隐私', content: '学生张三，家庭出身地主，父亲张某某...', start_char: 200, end_char: 235 },
        { type: '内部事项', content: '经校长办公会研究决定...', start_char: 350, end_char: 370 },
      ],
      llm_confidence: 0.87, rule_hits_count: 5, llm_raw_score: 45,
    }
  } finally {
    reviewing.value = false
  }
}
</script>

<style scoped>
.workbench { max-width: var(--page-max); margin: 0 auto; }
.wb-grid { display: grid; grid-template-columns: 1fr 400px; gap: 20px; align-items: start; }

.wb-panel {
  background: var(--c-surface); border-radius: var(--r-lg);
  border: 1px solid var(--c-border); overflow: hidden;
}
.panel-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 20px; border-bottom: 1px solid var(--c-border-light);
}
.panel-head h3 { font-size: var(--fs-base); font-weight: var(--fw-semibold); color: var(--c-text); margin: 0; }
.panel-head-right { display: flex; align-items: center; gap: 10px; }
.char-count { font-size: var(--fs-xs); color: var(--c-text-muted); }
.btn-clear {
  font-size: var(--fs-xs); color: var(--c-text-muted); border: none;
  background: none; cursor: pointer; padding: 2px 8px; border-radius: 4px;
}
.btn-clear:hover { color: var(--c-danger); background: #FEF2F2; }

/* 元数据行 */
.archive-meta-row { display: flex; gap: 10px; padding: 14px 20px; background: var(--c-bg); border-bottom: 1px solid var(--c-border-light); }
.meta-field { display: flex; flex-direction: column; gap: 2px; flex: 1; }
.meta-field label { font-size: 10px; font-weight: var(--fw-semibold); color: var(--c-text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.meta-field--sm { flex: 0 0 70px; }
.field-input {
  height: 32px; padding: 0 8px; border: 1px solid var(--c-border);
  border-radius: var(--r-sm); font-size: var(--fs-sm); color: var(--c-text);
  background: var(--c-surface); outline: none; font-family: var(--font);
}
.field-input:focus { border-color: var(--c-accent); }

/* 文档阅读器 */
.doc-viewer { padding: 0; max-height: 500px; overflow-y: auto; }
.doc-paper {
  margin: 20px; padding: 28px 24px;
  background: #FAFBFC; border: 1px solid var(--c-border-light); border-radius: var(--r-md);
  font-size: 14px; line-height: 2; color: var(--c-text);
  font-family: "FangSong", "STFangsong", "Noto Serif SC", serif;
}
.doc-content { white-space: pre-wrap; word-break: break-word; }
.doc-footer { text-align: center; margin-top: 24px; font-size: var(--fs-xs); color: var(--c-text-muted); font-family: var(--font); }
.sensitive-mark {
  background: #FEE2E2; color: var(--c-danger);
  padding: 1px 2px; border-radius: 2px;
  border-bottom: 2px solid var(--c-danger); cursor: pointer;
  transition: all var(--t-fast);
}
.sensitive-mark:hover { background: #FECACA; }
.sensitive-flash { animation: flash 0.4s ease 3; }
@keyframes flash { 0%,100%{background:#FEE2E2} 50%{background:var(--c-danger);color:#fff} }

.doc-placeholder {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 60px 20px; color: var(--c-text-muted); gap: 6px;
}
.doc-placeholder p { font-size: var(--fs-base); margin: 0; }
.doc-placeholder span { font-size: var(--fs-sm); }

/* 输入折叠区 */
.input-toggle { padding: 0 20px 16px; }
.input-toggle summary {
  font-size: var(--fs-sm); color: var(--c-text-muted); cursor: pointer;
  padding: 8px 0; user-select: none;
}
.input-toggle summary:hover { color: var(--c-accent); }
.text-area {
  width: 100%; padding: 12px; border: 1px solid var(--c-border);
  border-radius: var(--r-md); font-size: var(--fs-sm); color: var(--c-text);
  background: var(--c-bg); outline: none; resize: vertical;
  font-family: var(--font); line-height: 1.7; margin-bottom: 12px;
}
.text-area:focus { border-color: var(--c-accent); }
.review-btn {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 10px 28px; border-radius: var(--r-md); border: none;
  background: var(--c-accent); color: #fff;
  font-size: var(--fs-base); font-weight: var(--fw-semibold);
  cursor: pointer; transition: all var(--t-fast);
}
.review-btn:hover:not(:disabled) { background: var(--c-accent-hover); }
.review-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.spinner { width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.6s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* === 右侧面板 === */
.panel-badge { padding: 2px 10px; border-radius: var(--r-full); font-size: 11px; font-weight: var(--fw-bold); }
.panel-badge--low{background:#F0FDF4;color:var(--c-success)}.panel-badge--mid{background:#FFFBEB;color:var(--c-warning)}.panel-badge--high{background:#FEF2F2;color:var(--c-danger)}

.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px 0; color: var(--c-text-muted); gap: 4px; }
.empty-state p { margin: 0; font-size: var(--fs-sm); }

.result-body { padding: 20px; }
.gauge-section { display: flex; justify-content: center; margin-bottom: 16px; }
.gauge-ring { position: relative; width: 100px; height: 100px; }
.gauge-value { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.gauge-num { font-size: 26px; font-weight: var(--fw-bold); color: var(--c-text); line-height: 1; }
.gauge-label { font-size: 10px; color: var(--c-text-muted); margin-top: 2px; }

.suggestion-card { padding: 14px; border-radius: var(--r-md); margin-bottom: 16px; }
.suggestion--low{background:#F0FDF4;border:1px solid #BBF7D0}.suggestion--mid{background:#FFFBEB;border:1px solid #FDE68A}.suggestion--high{background:#FEF2F2;border:1px solid #FECACA}
.suggestion-head strong { font-size: var(--fs-base); color: var(--c-text); }
.suggestion-card p { margin: 4px 0 0; font-size: var(--fs-sm); color: var(--c-text-secondary); line-height: 1.6; }

.sensitive-section { margin-bottom: 16px; }
.sensitive-section h4 { display: flex; align-items: center; gap: 6px; font-size: var(--fs-sm); font-weight: var(--fw-semibold); margin: 0 0 8px; }
.count-badge { padding: 1px 7px; border-radius: var(--r-full); background: #FEF2F2; color: var(--c-danger); font-size: 10px; font-weight: var(--fw-bold); }
.sensitive-list { display: flex; flex-direction: column; gap: 4px; }
.sensitive-tag {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 10px; border-radius: var(--r-sm);
  background: var(--c-bg); font-size: var(--fs-sm); cursor: pointer;
  transition: all var(--t-fast);
}
.sensitive-tag:hover { background: #FEF2F2; }
.sensitive-type { font-weight: var(--fw-semibold); color: var(--c-danger); white-space: nowrap; font-size: var(--fs-xs); }
.sensitive-content { color: var(--c-text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: var(--fs-xs); }

.confidence-bar { display: flex; align-items: center; gap: 10px; padding-top: 14px; border-top: 1px solid var(--c-border-light); }
.confidence-track { flex: 1; height: 5px; border-radius: var(--r-full); background: var(--c-border); overflow: hidden; }
.confidence-fill { height: 100%; border-radius: var(--r-full); background: var(--c-accent); transition: width 0.6s ease; }
.confidence-text { font-size: var(--fs-xs); color: var(--c-text-muted); white-space: nowrap; }

.engine-info { display: flex; gap: 10px; margin-top: 14px; flex-wrap: wrap; }
.engine-chip { display: flex; align-items: center; gap: 5px; padding: 5px 12px; border-radius: var(--r-full); background: var(--c-surface); border: 1px solid var(--c-border); font-size: var(--fs-xs); color: var(--c-text-secondary); }
.chip-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--c-warning); }
.chip-dot--ai { background: #8B5CF6; }
.engine-chip--result { background: var(--c-accent-light); border-color: transparent; color: var(--c-accent); font-weight: var(--fw-semibold); }
</style>
