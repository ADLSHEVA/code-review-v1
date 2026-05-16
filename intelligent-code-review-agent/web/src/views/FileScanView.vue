<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { fileScanApi } from '@/services/api'

const router = useRouter()
const { t } = useI18n()

const file = ref<File | null>(null)
const scanning = ref(false)
const error = ref('')
const language = ref('')
const dragging = ref(false)

const EXT_MAP: Record<string, string> = {
  '.py': 'Python', '.js': 'JavaScript', '.jsx': 'JavaScript', '.ts': 'TypeScript', '.tsx': 'TypeScript',
  '.java': 'Java', '.go': 'Go', '.rs': 'Rust', '.c': 'C', '.cpp': 'C++', '.h': 'C', '.hpp': 'C++',
  '.cs': 'C#', '.php': 'PHP', '.rb': 'Ruby', '.swift': 'Swift', '.kt': 'Kotlin', '.kts': 'Kotlin',
  '.scala': 'Scala', '.sc': 'Scala', '.lua': 'Lua', '.sql': 'SQL', '.jl': 'Julia', '.m': 'MATLAB',
  '.dart': 'Dart', '.st': 'Structured Text', '.iecst': 'Structured Text',
  '.cob': 'COBOL', '.cbl': 'COBOL', '.cpy': 'COBOL', '.r': 'R', '.sas': 'SAS',
  '.sol': 'Solidity', '.sh': 'Shell', '.bash': 'Shell', '.zsh': 'Shell',
  '.v': 'Verilog', '.vh': 'Verilog', '.sv': 'SystemVerilog', '.svh': 'SystemVerilog', '.zig': 'Zig', '.mm': 'Objective-C',
}

function detectLanguage(filename: string): string {
  const ext = '.' + filename.split('.').pop()?.toLowerCase()
  return EXT_MAP[ext] || ''
}

function onDrop(e: DragEvent) {
  dragging.value = false
  const files = e.dataTransfer?.files
  if (files && files.length > 0) {
    selectFile(files[0]!)
  }
}

function onDragOver(e: DragEvent) {
  dragging.value = true
}

function onDragLeave() {
  dragging.value = false
}

function onFileInput(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    selectFile(input.files[0]!)
  }
}

function selectFile(f: File) {
  file.value = f
  language.value = detectLanguage(f.name)
  error.value = ''
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

async function startScan() {
  if (!file.value) return
  if (!language.value) {
    error.value = t('fileScan.unsupported')
    return
  }
  scanning.value = true
  error.value = ''
  try {
    const res = await fileScanApi.scan(file.value)
    router.push(`/report/${res.data.report_id}`)
  } catch (e: any) {
    error.value = e.response?.data?.detail || t('fileScan.failed')
    scanning.value = false
  }
}

function triggerFileInput() {
  document.getElementById('file-input')?.click()
}
</script>

<template>
  <div class="file-scan">
    <h2>{{ t('fileScan.title') }}</h2>

    <div
      v-if="!scanning"
      class="drop-zone"
      :class="{ dragging, 'has-file': !!file }"
      @drop.prevent="onDrop"
      @dragover.prevent="onDragOver"
      @dragleave="onDragLeave"
      @click="triggerFileInput"
    >
      <input
        id="file-input"
        type="file"
        @change="onFileInput"
        style="display: none"
      />

      <div v-if="!file" class="drop-prompt">
        <div class="drop-icon">📄</div>
        <p class="drop-text">{{ t('fileScan.dropzone') }}</p>
        <span class="browse-btn">{{ t('fileScan.browse') }}</span>
      </div>

      <div v-else class="file-info">
        <div class="file-icon">📝</div>
        <div class="file-details">
          <span class="file-name">{{ file.name }}</span>
          <span class="file-meta">
            {{ formatSize(file.size) }}
            <span v-if="language" class="lang-badge">{{ language }}</span>
            <span v-else class="lang-badge unsupported">{{ t('fileScan.unsupported') }}</span>
          </span>
        </div>
      </div>
    </div>

    <div v-if="error" class="error-msg">{{ error }}</div>

    <button
      v-if="!scanning && file"
      class="scan-btn"
      :disabled="!language"
      @click="startScan"
    >
      {{ t('fileScan.scanBtn') }}
    </button>

    <div v-if="scanning" class="scanning">
      <div class="spinner"></div>
      <p>{{ t('fileScan.scanning') }}</p>
    </div>
  </div>
</template>

<style scoped>
.file-scan {
  max-width: 700px;
  margin: 0 auto;
}

h2 {
  margin-bottom: 1.5rem;
  font-size: 1.5rem;
}

.drop-zone {
  border: 2px dashed var(--border);
  border-radius: 1rem;
  padding: 3rem 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--bg-secondary);
}

.drop-zone:hover,
.drop-zone.dragging {
  border-color: var(--accent);
  background: rgba(59, 130, 246, 0.05);
}

.drop-zone.has-file {
  border-color: var(--success);
  padding: 1.5rem 2rem;
}

.drop-prompt {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.drop-icon {
  font-size: 3rem;
}

.drop-text {
  font-size: 1.1rem;
  color: var(--text-secondary);
}

.browse-btn {
  display: inline-block;
  padding: 0.5rem 1.5rem;
  background: var(--accent);
  color: white;
  border-radius: 0.5rem;
  font-size: 0.9rem;
  margin-top: 0.5rem;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.file-icon {
  font-size: 2.5rem;
}

.file-details {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  text-align: left;
}

.file-name {
  font-size: 1.1rem;
  font-weight: 600;
}

.file-meta {
  font-size: 0.85rem;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.lang-badge {
  display: inline-block;
  padding: 0.15rem 0.6rem;
  background: var(--accent);
  color: white;
  border-radius: 1rem;
  font-size: 0.75rem;
  font-weight: 600;
}

.lang-badge.unsupported {
  background: var(--error);
}

.error-msg {
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid var(--critical);
  border-radius: 0.5rem;
  color: var(--critical);
}

.scan-btn {
  margin-top: 1.5rem;
  padding: 0.75rem 2rem;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}

.scan-btn:hover:not(:disabled) {
  background: var(--accent-hover);
}

.scan-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.scanning {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 3rem;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.scanning p {
  font-size: 1.1rem;
  color: var(--text-secondary);
}
</style>
