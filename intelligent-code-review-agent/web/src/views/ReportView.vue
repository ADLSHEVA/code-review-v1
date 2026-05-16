<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useScanStore } from '@/stores/scan'
import type { Comment } from '@/services/api'

const { t } = useI18n()
const route = useRoute()
const store = useScanStore()
const activeSeverity = ref<string | null>(null)
const activeFile = ref<string | null>(null)
const selectedComment = ref<Comment | null>(null)

const reportId = computed(() => route.params.id as string)

onMounted(async () => {
  await store.loadReport(reportId.value)
})

const filteredComments = computed(() => {
  let comments = store.currentReport?.comments || []
  if (activeSeverity.value) {
    comments = comments.filter(c => c.severity === activeSeverity.value)
  }
  if (activeFile.value) {
    comments = comments.filter(c => c.file_path === activeFile.value)
  }
  return comments
})

function confidenceColor(conf: number) {
  if (conf >= 0.9) return 'var(--success)'
  if (conf >= 0.7) return 'var(--warning)'
  return 'var(--critical)'
}
</script>

<template>
  <div v-if="store.currentReport" class="report-page">
    <div class="report-header">
      <h2>{{ t('report.title') }} <span class="report-id">#{{ reportId }}</span></h2>
      <p class="repo-path">{{ store.currentReport.repo_path }}</p>
      <p class="report-date">{{ new Date(store.currentReport.created_at).toLocaleString() }}</p>
    </div>

    <div class="summary-cards">
      <div class="summary-card critical" @click="activeSeverity = activeSeverity === 'critical' ? null : 'critical'">
        <span class="count">{{ store.currentReport.stats.critical }}</span>
        <span class="label">{{ t('report.critical') }}</span>
      </div>
      <div class="summary-card error" @click="activeSeverity = activeSeverity === 'error' ? null : 'error'">
        <span class="count">{{ store.currentReport.stats.error }}</span>
        <span class="label">{{ t('report.error') }}</span>
      </div>
      <div class="summary-card warning" @click="activeSeverity = activeSeverity === 'warning' ? null : 'warning'">
        <span class="count">{{ store.currentReport.stats.warning }}</span>
        <span class="label">{{ t('report.warning') }}</span>
      </div>
      <div class="summary-card info" @click="activeSeverity = activeSeverity === 'info' ? null : 'info'">
        <span class="count">{{ store.currentReport.stats.info }}</span>
        <span class="label">{{ t('report.info') }}</span>
      </div>
    </div>

    <div class="report-body">
      <aside class="file-list">
        <h3>{{ t('report.files') }} ({{ store.filesWithIssues.length }})</h3>
        <div class="file-filters">
          <button :class="{ active: !activeFile }" @click="activeFile = null">{{ t('report.all') }}</button>
        </div>
        <div
          v-for="f in store.filesWithIssues"
          :key="f.path"
          :class="['file-item', { active: activeFile === f.path }]"
          @click="activeFile = activeFile === f.path ? null : f.path"
        >
          <span class="file-name">{{ f.path.split('/').pop() }}</span>
          <span class="file-counts">
            <span v-if="f.critical" class="badge critical">{{ f.critical }}</span>
            <span v-if="f.error" class="badge error">{{ f.error }}</span>
            <span v-if="f.warning" class="badge warning">{{ f.warning }}</span>
            <span v-if="f.info" class="badge info">{{ f.info }}</span>
          </span>
        </div>
      </aside>

      <div class="comments-panel">
        <div class="panel-header">
          <h3>{{ t('report.issues') }} ({{ filteredComments.length }})</h3>
          <div class="filter-tags">
            <span v-if="activeSeverity" class="filter-tag" @click="activeSeverity = null">
              {{ activeSeverity }} ✕
            </span>
            <span v-if="activeFile" class="filter-tag" @click="activeFile = null">
              {{ activeFile.split('/').pop() }} ✕
            </span>
          </div>
        </div>

        <div class="comment-list">
          <div
            v-for="(c, i) in filteredComments"
            :key="i"
            :class="['comment-card', { selected: selectedComment === c }]"
            @click="selectedComment = selectedComment === c ? null : c"
          >
            <div class="comment-header">
              <span :class="['severity-badge', c.severity]">{{ c.severity }}</span>
              <span class="comment-category">{{ c.category }}</span>
              <span class="comment-confidence" :style="{ color: confidenceColor(c.confidence) }">
                {{ Math.round(c.confidence * 100) }}%
              </span>
            </div>
            <div class="comment-title">{{ c.title }}</div>
            <div class="comment-location">
              <span class="file">{{ c.file_path }}</span>
              <span class="line">:{{ c.line_start }}</span>
            </div>

            <div v-if="selectedComment === c" class="comment-detail">
              <div class="detail-section">
                <h4>{{ t('report.description') }}</h4>
                <p>{{ c.description }}</p>
              </div>
              <div v-if="c.suggestion" class="detail-section">
                <h4>{{ t('report.suggestion') }}</h4>
                <pre class="suggestion-code">{{ c.suggestion }}</pre>
              </div>
            </div>
          </div>

          <div v-if="filteredComments.length === 0" class="empty">
            {{ t('report.noIssues') }}
          </div>
        </div>
      </div>
    </div>
  </div>

  <div v-else-if="store.loading" class="loading">
    {{ t('report.loading') }}
  </div>
