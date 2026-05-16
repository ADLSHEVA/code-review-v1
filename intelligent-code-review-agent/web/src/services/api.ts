import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 300000,
})

export interface ScanRequest {
  repo_path: string
  commit_sha?: string
  base_ref?: string
  head_ref?: string
  model?: string
  files_filter?: string[]
}

export interface ScanJob {
  job_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  repo_path: string
  created_at: string
  started_at?: string
  completed_at?: string
  progress: number
  total_files: number
  current_file?: string
  error?: string
  report_id?: string
}

export interface Comment {
  file_path: string
  line_start: number
  line_end?: number
  severity: string
  category: string
  title: string
  description: string
  suggestion?: string
  confidence: number
}

export interface Report {
  report_id: string
  scan_id: string
  repo_path: string
  created_at: string
  summary: string
  comments: Comment[]
  stats: { critical: number; error: number; warning: number; info: number }
  reviewed_files: string[]
  skipped_files: string[]
}

export const scanApi = {
  start: (req: ScanRequest) => api.post<ScanJob>('/scan/start', req),
  status: (jobId: string) => api.get<ScanJob>(`/scan/status/${jobId}`),
  jobs: () => api.get<ScanJob[]>('/scan/jobs'),
  reports: () => api.get('/scan/reports'),
}

export const reportApi = {
  get: (id: string) => api.get<Report>(`/report/${id}`),
  comments: (id: string, params?: { severity?: string; category?: string; file_path?: string }) =>
    api.get<Comment[]>(`/report/${id}/comments`, { params }),
  files: (id: string) => api.get(`/report/${id}/files`),
  compare: (a: string, b: string) => api.post('/report/compare', { report_id_a: a, report_id_b: b }),
}

export const configApi = {
  get: () => api.get('/config/'),
  languages: () => api.get('/config/languages'),
}

export interface GuidelineFile {
  filename: string
  size_bytes: number
  uploaded_at: string
  doc_count: number
}

export interface GuidelineListResponse {
  files: GuidelineFile[]
  total_files: number
  total_chunks: number
}

export interface GuidelineUploadResponse {
  filename: string
  size_bytes: number
  chunks_indexed: number
  message: string
}

export const guidelinesApi = {
  list: () => api.get<GuidelineListResponse>('/guidelines/list'),
  upload: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post<GuidelineUploadResponse>('/guidelines/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  delete: (filename: string) => api.delete(`/guidelines/${encodeURIComponent(filename)}`),
  reindex: () => api.post('/guidelines/reindex'),
}

export interface FileScanResponse {
  report_id: string
  filename: string
  language: string
  issues_count: number
}

export const fileScanApi = {
  scan: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post<FileScanResponse>('/file-scan/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

export default api
