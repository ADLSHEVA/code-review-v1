<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useScanStore } from '@/stores/scan'
import { guidelinesApi, type GuidelineFile } from '@/services/api'

const { t } = useI18n()
const router = useRouter()
const store = useScanStore()

const repoPath = ref('D:\\tygr')
const commitSha = ref('HEAD')
const mode = ref<'commit' | 'branch'>('commit')
const baseRef = ref('main')
const headRef = ref('develop')
const scanning = ref(false)
const job = ref<any>(null)
const guidelines = ref<GuidelineFile[]>([])
const totalChunks = ref(0)
const startTime = ref(0)
const elapsed = ref('0:00')
let pollTimer: ReturnType<typeof setInterval> | null = null
let elapsedTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  try {
    const res = await guidelinesApi.list()
    guidelines.value = res.data.files
    totalChunks.value = res.data.total_chunks
  } catch { /* ignore */ }
})

const progressPercent = computed(() => job.value?.progress || 0)
const currentFileNum = computed(() => {
  if (!job.value?.current_file || !job.value?.total_files) return 0
  const pct = job.value.progress || 0
  return Math.max(1, Math.round((pct / 100) * job.value.total_files))
})

function updateElapsed() {
  const secs = Math.floor((Date.now() - startTime.value) / 1000)
  const m = Math.floor(secs / 60)
  const s = secs % 60
  elapsed.value = `${m}:${s.toString().padStart(2, '0')}`
}

async function startScan() {
  scanning.value = true
  startTime.value = Date.now()
  elapsedTimer = setInterval(updateElapsed, 1000)
  try {
    const result = await store.startScan(repoPath.value, {
      commit: mode.value === 'commit' ? commitSha.value : undefined,
      base: mode.value === 'branch' ? baseRef.value : undefined,
      head: mode.value === 'branch' ? headRef.value : undefined,
    })
    job.value = result
    pollTimer = setInterval(async () => {
      const updated = await store.pollJob(result.job_id)
      job.value = updated
      if (updated.status === 'completed' || updated.status === 'failed') {
        if (pollTimer) clearInterval(pollTimer)
        if (elapsedTimer) clearInterval(elapsedTimer)
        if (updated.report_id) {
          setTimeout(() => router.push(`/report/${updated.report_id}`), 800)
        }
      }
    }, 2000)
  } catch (e) {
    scanning.value = false
    if (elapsedTimer) clearInterval(elapsedTimer)
  }
}

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
  if (elapsedTimer) clearInterval(elapsedTimer)
})
</script>

<template>
  <div>
    <h2 class="page-title">{{ t('scan.title') }}</h2>

    <div v-if="!scanning" class="scan-layout">
      <div class="scan-form">
        <div class="form-group">
          <label>{{ t('scan.repoPath') }}</label>
          <input v-model="repoPath" type="text" :placeholder="t('scan.repoPlaceholder')" />
        </div>

        <div class="form-group">
          <label>{{ t('scan.scanMode') }}</label>
          <div class="mode-toggle">
            <button :class="{ active: mode === 'commit' }" @click="mode = 'commit'">{{ t('scan.singleCommit') }}</button>
            <button :class="{ active: mode === 'branch' }" @click="mode = 'branch'">{{ t('scan.branchDiff') }}</button>
          </div>
        </div>

        <div v-if="mode === 'commit'" class="form-group">
          <label>{{ t('scan.commitSha') }}</label>
          <input v-model="commitSha" type="text" :placeholder="t('scan.commitPlaceholder')" />
        </div>

        <div v-else class="form-row">
          <div class="form-group">
            <label>{{ t('scan.baseRef') }}</label>
            <input v-model="baseRef" type="text" :placeholder="t('scan.basePlaceholder')" />
          </div>
          <div class="form-group">
            <label>{{ t('scan.headRef') }}</label>
            <input v-model="headRef" type="text" :placeholder="t('scan.headPlaceholder')" />
          </div>
        </div>

        <button class="btn-primary" @click="startScan">
          🔍 {{ t('scan.startBtn') }}
        </button>
      </div>

      <div class="rag-panel">
        <div class="rag-header">
          <h3>📋 {{ t('scan.ragTitle') }}</h3>
          <button class="btn-link" @click="router.push('/guidelines')">{{ t('scan.manageGuidelines') }}</button>
        </div>

        <div class="rag-status">
          <div class="rag-stat">
            <span class="rag-icon">📄</span>
            <span class="rag-label">{{ t('scan.defaultGuidelines') }}</span>
            <span class="rag-value">3 {{ t('scan.files') }}</span>
          </div>
          <div class="rag-stat">
            <span class="rag-icon">📁</span>
            <span class="rag-label">{{ t('scan.customGuidelines') }}</span>
            <span class="rag-value">{{ guidelines.length }} {{ t('scan.files') }}</span>
          </div>
          <div class="rag-stat">
            <span class="rag-icon">🧩</span>
            <span class="rag-label">{{ t('scan.totalChunks') }}</span>
            <span class="rag-value">{{ totalChunks }}</span>
          </div>
        </div>

        <div v-if="guidelines.length > 0" class="rag-files">
          <div v-for="g in guidelines" :key="g.filename" class="rag-file">
            <span class="rag-file-icon">📎</span>
            <span class="rag-file-name">{{ g.filename }}</span>
            <span class="rag-file-chunks">{{ g.doc_count }} {{ t('scan.chunks') }}</span>
          </div>
        </div>

        <p class="rag-hint">{{ t('scan.ragHint') }}</p>
      </div>
    </div>

    <div v-else class="scanning">
      <div class="progress-section">
        <div class="progress-header">
          <span :class="['progress-status', job?.status]">
            {{ job?.status === 'running' ? t('scan.scanning') : job?.status }}
          </span>
          <span class="progress-elapsed">{{ t('scan.elapsed') }}: {{ elapsed }}</span>
        </div>

        <div class="progress-track">
          <div class="progress-fill" :style="{ width: progressPercent + '%' }">
            <span v-if="progressPercent > 5" class="progress-inner-text">{{ progressPercent }}%</span>
          </div>
        </div>
        <span class="progress-percent">{{ progressPercent }}%</span>

        <div class="progress-detail">
          <div class="detail-item">
            <span class="detail-label">{{ t('scan.files') }}</span>
            <span class="detail-value">{{ currentFileNum }} / {{ job?.total_files || '?' }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">{{ t('scan.status') }}</span>
            <span :class="['detail-value', 'status-' + job?.status]">{{ job?.status }}</span>
          </div>
        </div>

        <div v-if="job?.current_file" class="current-file-section">
          <span class="current-label">{{ t('scan.current') }}</span>
          <span class="current-path">{{ job.current_file }}</span>
        </div>

        <div v-if="job?.status === 'completed'" class="scan-done success">
          ✅ {{ t('scan.done') }}
        </div>
        <div v-if="job?.status === 'failed'" class="scan-done failed">
          ❌ {{ t('scan.failed') }}: {{ job?.error }}
        </div>
      </div>
    </div>

    <div v-if="store.error" class="error-banner">
      {{ store.error }}
    </div>
  </div>
</template>

<style scoped>
.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 1.5rem;
}

