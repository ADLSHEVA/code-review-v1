<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { guidelinesApi, type GuidelineFile } from '@/services/api'

const { t } = useI18n()

const files = ref<GuidelineFile[]>([])
const totalChunks = ref(0)
const loading = ref(false)
const uploading = ref(false)
const reindexing = ref(false)
const statusMsg = ref('')
const statusType = ref<'success' | 'error'>('success')
const fileInput = ref<HTMLInputElement | null>(null)

onMounted(() => {
  loadFiles()
})

async function loadFiles() {
  loading.value = true
  try {
    const res = await guidelinesApi.list()
    files.value = res.data.files
    totalChunks.value = res.data.total_chunks
  } catch {
    // silent
  } finally {
    loading.value = false
  }
}

function triggerFileInput() {
  fileInput.value?.click()
}

async function handleUpload(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  uploading.value = true
  statusMsg.value = ''
  try {
    const res = await guidelinesApi.upload(file)
    showStatus(t('guidelines.uploadSuccess') + ` (${res.data.chunks_indexed} ${t('guidelines.chunks').toLowerCase()})`, 'success')
    await loadFiles()
  } catch (e: any) {
    showStatus(e.response?.data?.detail || t('guidelines.uploadError'), 'error')
  } finally {
    uploading.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}

async function deleteFile(filename: string) {
  if (!confirm(t('guidelines.deleteConfirm'))) return
  try {
    await guidelinesApi.delete(filename)
    showStatus(t('guidelines.deleteSuccess'), 'success')
    await loadFiles()
  } catch {
    showStatus(t('guidelines.deleteError'), 'error')
  }
}

async function reindexAll() {
  reindexing.value = true
  statusMsg.value = ''
  try {
    const res = await guidelinesApi.reindex()
    showStatus(t('guidelines.reindexSuccess') + ` (${res.data.chunks_indexed} ${t('guidelines.chunks').toLowerCase()})`, 'success')
    await loadFiles()
  } catch {
    showStatus(t('guidelines.reindexError'), 'error')
  } finally {
    reindexing.value = false
  }
}

function showStatus(msg: string, type: 'success' | 'error') {
  statusMsg.value = msg
  statusType.value = type
  setTimeout(() => { statusMsg.value = '' }, 5000)
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString()
}
</script>

<template>
  <div>
    <h2 class="page-title">{{ t('guidelines.title') }}</h2>

    <div class="upload-section">
      <div class="upload-area">
        <input
          ref="fileInput"
          type="file"
          accept=".md,.txt,.rst,.adoc,.pdf,.docx"
          style="display: none"
          @change="handleUpload"
        />
        <button class="btn-primary" :disabled="uploading" @click="triggerFileInput">
          {{ uploading ? t('guidelines.uploading') : t('guidelines.uploadBtn') }}
        </button>
        <span class="upload-hint">{{ t('guidelines.acceptedFormats') }}</span>
        <span class="upload-hint">{{ t('guidelines.maxSize') }}</span>
      </div>

      <div v-if="statusMsg" :class="['status-msg', statusType]">
        {{ statusMsg }}
      </div>
    </div>

    <div class="list-section">
      <div class="list-header">
        <h3>{{ t('guidelines.list') }}</h3>
        <div class="list-actions">
          <span class="stat">{{ t('guidelines.totalFiles') }}: {{ files.length }}</span>
          <span class="stat">{{ t('guidelines.totalChunks') }}: {{ totalChunks }}</span>
          <button class="btn-secondary" :disabled="reindexing" @click="reindexAll">
            {{ reindexing ? t('guidelines.reindexing') : t('guidelines.reindex') }}
          </button>
        </div>
      </div>

      <div v-if="files.length === 0" class="empty">
        {{ t('guidelines.noFiles') }}
      </div>

      <table v-else class="files-table">
        <thead>
          <tr>
            <th>{{ t('guidelines.filename') }}</th>
            <th>{{ t('guidelines.size') }}</th>
            <th>{{ t('guidelines.uploadedAt') }}</th>
            <th>{{ t('guidelines.chunks') }}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="f in files" :key="f.filename">
            <td class="filename">{{ f.filename }}</td>
            <td>{{ formatSize(f.size_bytes) }}</td>
            <td>{{ formatDate(f.uploaded_at) }}</td>
            <td class="chunks">{{ f.doc_count }}</td>
            <td>
              <button class="btn-delete" @click="deleteFile(f.filename)">
                {{ t('guidelines.delete') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 1.5rem;
}

.upload-section {
  margin-bottom: 2rem;
}

.upload-area {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.upload-hint {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.status-msg {
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.85rem;
}

.status-msg.success {
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid var(--success);
  color: var(--success);
}

.status-msg.error {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid var(--critical);
  color: var(--critical);
}

.list-section {
  background: var(--bg-secondary);
  border-radius: 0.5rem;
  padding: 1.5rem;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.list-header h3 {
  font-size: 1rem;
  color: var(--accent);
}

.list-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.stat {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.empty {
  text-align: center;
  color: var(--text-secondary);
  padding: 2rem;
}

.files-table {
  width: 100%;
  border-collapse: collapse;
}

.files-table th {
  text-align: left;
  padding: 0.75rem;
  border-bottom: 1px solid var(--border);
  font-size: 0.8rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  font-weight: 600;
}

.files-table td {
  padding: 0.75rem;
  border-bottom: 1px solid var(--border);
  font-size: 0.85rem;
}

.filename {
  font-family: monospace;
  font-weight: 600;
}

.chunks {
  text-align: center;
}

.btn-primary, .btn-secondary {
  padding: 0.6rem 1.2rem;
  border: none;
  border-radius: 0.5rem;
  font-size: 0.85rem;
  cursor: pointer;
  font-weight: 600;
}

.btn-primary {
  background: var(--accent);
  color: white;
}

.btn-primary:hover { background: var(--accent-hover); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary {
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
}

.btn-secondary:hover { background: var(--border); }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-delete {
  padding: 0.3rem 0.8rem;
  background: transparent;
  border: 1px solid var(--critical);
  border-radius: 0.25rem;
  color: var(--critical);
  cursor: pointer;
  font-size: 0.75rem;
}

.btn-delete:hover {
  background: rgba(239, 68, 68, 0.15);
}
</style>
