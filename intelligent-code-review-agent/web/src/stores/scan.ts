import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { scanApi, reportApi, type ScanJob, type Report, type Comment } from '@/services/api'

export const useScanStore = defineStore('scan', () => {
  const currentJob = ref<ScanJob | null>(null)
  const jobs = ref<ScanJob[]>([])
  const currentReport = ref<Report | null>(null)
  const reports = ref<{ report_id: string; created_at: string; repo_path: string; total_comments: number }[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const severityCounts = computed(() => {
    if (!currentReport.value) return { critical: 0, error: 0, warning: 0, info: 0 }
    return currentReport.value.stats
  })

  const groupedComments = computed(() => {
    if (!currentReport.value) return {}
    const groups: Record<string, Comment[]> = {}
    for (const c of currentReport.value.comments) {
      if (!groups[c.severity]) groups[c.severity] = []
      groups[c.severity]!.push(c)
    }
    return groups
  })

  const filesWithIssues = computed(() => {
    if (!currentReport.value) return []
    const files: Record<string, { path: string; total: number; critical: number; error: number; warning: number; info: number }> = {}
    for (const c of currentReport.value.comments) {
      if (!files[c.file_path]) {
        files[c.file_path] = { path: c.file_path, total: 0, critical: 0, error: 0, warning: 0, info: 0 }
      }
      files[c.file_path]!.total++
      files[c.file_path]![c.severity as keyof typeof files[string]]!++
    }
    return Object.values(files).sort((a, b) => b.critical - a.critical || b.error - a.error || a.path.localeCompare(b.path))
  })

  async function startScan(repoPath: string, options: { commit?: string; base?: string; head?: string; model?: string } = {}) {
    loading.value = true
    error.value = null
    try {
      const res = await scanApi.start({
        repo_path: repoPath,
        commit_sha: options.commit,
        base_ref: options.base,
        head_ref: options.head,
        model: options.model,
      })
      currentJob.value = res.data
      return res.data
    } catch (e: any) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function pollJob(jobId: string): Promise<ScanJob> {
    const res = await scanApi.status(jobId)
    currentJob.value = res.data
    return res.data
  }

  async function loadReport(reportId: string) {
    loading.value = true
    try {
      const res = await reportApi.get(reportId)
      currentReport.value = res.data
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function loadReports() {
    try {
      const res = await scanApi.reports()
      reports.value = res.data
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function loadJobs() {
    try {
      const res = await scanApi.jobs()
      jobs.value = res.data
    } catch (e: any) {
      error.value = e.message
    }
  }

  return {
    currentJob, jobs, currentReport, reports, loading, error,
    severityCounts, groupedComments, filesWithIssues,
    startScan, pollJob, loadReport, loadReports, loadJobs,
  }
})
