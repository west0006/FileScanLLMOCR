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

        <!-- 关联档案 -->
        <div class="info-card" v-if="related.length">
          <h3 class="info-card-title">📎 关联档案</h3>
          <div class="related-list">
            <router-link
              v-for="r in related" :key="r.archive_id"
              :to="'/search/detail/' + r.archive_id"
              class="related-item"
            >
              <div class="related-title">{{ r.title }}</div>
              <div class="related-meta">
                <span>{{ r.year }}</span>
                <span>·</span>
                <span>{{ r.department }}</span>
                <span class="related-reason">{{ r.reason }}</span>
              </div>
            </router-link>
          </div>
        </div>

        <!-- 知识图谱实体 -->
        <div class="info-card" v-if="entitySummary && Object.keys(entitySummary).length">
          <h3 class="info-card-title">🧠 知识图谱</h3>
          <div class="entity-section" v-for="(names, type) in entitySummary" :key="type">
            <div class="entity-type">{{ typeLabel(type) }}</div>
            <div class="entity-tags">
              <span v-for="n in names.slice(0,5)" :key="n" class="entity-tag">{{ n }}</span>
            </div>
          </div>
          <div class="kg-footer" v-if="kgInfo">
            <span>关联档案 {{ kgInfo.related_count }} 件</span><span>·</span><span>实体 {{ kgInfo.entity_count }} 个</span>
          </div>
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
              <div v-if="imagePages.length" class="image-viewer">
                <div class="image-nav">
                  <button :disabled="curPage <= 0" @click="curPage--">&lt; 上一页</button>
                  <span>{{ curPage + 1 }} / {{ imagePages.length }}</span>
                  <button :disabled="curPage >= imagePages.length - 1" @click="curPage++">下一页 &gt;</button>
                </div>
                <div class="image-main" v-if="imagePages[curPage]">
                  <!-- PDF 使用 iframe 在线预览 -->
                  <iframe
                    v-if="imagePages[curPage].format === 'pdf'"
                    :src="'/api/sync/files/' + imagePages[curPage].path"
                    class="archive-pdf"
                    frameborder="0"
                  />
                  <!-- 图像直接显示 -->
                  <img
                    v-else
                    :src="'/api/sync/files/' + imagePages[curPage].path"
                    :alt="imagePages[curPage].filename"
                    @error="onImageError"
                    class="archive-image"
                  />
                </div>
                <div class="image-file-list">
                  <div v-for="(f, i) in imagePages" :key="f.page"
                       :class="['image-file-item', { active: curPage === i }]"
                       @click="curPage = i">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/></svg>
                    <span>{{ f.filename }}</span>
                  </div>
                </div>
              </div>
              <div v-else class="image-placeholder">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
                <p>原文图像暂未就绪</p>
                <span v-if="imageInfo">{{ imageInfo.hint || '支持 TIFF / JPG / PDF 在线浏览' }}</span>
                <span v-else>支持 TIFF / JPG / PDF 在线浏览</span>
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

const imageInfo = ref<any>(null)
const imagePages = ref<any[]>([])
const curPage = ref(0)
const related = ref<any[]>([])
const entitySummary = ref<Record<string, string[]> | null>(null)
const kgInfo = ref<any>(null)

function typeLabel(t: string): string {
  const m: Record<string,string> = {PERSON:'👤 人物',ORG:'🏛️ 机构',DATE:'📅 日期',DOC_ID:'📄 文件编号',EVENT:'📌 事件',LOCATION:'📍 地点'}
  return m[t] || t
}

function onImageError() {
  // 图片加载失败，静默降级
}

onMounted(async () => {
  try {
    const [d, o, img] = await Promise.all([
      searchApi.detail(archiveId),
      searchApi.ocrText(archiveId),
      searchApi.image(archiveId).catch(() => ({ data: null })),
    ])
    archive.value = d.data
    ocrContent.value = o.data.ocr_text || '(暂无 OCR 文本)'
    if (img.data) {
      imageInfo.value = img.data
      imagePages.value = img.data.files || []
    }

    // 关联档案
    const rel = await searchApi.related(archiveId).catch(() => ({ data: { related: [] } }))
    related.value = rel.data.related || []

    // 知识图谱
    const kg = await searchApi.knowledgeGraph(archiveId).catch(() => ({ data: null }))
    if (kg.data) {
      entitySummary.value = kg.data.center_summary || null
      kgInfo.value = kg.data
    }
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

/* 关联档案 */
.related-list { display: flex; flex-direction: column; gap: 2px; }
.related-item {
  display: block; padding: 8px 10px; border-radius: var(--r-sm);
  text-decoration: none; transition: background var(--t-fast);
}
.related-item:hover { background: var(--c-bg); }
.related-title { font-size: var(--fs-sm); color: var(--c-text); font-weight: var(--fw-medium); line-height: 1.4; }
.related-meta { font-size: var(--fs-xs); color: var(--c-text-muted); margin-top: 2px; display: flex; gap: 6px; }
.related-reason { color: var(--c-accent); margin-left: auto; }

/* 知识图谱 */
.entity-section { margin-bottom: 10px; }
.entity-type { font-size: var(--fs-xs); color: var(--c-text-muted); font-weight: var(--fw-semibold); margin-bottom: 4px; }
.entity-tags { display: flex; flex-wrap: wrap; gap: 4px; }
.entity-tag {
  display: inline-block; padding: 2px 8px; border-radius: var(--r-full);
  font-size: 11px; background: var(--c-accent-light); color: var(--c-accent);
  font-weight: var(--fw-medium);
}
.kg-footer { margin-top: 10px; padding-top: 8px; border-top: 1px solid var(--c-border-light); font-size: var(--fs-xs); color: var(--c-text-muted); display: flex; gap: 6px; }

/* 图像查看器 */
.image-viewer { display: flex; flex-direction: column; height: 500px; }
.image-nav {
  display: flex; align-items: center; justify-content: center; gap: 16px;
  padding: 8px 0; border-bottom: 1px solid var(--c-border-light);
}
.image-nav button {
  padding: 4px 12px; border: 1px solid var(--c-border); border-radius: var(--r-sm);
  background: var(--c-surface); color: var(--c-text-secondary); font-size: var(--fs-xs); cursor: pointer;
}
.image-nav button:hover:not(:disabled) { border-color: var(--c-accent); color: var(--c-accent); }
.image-nav button:disabled { opacity: 0.4; cursor: not-allowed; }
.image-nav span { font-size: var(--fs-sm); color: var(--c-text); }
.image-main { flex: 1; display: flex; align-items: center; justify-content: center; overflow: hidden; background: #f5f5f5; }
.archive-image { max-width: 100%; max-height: 100%; object-fit: contain; }
.archive-pdf { width: 100%; height: 100%; min-height: 500px; border: none; }
.image-file-list {
  display: flex; gap: 4px; padding: 8px; overflow-x: auto;
  border-top: 1px solid var(--c-border-light); background: var(--c-bg);
}
.image-file-item {
  display: flex; align-items: center; gap: 4px; padding: 4px 10px;
  border-radius: var(--r-sm); font-size: var(--fs-xs); color: var(--c-text-secondary);
  cursor: pointer; white-space: nowrap; transition: all var(--t-fast);
}
.image-file-item:hover { background: var(--c-border-light); }
.image-file-item.active { background: var(--c-accent); color: #fff; }
</style>
