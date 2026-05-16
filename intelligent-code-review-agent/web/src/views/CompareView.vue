<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { reportApi, scanApi } from '@/services/api'

const { t } = useI18n()
const reports = ref<any[]>([])
const selectedA = ref('')
const selectedB = ref('')
const comparison = ref<any>(null)
const loading = ref(false)

onMounted(async () => {
  const res = await scanApi.reports()
  reports.value = res.data
})

async function compare() {
  if (!selectedA.value || !selectedB.value) return
  loading.value = true
  try {
    const res = await reportApi.compare(selectedA.value, selectedB.value)
    comparison.value = res.data
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <h2 class="page-title">{{ t('compare.title') }}</h2>

    <div class="compare-form">
      <div class="form-group">
        <label>{{ t('compare.reportA') }}</label>
        <select v-model="selectedA">
          <option value="">{{ t('compare.selectReport') }}</option>
          <option v-for="r in reports" :key="r.report_id" :value="r.report_id">
            #{{ r.report_id }} — {{ r.repo_path }} ({{ r.total_comments }} {{ t('common.issues') }})
          </option>
        </select>
      </div>
      <div class="form-group">
        <label>{{ t('compare.reportB') }}</label>
        <select v-model="selectedB">
          <option value="">{{ t('compare.selectReport') }}</option>
          <option v-for="r in reports" :key="r.report_id" :value="r.report_id">
            #{{ r.report_id }} — {{ r.repo_path }} ({{ r.total_comments }} {{ t('common.issues') }})
          </option>
        </select>
      </div>
      <button class="btn-primary" :disabled="!selectedA || !selectedB || loading" @click="compare">
        {{ loading ? t('compare.comparing') : t('compare.compareBtn') }}
      </button>
    </div>

    <div v-if="comparison" class="compare-results">
      <div class="result-summary">
        <div class="result-card resolved">
          <span class="count">{{ comparison.summary.resolved_count }}</span>
          <span class="label">{{ t('compare.resolved') }}</span>
        </div>
        <div class="result-card persistent">
          <span class="count">{{ comparison.summary.persistent_count }}</span>
          <span class="label">{{ t('compare.persistent') }}</span>
        </div>
        <div class="result-card new">
          <span class="count">{{ comparison.summary.new_count }}</span>
          <span class="label">{{ t('compare.newIssues') }}</span>
        </div>
      </div>

      <div v-if="comparison.new_issues.length" class="section">
        <h3 class="section-title new">{{ t('compare.newIssues') }} ({{ comparison.new_issues.length }})</h3>
        <div v-for="(c, i) in comparison.new_issues" :key="i" class="issue-row">
          <span :class="['severity-dot', c.severity]"></span>
          <span class="issue-title">{{ c.title }}</span>
          <span class="issue-file">{{ c.file_path }}:{{ c.line_start }}</span>
        </div>
      </div>

      <div v-if="comparison.resolved_issues.length" class="section">
        <h3 class="section-title resolved">{{ t('compare.resolvedIssues') }} ({{ comparison.resolved_issues.length }})</h3>
        <div v-for="(c, i) in comparison.resolved_issues" :key="i" class="issue-row resolved">
          <span :class="['severity-dot', c.severity]"></span>
          <span class="issue-title">{{ c.title }}</span>
          <span class="issue-file">{{ c.file_path }}:{{ c.line_start }}</span>
        </div>
      </div>

      <div v-if="comparison.persistent_issues.length" class="section">
        <h3 class="section-title persistent">{{ t('compare.persistentIssues') }} ({{ comparison.persistent_issues.length }})</h3>
        <div v-for="(c, i) in comparison.persistent_issues" :key="i" class="issue-row">
          <span :class="['severity-dot', c.severity]"></span>
          <span class="issue-title">{{ c.title }}</span>
          <span class="issue-file">{{ c.file_path }}:{{ c.line_start }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-title { font-size: 1.5rem; font-weight: 700; margin-bottom: 1.5rem; }

.compare-form {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
  margin-bottom: 2rem;
}

.form-group { flex: 1; display: flex; flex-direction: column; gap: 0.5rem; }
.form-group label { font-size: 0.85rem; font-weight: 600; color: var(--text-secondary); }
.form-group select {
  padding: 0.75rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  color: var(--text-primary);
  font-size: 0.85rem;
}

.btn-primary {
  padding: 0.75rem 1.5rem;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-weight: 600;
}

.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.result-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin-bottom: 2rem;
}

.result-card {
  background: var(--bg-secondary);
  border-radius: 0.5rem;
  padding: 1.5rem;
  text-align: center;
}

.result-card .count { display: block; font-size: 2.5rem; font-weight: 800; }
.result-card .label { font-size: 0.8rem; color: var(--text-secondary); text-transform: uppercase; }
.result-card.resolved .count { color: var(--success); }
.result-card.persistent .count { color: var(--warning); }
.result-card.new .count { color: var(--critical); }

.section { margin-bottom: 2rem; }
.section-title { font-size: 1rem; margin-bottom: 1rem; }
.section-title.new { color: var(--critical); }
.section-title.resolved { color: var(--success); }
.section-title.persistent { color: var(--warning); }

.issue-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: var(--bg-secondary);
  border-radius: 0.25rem;
  margin-bottom: 0.5rem;
  font-size: 0.85rem;
}

.issue-row.resolved { opacity: 0.6; text-decoration: line-through; }

.severity-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.severity-dot.critical { background: var(--critical); }
.severity-dot.error { background: var(--error); }
.severity-dot.warning { background: var(--warning); }
.severity-dot.info { background: var(--info); }

.issue-title { flex: 1; }
.issue-file { font-family: monospace; font-size: 0.8rem; color: var(--text-secondary); }
</style>
