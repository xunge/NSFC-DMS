import axios from 'axios'

// 创建 axios 实例
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    if (error.response) {
      const message = error.response.data?.error || '请求失败'
      return Promise.reject(new Error(message))
    }
    return Promise.reject(error)
  }
)

// API 方法
export default {
  // 健康检查
  health: () => api.get('/health'),

  // 项目相关
  fetchProject: (url, autoDownload = false) => api.post('/projects/fetch', { url, auto_download: autoDownload }),
  getProjects: (params = {}) => api.get('/projects', { params }),
  getProjectDetail: (id) => api.get(`/projects/${id}`),
  createProject: (data) => api.post('/projects', data),
  updateProject: (id, data) => api.put(`/projects/${id}`, data),
  deleteProject: (id) => api.delete(`/projects/${id}`),
  downloadProjectReport: (projectId) => api.post(`/projects/${projectId}/download-report`),
  downloadProjectReportSimple: (projectId) => api.post(`/projects/${projectId}/download-report-simple`),

  // PDF 相关
  uploadReport: (formData) => api.post('/reports/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  }),
  viewReport: (id) => api.get(`/reports/${id}/view`),
  downloadReport: (id) => api.get(`/reports/${id}/download`, {
    responseType: 'blob'
  }),
  deleteReport: (id) => api.delete(`/reports/${id}`),

  // 搜索历史
  getSearchHistory: (limit = 10) => api.get('/search/history', { params: { limit } }),
  clearSearchHistory: () => api.delete('/search/history'),

  // 导出
  exportProjects: (params = {}) => api.get('/export/projects', {
    params,
    responseType: 'blob'
  })
}
