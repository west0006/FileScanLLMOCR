<template>
  <div class="detail-page">
    <!-- 返回 + 标题 -->
    <div class="detail-top">
      <button class="back-btn" @click="$router.back()">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
        返回
      </button>
      <div class="detail-head">
        <h1 class="detail-title">{{ archive.title || '档案详情' }}</h1>
        <div class="detail-badges">
          <span class="badge badge--plain">{{ archive.category }}</span>
          <span class="badge badge--plain">{{ archive.year }}</span>
        </div>
      </div>
    </div>

    <div class="detail-body">
      <!-- 左侧：元数据 -->
      <div class="detail-side">
        <div class="info-card">
          <h3 class="info-card-title">档案信息</h3>
          <dl class="info-list">
            <div class="info-row"><dt>档案编号</dt><dd>{{ archive.archive_id }}</dd></div>
            <div class="info-row"><dt>归档年度</dt><dd>{{ archive.year }}</dd></div>
            <div class="info-row"><dt>档案门类</dt><dd>{{ archive.category }}</dd></div>
            <div class="info-row"><dt>归口单位</dt><dd>{{ archive.department }}</dd></div>
            <div class="info-row"><dt>保管期限</dt><dd>{{ archive.retention_period || '永久' }}</dd></div>
            <div class="info-row"><dt>密级</dt><dd>{{ archive.security_level || '内部' }}</dd></div>
            <div class="info-row"><dt>卷内文件</dt><dd>{{ archive.file_count || 0 }} 件</dd></div>
          </dl>
        </div>
      </div>

      <!-- 右侧：原文 -->
      <div class="detail-main">
        <div class="view-card">
          <div class="view-tabs">
            <button :class="['view-tab', { active: viewMode === 'image' }]" @click="viewMode = 'image'">原文浏览</button>
            <button :class="['view-tab', { active: viewMode === 'ocr' }]" @click="viewMode = 'ocr'">OCR 文本</button>
            <button :class="['view-tab', { active: viewMode === 'compare' }]" @click="viewMode = 'compare'">对照浏览</button>
          </div>

          <div class="view-content">
            <div v-if="viewMode === 'image'" class="image-panel">
              <div class="image-placeholder">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
                <p>原文图像区域</p>
                <span>支持 TIFF / JPG / PDF 在线浏览</span>
              </div>
            </div>
            <div v-else-if="viewMode === 'ocr'" class="ocr-panel">
              <pre class="ocr-text">{{ ocrContent }}</pre>
            </div>
            <div v-else class="compare-panel">
              <div class="compare-col">
                <div class="compare-label">原文图像</div>
                <div class="image-placeholder"><p>图像区域</p></div>
              </div>
              <div class="compare-divider"></div>
              <div class="compare-col">
                <div class="compare-label">OCR 识别文本</div>
                <pre class="ocr-text">{{ ocrContent }}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { searchApi } from '@/api'

const route = useRoute()
const archiveId = route.params.id as string
const viewMode = ref('image')
const archive = ref<any>({})
const ocrContent = ref('')

onMounted(async () => {
  try {
    const [d, o] = await Promise.all([searchApi.detail(archiveId), searchApi.ocrText(archiveId)])
    archive.value = d.data
    ocrContent.value = o.data.ocr_text || '(暂无 OCR 文本)'
  } catch {
    archive.value = { archive_id: archiveId, title: '示例档案', year: 1996, category: '行政档案', department: '学校办公室', retention_period: '永久', security_level: '内部', file_count: 3 }
    ocrContent.value = 'OCR 文本加载中...'
  }
})
</script>

<style scoped>
.detail-page { max-width: var(--page-max); margin: 0 auto; }
.detail-top { margin-bottom: 24px; }
.back-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 12px; border-radius: var(--r-sm); border: none;
  background: transparent; color: var(--c-text-secondary);
  font-size: var(--fs-sm); cursor: pointer; margin-bottom: 12px;
  transition: all var(--t-fast);
}
.back-btn:hover { background: var(--c-bg); color: var(--c-accent); }
.detail-head { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.detail-title { font-size: var(--fs-2xl); font-weight: var(--fw-bold); color: var(--c-text); margin: 0; }
.badge--plain { padding: 3px 10px; border-radius: var(--r-full); font-size: 11px; font-weight: var(--fw-semibold); background: var(--c-bg); color: var(--c-text-secondary); }

.detail-body { display: flex; gap: 24px; align-items: flex-start; }

/* 左侧信息卡 */
.detail-side { width: 280px; flex-shrink: 0; }
.info-card {
  background: var(--c-surface); border-radius: var(--r-lg);
  border: 1px solid var(--c-border); padding: 20px;
}
.info-card-title {
  font-size: var(--fs-base); font-weight: var(--fw-semibold);
  color: var(--c-text); margin: 0 0 16px; padding-bottom: 12px;
  border-bottom: 1px solid var(--c-border-light);
}
.info-list { margin: 0; }
.info-row {
  display: flex; justify-content: space-between; align-items: baseline;
  padding: 8px 0; border-bottom: 1px solid var(--c-border-light);
}
.info-row:last-child { border-bottom: none; }
.info-row dt { font-size: var(--fs-sm); color: var(--c-text-muted); }
.info-row dd { font-size: var(--fs-sm); color: var(--c-text); font-weight: var(--fw-medium); text-align: right; max-width: 60%; word-break: break-all; }

/* 右侧主区域 */
.detail-main { flex: 1; min-width: 0; }
.view-card {
  background: var(--c-surface); border-radius: var(--r-lg);
  border: 1px solid var(--c-border); overflow: hidden;
}
.view-tabs {
  display: flex; border-bottom: 1px solid var(--c-border-light);
  padding: 0 20px; background: var(--c-bg);
}
.view-tab {
  padding: 14px 20px; border: none; background: transparent;
  color: var(--c-text-secondary); font-size: var(--fs-sm);
  font-weight: var(--fw-medium); cursor: pointer;
  border-bottom: 2px solid transparent; transition: all var(--t-fast);
}
.view-tab.active { color: var(--c-accent); border-bottom-color: var(--c-accent); }
.view-content { min-height: 500px; }

.image-placeholder {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  height: 100%; min-height: 400px; color: var(--c-text-muted); gap: 8px;
}
.image-placeholder p { font-size: var(--fs-lg); margin: 0; }
.image-placeholder span { font-size: var(--fs-sm); }

.ocr-panel { padding: 20px; }
.ocr-text {
  font-size: 14px; line-height: 1.8; color: var(--c-text);
  white-space: pre-wrap; margin: 0; font-family: var(--font);
}

.compare-panel { display: flex; min-height: 500px; }
.compare-col { flex: 1; padding: 16px; overflow: auto; }
.compare-label {
  font-size: var(--fs-xs); font-weight: var(--fw-semibold); color: var(--c-text-muted);
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px;
}
.compare-divider { width: 1px; background: var(--c-border); flex-shrink: 0; }
</style>