.scan-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  max-width: 1100px;
}

.scan-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.form-group input {
  padding: 0.75rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  color: var(--text-primary);
  font-size: 0.9rem;
}

.form-group input:focus {
  outline: none;
  border-color: var(--accent);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.mode-toggle {
  display: flex;
  gap: 0;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  overflow: hidden;
}

.mode-toggle button {
  flex: 1;
  padding: 0.6rem 1rem;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  border: none;
  cursor: pointer;
  font-size: 0.85rem;
}

.mode-toggle button.active {
  background: var(--accent);
  color: white;
}

.btn-primary {
  padding: 0.75rem 1.5rem;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-size: 0.9rem;
  cursor: pointer;
  font-weight: 600;
  align-self: flex-start;
}

.btn-primary:hover { background: var(--accent-hover); }

/* RAG Panel */
.rag-panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  padding: 1.25rem;
}

.rag-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.rag-header h3 {
  font-size: 0.95rem;
  font-weight: 700;
}

.btn-link {
  background: none;
  border: none;
  color: var(--accent);
  cursor: pointer;
  font-size: 0.8rem;
}

.btn-link:hover { text-decoration: underline; }

.rag-status {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  margin-bottom: 1rem;
}

.rag-stat {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-size: 0.85rem;
}

.rag-icon {
  font-size: 1rem;
  width: 1.5rem;
  text-align: center;
}

.rag-label {
  flex: 1;
  color: var(--text-secondary);
}

.rag-value {
  font-weight: 600;
}

.rag-files {
  border-top: 1px solid var(--border);
  padding-top: 0.75rem;
  margin-bottom: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  max-height: 180px;
  overflow-y: auto;
}

.rag-file {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
  padding: 0.3rem 0;
}

.rag-file-icon {
  font-size: 0.85rem;
}

.rag-file-name {
  flex: 1;
  font-family: monospace;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rag-file-chunks {
  color: var(--text-secondary);
  font-size: 0.75rem;
}

.rag-hint {
  font-size: 0.75rem;
  color: var(--text-secondary);
  line-height: 1.5;
  border-top: 1px solid var(--border);
  padding-top: 0.75rem;
}

/* Scanning Progress */
.scanning {
  max-width: 700px;
}

.progress-section {
  background: var(--bg-secondary);
  border-radius: 0.75rem;
  padding: 2rem;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.25rem;
}

.progress-status {
  font-size: 1rem;
  font-weight: 700;
  text-transform: uppercase;
}

.progress-status.running { color: var(--accent); }
.progress-status.completed { color: var(--success); }
.progress-status.failed { color: var(--critical); }

.progress-elapsed {
  font-size: 0.85rem;
  color: var(--text-secondary);
  font-family: monospace;
}

.progress-track {
  height: 24px;
  background: var(--bg-card);
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 0.75rem;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent), #60a5fa);
  border-radius: 12px;
  transition: width 0.5s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
}

.progress-inner-text {
  font-size: 0.7rem;
  font-weight: 700;
  color: white;
}

.progress-percent {
  display: block;
  text-align: center;
  font-size: 2rem;
  font-weight: 800;
  color: var(--accent);
  margin-bottom: 1.5rem;
}

.progress-detail {
  display: flex;
  gap: 2rem;
  margin-bottom: 1.25rem;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.detail-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  font-weight: 600;
}

.detail-value {
  font-size: 1rem;
  font-weight: 700;
}

.status-running { color: var(--accent); }
.status-completed { color: var(--success); }
.status-failed { color: var(--critical); }

.current-file-section {
  background: var(--bg-card);
  border-radius: 0.5rem;
  padding: 1rem;
  margin-bottom: 1.25rem;
}

.current-label {
  display: block;
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  font-weight: 600;
}

.current-path {
  font-family: monospace;
  font-size: 0.85rem;
  color: var(--text-primary);
  word-break: break-all;
}

.scan-done {
  padding: 1rem;
  border-radius: 0.5rem;
  font-weight: 600;
  text-align: center;
}

.scan-done.success {
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid var(--success);
  color: var(--success);
}

.scan-done.failed {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid var(--critical);
  color: var(--critical);
}

.error-banner {
  margin-top: 1rem;
  padding: 1rem;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid var(--critical);
  border-radius: 0.5rem;
  color: var(--critical);
}
</style>
