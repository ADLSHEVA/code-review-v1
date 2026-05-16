<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useScanStore } from '@/stores/scan'

const { t } = useI18n()
const router = useRouter()
const store = useScanStore()
const expandedFolder = ref<string | null>(null)

onMounted(async () => {
  await store.loadJobs()
  await store.loadReports()
})

interface FolderGroup {
  path: string
  name: string
  reports: typeof store.reports
  latestDate: string
  totalIssues: number
}

const folders = computed<FolderGroup[]>(() => {
  const map = new Map<string, typeof store.reports>()
  for (const r of store.reports) {
    const key = r.repo_path
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(r)
  }
  return Array.from(map.entries()).map(([path, reports]) => {
    const sorted = reports.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    return {
      path,
      name: path.split(/[/\\]/).filter(Boolean).pop() || path,
      reports: sorted,
      latestDate: sorted[0]!.created_at,
      totalIssues: sorted[0]!.total_comments,
    }
  }).sort((a, b) => new Date(b.latestDate).getTime() - new Date(a.latestDate).getTime())
})

function toggleFolder(path: string) {
  expandedFolder.value = expandedFolder.value === path ? null : path
}

function statusColor(status: string) {
  return { completed: 'var(--success)', running: 'var(--accent)', failed: 'var(--critical)', pending: 'var(--warning)' }[status] || 'var(--text-secondary)'
}
</script>

<template>
  <div>
    <h2 class="page-title">{{ t('dashboard.title') }}</h2>

    <div class="quick-actions">
      <button class="btn-primary" @click="router.push('/scan')">
        🔍 {{ t('dashboard.startScan') }}
      </button>
      <button class="btn-secondary" @click="router.push('/compare')">
        📊 {{ t('dashboard.compareReports') }}
      </button>
    </div>

    <section class="section">
      <h3>{{ t('dashboard.recentReports') }}</h3>
      <div v-if="folders.length === 0" class="empty">{{ t('dashboard.noReports') }}</div>
      <div v-else class="folder-list">
        <div v-for="folder in folders" :key="folder.path" class="folder-group">
          <div class="folder-header" @click="toggleFolder(folder.path)">
            <div class="folder-info">
              <span class="folder-icon">{{ expandedFolder === folder.path ? '📂' : '📁' }}</span>
              <span class="folder-name">{{ folder.name }}</span>
              <span class="folder-path">{{ folder.path }}</span>
            </div>
            <div class="folder-meta">
              <span class="folder-count">{{ folder.reports.length }} {{ t('dashboard.reports') }}</span>
              <span class="folder-date">{{ new Date(folder.latestDate).toLocaleString() }}</span>
              <span class="arrow" :class="{ open: expandedFolder === folder.path }">▾</span>
            </div>
          </div>

          <div v-if="expandedFolder === folder.path" class="folder-reports">
            <div
              v-for="r in folder.reports"
              :key="r.report_id"
              class="report-row"
              @click="router.push(`/report/${r.report_id}`)"
            >
              <span class="report-id">#{{ r.report_id }}</span>
              <span class="report-date">{{ new Date(r.created_at).toLocaleString() }}</span>
              <button class="btn-link">{{ t('dashboard.viewReport') }} →</button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="section">
      <h3>{{ t('dashboard.recentScans') }}</h3>
      <div v-if="store.jobs.length === 0" class="empty">{{ t('dashboard.noScans') }}</div>
      <div v-else class="job-list">
        <div v-for="job in store.jobs.slice(0, 10)" :key="job.job_id" class="job-item">
          <span class="status-dot" :style="{ background: statusColor(job.status) }"></span>
          <span class="job-repo">{{ job.repo_path }}</span>
          <span class="job-status">{{ job.status }}</span>
          <span class="job-date">{{ new Date(job.created_at).toLocaleString() }}</span>
          <button
            v-if="job.report_id"
            class="btn-link"
            @click="router.push(`/report/${job.report_id}`)"
          >
            {{ t('dashboard.viewReport') }}
          </button>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 1.5rem;
}

.quick-actions {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
}

.btn-primary, .btn-secondary {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 0.5rem;
  font-size: 0.9rem;
  cursor: pointer;
  font-weight: 600;
}

.btn-primary {
  background: var(--accent);
  color: white;
}

.btn-primary:hover { background: var(--accent-hover); }

.btn-secondary {
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
}

.btn-secondary:hover { background: var(--border); }

.section {
  margin-bottom: 2rem;
}

.section h3 {
  font-size: 1.1rem;
  margin-bottom: 1rem;
  color: var(--text-secondary);
}

.empty {
  color: var(--text-secondary);
  padding: 2rem;
  text-align: center;
  background: var(--bg-secondary);
  border-radius: 0.5rem;
}

.report-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}

.folder-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.folder-group {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  overflow: hidden;
}

.folder-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  cursor: pointer;
  transition: background 0.15s;
}

.folder-header:hover {
  background: var(--bg-card);
}

.folder-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
}

.folder-icon {
  font-size: 1.3rem;
  flex-shrink: 0;
}

.folder-name {
  font-weight: 700;
  font-size: 1rem;
  flex-shrink: 0;
}

.folder-path {
  font-size: 0.75rem;
  color: var(--text-secondary);
  font-family: monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.folder-meta {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-shrink: 0;
}

.folder-count {
  font-size: 0.8rem;
  color: var(--text-secondary);
  background: var(--bg-card);
  padding: 0.2rem 0.6rem;
  border-radius: 0.25rem;
}

.folder-date {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.arrow {
  font-size: 0.7rem;
  color: var(--text-secondary);
  transition: transform 0.2s;
}

.arrow.open {
  transform: rotate(180deg);
}

.folder-reports {
  border-top: 1px solid var(--border);
  padding: 0.5rem;
}

.report-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.6rem 0.75rem;
  border-radius: 0.4rem;
  cursor: pointer;
  transition: background 0.15s;
}

.report-row:hover {
  background: var(--bg-card);
}

.report-id {
  font-weight: 700;
  color: var(--accent);
  font-size: 0.85rem;
}

.report-date {
  flex: 1;
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.comment-count {
  background: var(--bg-card);
  padding: 0.2rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.8rem;
}

.card-repo {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-bottom: 0.25rem;
  word-break: break-all;
}

.card-date {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.job-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.job-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: var(--bg-secondary);
  border-radius: 0.5rem;
  font-size: 0.85rem;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.job-repo {
  flex: 1;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.job-status {
  text-transform: uppercase;
  font-size: 0.75rem;
  font-weight: 600;
}

.job-date {
  color: var(--text-secondary);
  font-size: 0.75rem;
}

.btn-link {
  background: none;
  border: none;
  color: var(--accent);
  cursor: pointer;
  font-size: 0.85rem;
}

.btn-link:hover { text-decoration: underline; }
</style>