</template>

<style scoped>
.report-page {
  max-width: 1400px;
}

.report-header {
  margin-bottom: 1.5rem;
}

.report-header h2 {
  font-size: 1.5rem;
  font-weight: 700;
}

.report-id {
  color: var(--accent);
  font-size: 1rem;
}

.repo-path {
  color: var(--text-secondary);
  font-size: 0.85rem;
  font-family: monospace;
  margin-top: 0.25rem;
}

.report-date {
  color: var(--text-secondary);
  font-size: 0.8rem;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.summary-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  padding: 1.25rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.15s;
}

.summary-card:hover { transform: translateY(-2px); }

.summary-card .count {
  display: block;
  font-size: 2rem;
  font-weight: 800;
}

.summary-card .label {
  font-size: 0.8rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  font-weight: 600;
}

.summary-card.critical .count { color: var(--critical); }
.summary-card.error .count { color: var(--error); }
.summary-card.warning .count { color: var(--warning); }
.summary-card.info .count { color: var(--info); }

.report-body {
  display: flex;
  gap: 1.5rem;
  min-height: 60vh;
}

.file-list {
  width: 280px;
  flex-shrink: 0;
  background: var(--bg-secondary);
  border-radius: 0.5rem;
  padding: 1rem;
  overflow-y: auto;
  max-height: 70vh;
}

.file-list h3 {
  font-size: 0.9rem;
  color: var(--text-secondary);
  margin-bottom: 0.75rem;
}

.file-filters {
  margin-bottom: 0.75rem;
}

.file-filters button {
  padding: 0.3rem 0.6rem;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 0.25rem;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.75rem;
}

.file-filters button.active {
  background: var(--accent);
  color: white;
  border-color: var(--accent);
}

.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.75rem;
  border-radius: 0.25rem;
  cursor: pointer;
  font-size: 0.8rem;
  margin-bottom: 0.25rem;
}

.file-item:hover { background: var(--bg-card); }
.file-item.active { background: var(--bg-card); border-left: 3px solid var(--accent); }

.file-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.file-counts {
  display: flex;
  gap: 0.25rem;
}

.badge {
  font-size: 0.65rem;
  padding: 0.1rem 0.35rem;
  border-radius: 0.2rem;
  font-weight: 700;
}

.badge.critical { background: rgba(239,68,68,0.2); color: var(--critical); }
.badge.error { background: rgba(249,115,22,0.2); color: var(--error); }
.badge.warning { background: rgba(234,179,8,0.2); color: var(--warning); }
.badge.info { background: rgba(59,130,246,0.2); color: var(--info); }

.comments-panel {
  flex: 1;
  background: var(--bg-secondary);
  border-radius: 0.5rem;
  padding: 1rem;
  overflow-y: auto;
  max-height: 70vh;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.panel-header h3 {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.filter-tags {
  display: flex;
  gap: 0.5rem;
}

.filter-tag {
  background: var(--accent);
  color: white;
  padding: 0.2rem 0.6rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  cursor: pointer;
}

.comment-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.comment-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  padding: 1rem;
  cursor: pointer;
  transition: border-color 0.15s;
}

.comment-card:hover { border-color: var(--accent); }
.comment-card.selected { border-color: var(--accent); }

.comment-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.severity-badge {
  padding: 0.15rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
}

.severity-badge.critical { background: rgba(239,68,68,0.2); color: var(--critical); }
.severity-badge.error { background: rgba(249,115,22,0.2); color: var(--error); }
.severity-badge.warning { background: rgba(234,179,8,0.2); color: var(--warning); }
.severity-badge.info { background: rgba(59,130,246,0.2); color: var(--info); }

.comment-category {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.comment-confidence {
  margin-left: auto;
  font-size: 0.75rem;
  font-weight: 700;
}

.comment-title {
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.comment-location {
  font-size: 0.8rem;
  font-family: monospace;
}

.comment-location .file { color: var(--text-secondary); }
.comment-location .line { color: var(--accent); }

.comment-detail {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
}

.detail-section {
  margin-bottom: 1rem;
}

.detail-section h4 {
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
  text-transform: uppercase;
}

.detail-section p {
  font-size: 0.85rem;
  line-height: 1.6;
}

.suggestion-code {
  background: var(--bg-primary);
  padding: 0.75rem;
  border-radius: 0.25rem;
  font-size: 0.8rem;
  overflow-x: auto;
  white-space: pre-wrap;
}

.empty {
  text-align: center;
  color: var(--text-secondary);
  padding: 2rem;
}

.loading {
  text-align: center;
  color: var(--text-secondary);
  padding: 4rem;
  font-size: 1.1rem;
}
</style>
