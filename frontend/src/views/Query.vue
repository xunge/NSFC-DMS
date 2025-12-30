<template>
  <div class="query" style="height: 100%; overflow-y: auto;">
    <div class="container" style="min-height: 100%;">
      <h2 class="page-title">项目查询</h2>

      <div class="card mb-20">
        <h3>获取项目信息</h3>
        <p style="color: #909399; margin-bottom: 16px; font-size: 14px;">
          从 <el-link type="primary" href="https://kd.nsfc.cn/" target="_blank">kd.nsfc.cn</el-link> 获取项目详情链接，输入URL提取项目信息
        </p>

        <el-form :model="fetchForm" :rules="fetchRules" ref="fetchForm" label-position="top">
          <el-form-item label="项目详情URL" prop="url">
            <el-input
              v-model="fetchForm.url"
              placeholder="例如：https://kd.nsfc.cn/finalDetails?id=5a1756a1889ed2729849032b6b815f47"
              clearable
              :disabled="loading"
            >
              <template #append>
                <el-button @click="handleFetch" :loading="loading" type="primary">
                  {{ loading ? '获取中...' : '获取信息' }}
                </el-button>
              </template>
            </el-input>
          </el-form-item>
          <el-form-item>
            <el-checkbox v-model="fetchForm.autoDownload" :disabled="loading">
              自动下载结题报告PDF（耗时较长）
            </el-checkbox>
            <!-- <span style="color: #909399; font-size: 12px; margin-left: 12px;">
              下载过程可能需要几分钟，请耐心等待
            </span> -->
          </el-form-item>
        </el-form>

        <!-- 下载进度显示 -->
        <div v-if="downloadProgress.show" class="download-progress mt-20">
          <div style="margin-top: 8px;">
            <div v-if="downloadProgress.current_page > 0 || downloadProgress.total_pages" style="margin-top: 12px; padding: 8px; background-color: #f0f9ff; border-radius: 4px; border-left: 3px solid #409eff;">
              <div v-if="downloadProgress.collected_pages > 0" style="font-size: 12px; color: #606266; margin-top: 4px;">
                已成功收集：{{ downloadProgress.collected_pages }} 页
                <span v-if="downloadProgress.total_pages"> / {{ downloadProgress.total_pages }} 页</span>
              </div>
              <div v-if="downloadProgress.total_pages && downloadProgress.collected_pages > 0" style="margin-top: 8px;">
                <el-progress 
                  :percentage="Math.round((downloadProgress.collected_pages / downloadProgress.total_pages) * 100)" 
                  :stroke-width="8"
                  :show-text="true"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- 结题报告下载结果 -->
          <div v-if="reportResult.show" class="mt-20">
            <el-alert
              :title="reportResult.title"
              :type="reportResult.type"
              :closable="false"
            >
              <div v-if="reportResult.success" style="margin-top: 8px;">
                <div>文件名: {{ reportResult.filename }}</div>
                <div>页数: {{ reportResult.page_count }} 页</div>
                <div style="margin-top: 8px;">
                  <el-button size="small" type="primary" @click="viewReport(reportResult.report_id)">
                    在线预览
                  </el-button>
                  <el-button size="small" @click="downloadReport(reportResult.report_id)">
                    下载PDF
                  </el-button>
                </div>
              </div>
              <div v-else style="margin-top: 8px;">
                {{ reportResult.message }}
              </div>
            </el-alert>
          </div>

        <div v-if="fetchedData" class="mt-20">
          <el-alert
            title="获取成功！"
            type="success"
            :closable="false"
            class="mb-20"
          >
            项目信息已提取并保存到数据库
          </el-alert>

          <el-descriptions :column="2" border title="项目信息">
            <el-descriptions-item label="项目名称">{{ fetchedData.title }}</el-descriptions-item>
            <el-descriptions-item label="项目批准号">{{ fetchedData.approval_number || '-' }}</el-descriptions-item>
            <el-descriptions-item label="申请代码">{{ fetchedData.application_code || '-' }}</el-descriptions-item>
            <el-descriptions-item label="项目负责人">{{ fetchedData.leader || '-' }}</el-descriptions-item>
            <el-descriptions-item label="依托单位">{{ fetchedData.unit || '-' }}</el-descriptions-item>
            <el-descriptions-item label="研究期限">{{ fetchedData.start_date }} 至 {{ fetchedData.end_date }}</el-descriptions-item>
            <el-descriptions-item label="资助经费">{{ fetchedData.funding ? fetchedData.funding + ' 万元' : '-' }}</el-descriptions-item>
          </el-descriptions>

          <div v-if="fetchedData.abstract" class="mt-20">
            <h4>项目摘要</h4>
            <div class="code-block">{{ fetchedData.abstract }}</div>
          </div>

          <div v-if="fetchedData.conclusion_abstract" class="mt-20">
            <h4>结题摘要</h4>
            <div class="code-block">{{ fetchedData.conclusion_abstract }}</div>
          </div>

          <div class="mt-20">
            <el-button @click="resetForm">清空</el-button>
            <el-button v-if="fetchedData && !reportResult.success"
                       type="success" @click="downloadReportSeparately" :loading="downloadSeparateLoading">
              {{ downloadSeparateLoading ? '下载中...' : '下载结题报告' }}
            </el-button>
          </div>
        </div>
      </div>

      <div class="card">
        <h3>高级查询</h3>
        <el-form :model="searchForm" label-position="top" @submit.native.prevent="handleSearch">
          <el-row :gutter="16">
            <el-col :xs="24" :sm="12">
              <el-form-item label="机构名称">
                <el-input
                  v-model="searchForm.unit"
                  placeholder="输入机构名称（支持模糊查询）"
                  clearable
                  :disabled="searchLoading"
                  @keyup.enter="handleSearch"
                />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="学科领域（申请代码）">
                <el-input
                  v-model="searchForm.code"
                  placeholder="输入申请代码（如：F0205）"
                  clearable
                  :disabled="searchLoading"
                  @keyup.enter="handleSearch"
                />
              </el-form-item>
            </el-col>
          </el-row>

          <div class="search-actions">
            <el-button type="primary" @click="handleSearch" :loading="searchLoading">
              {{ searchLoading ? '查询中...' : '查询' }}
            </el-button>
            <el-button @click="resetSearch" :disabled="searchLoading">重置</el-button>
            <el-button type="success" @click="exportResults" :disabled="searchResults.length === 0 || searchLoading">
              导出CSV
            </el-button>
          </div>
        </el-form>

        <div v-if="searchResults.length > 0" class="mt-20">
          <div class="search-header">
            <h4>查询结果 ({{ pagination.total }} 条)</h4>
          </div>

          <el-table
            :data="searchResults"
            stripe
            border
            style="width: 100%"
            @row-click="goToDetail"
          >
            <el-table-column prop="title" label="项目名称" min-width="200" show-overflow-tooltip />
            <el-table-column prop="approval_number" label="批准号" width="120" />
            <el-table-column prop="leader" label="负责人" width="100" />
            <el-table-column prop="unit" label="依托单位" min-width="150" show-overflow-tooltip />
            <el-table-column prop="funding" label="经费(万)" width="100" align="center">
              <template #default="scope">
                {{ scope.row.funding ? scope.row.funding.toFixed(1) : '-' }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" align="center">
              <template #default="scope">
                <el-button size="small" @click.stop="goToDetail(scope.row)">
                  详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-container mt-20" v-if="pagination.totalPages > 1">
            <el-pagination
              background
              layout="prev, pager, next, total"
              :current-page="pagination.page"
              :page-size="pagination.per_page"
              :total="pagination.total"
              @current-change="handlePageChange"
            />
          </div>
        </div>

        <div v-else-if="searchExecuted" class="empty-state mt-20">
          <el-empty description="未找到匹配的项目数据"></el-empty>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '../services/api'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'Query',
  data() {
    return {
      fetchForm: {
        url: '',
        autoDownload: true
      },
      fetchRules: {
        url: [
          { required: true, message: '请输入项目详情URL', trigger: 'blur' },
          {
            pattern: /^https?:\/\/kd\.nsfc\.cn\/finalDetails\?id=.+$/,
            message: '请输入有效的kd.nsfc.cn项目链接',
            trigger: 'blur'
          }
        ]
      },
      loading: false,
      fetchedData: null,

      // 下载进度
      downloadProgress: {
        show: false,
        message: '',
        title: '正在提取项目信息...',
        type: 'info',
        current_page: 0,
        collected_pages: 0,
        total_pages: null
      },

      // 报告下载结果
      reportResult: {
        show: false,
        success: false,
        title: '',
        type: 'info',
        filename: '',
        page_count: 0,
        report_id: '',
        message: ''
      },

      // 单独下载状态
      downloadSeparateLoading: false,

      searchForm: {
        unit: '',
        code: ''
      },
      searchResults: [],
      searchLoading: false,
      searchExecuted: false,
      pagination: {
        page: 1,
        per_page: 20,
        total: 0,
        totalPages: 0
      }
    }
  },
  methods: {
    async handleFetch() {
      try {
        await this.$refs.fetchForm.validate()
        this.loading = true

        // 重置状态
        this.resetDownloadStatus()

        // 如果需要下载，显示进度信息
        if (this.fetchForm.autoDownload) {
          this.downloadProgress.show = true
          this.downloadProgress.message = '开始获取项目信息...'
          this.downloadProgress.type = 'info'
        }

        const res = await api.fetchProject(this.fetchForm.url, this.fetchForm.autoDownload)

        if (res.success && res.data) {
          this.fetchedData = res.data
          ElMessage.success('项目信息获取成功')

          // 处理结题报告下载
          if (this.fetchForm.autoDownload && res.need_download_report) {
            // 开始下载结题报告
            await this.downloadReportForProject(res.project_id)
          } else {
            // 不需要下载，隐藏进度条
            this.downloadProgress.show = false
          }
        } else {
          ElMessage.error(res.error || '获取失败')
          this.downloadProgress.show = false
        }
      } catch (error) {
        ElMessage.error(error.message || '获取失败')
        this.downloadProgress.show = false
      } finally {
        this.loading = false
      }
    },

    async downloadReportForProject(projectId) {
      // 使用 SSE 实时获取进度
      this.downloadProgress.title = '正在下载结题报告...'
      this.downloadProgress.message = '正在连接服务器...'
      this.downloadProgress.type = 'info'

      try {
        // 创建 SSE 连接 - 使用完整URL
        const eventSource = new EventSource(`/api/projects/${projectId}/download-report`)

        return new Promise((resolve, reject) => {
          let completed = false

          // SSE 使用 message 事件接收所有数据
          eventSource.addEventListener('message', (event) => {
            if (completed) return

            try {
              const data = JSON.parse(event.data)
              console.log('SSE received:', data) // 调试日志

              if (data.type === 'start') {
                this.downloadProgress.title = '开始下载结题报告...'
                this.downloadProgress.message = data.message
                this.downloadProgress.current_page = 0
                this.downloadProgress.collected_pages = 0
                this.downloadProgress.total_pages = null
              } else if (data.type === 'progress') {
                // 更新进度信息
                const message = data.message
                const currentPage = data.current_page || 0
                const collectedPages = data.collected_pages || 0
                const totalPages = data.total_pages !== undefined ? data.total_pages : null
                
                // 更新页码信息
                this.downloadProgress.current_page = currentPage
                this.downloadProgress.collected_pages = collectedPages
                this.downloadProgress.total_pages = totalPages
                
                // 更新标题和消息
                if (currentPage > 0) {
                  if (totalPages) {
                    this.downloadProgress.title = `正在处理第 ${currentPage} / ${totalPages} 页...`
                  } else {
                    this.downloadProgress.title = `正在处理第 ${currentPage} 页...`
                  }
                } else {
                  // 从消息中提取页码信息作为备选
                  const pageMatch = message.match(/第\s*(\d+)\s*页/)
                  if (pageMatch) {
                    if (totalPages) {
                      this.downloadProgress.title = `正在下载第 ${pageMatch[1]} / ${totalPages} 页...`
                    } else {
                      this.downloadProgress.title = `正在下载第 ${pageMatch[1]} 页...`
                    }
                  } else {
                    this.downloadProgress.title = '正在下载结题报告...'
                  }
                }
                this.downloadProgress.message = message
              } else if (data.type === 'complete') {
                completed = true
                eventSource.close()

                this.downloadProgress.title = '下载完成！'
                this.downloadProgress.message = data.message
                this.downloadProgress.type = 'success'

                // 显示报告结果
                this.reportResult = {
                  show: true,
                  success: true,
                  title: '结题报告下载成功！',
                  type: 'success',
                  filename: data.filename,
                  page_count: data.page_count,
                  report_id: data.report_id,
                  message: data.message
                }
                ElMessage.success('结题报告下载成功')
                resolve(data)
              } else if (data.type === 'error') {
                completed = true
                eventSource.close()

                this.downloadProgress.title = '下载失败'
                this.downloadProgress.message = data.message
                this.downloadProgress.type = 'warning'

                this.reportResult = {
                  show: true,
                  success: false,
                  title: '结题报告下载失败',
                  type: 'warning',
                  message: data.message
                }
                ElMessage.error(data.message || '下载失败')
                reject(new Error(data.message))
              }
            } catch (parseError) {
              console.error('SSE 数据解析错误:', parseError)
            }
          })

          // SSE 连接错误处理
          eventSource.addEventListener('error', (error) => {
            if (completed) return
            console.error('SSE 连接错误:', error)
            eventSource.close()

            // 连接失败，显示错误
            this.downloadProgress.title = '连接失败'
            this.downloadProgress.message = '无法连接到服务器，请检查网络连接或稍后重试'
            this.downloadProgress.type = 'warning'
            
            this.reportResult = {
              show: true,
              success: false,
              title: '结题报告下载失败',
              type: 'warning',
              message: '无法连接到服务器，请检查网络连接或稍后重试'
            }
            ElMessage.error('无法连接到服务器，请检查网络连接或稍后重试')
            reject(new Error('SSE 连接失败'))
          })

          // 设置超时保护 - 5分钟后自动关闭
          setTimeout(() => {
            if (!completed) {
              console.log('SSE 超时')
              eventSource.close()
              
              this.downloadProgress.title = '下载超时'
              this.downloadProgress.message = '下载时间过长，请检查网络连接或稍后重试'
              this.downloadProgress.type = 'warning'
              
              this.reportResult = {
                show: true,
                success: false,
                title: '结题报告下载超时',
                type: 'warning',
                message: '下载时间过长，请检查网络连接或稍后重试'
              }
              ElMessage.error('下载超时，请检查网络连接或稍后重试')
              reject(new Error('下载超时'))
            }
          }, 3000000)

          // 浏览器关闭时清理连接
          window.addEventListener('beforeunload', () => {
            if (!completed) {
              eventSource.close()
            }
          })
        })
      } catch (error) {
        // 如果 SSE 创建失败，显示错误
        console.error('SSE 连接失败:', error.message)
        this.downloadProgress.title = '连接失败'
        this.downloadProgress.message = '无法创建连接，请检查网络连接或稍后重试'
        this.downloadProgress.type = 'warning'
        
        this.reportResult = {
          show: true,
          success: false,
          title: '结题报告下载失败',
          type: 'warning',
          message: '无法创建连接，请检查网络连接或稍后重试'
        }
        ElMessage.error('无法创建连接，请检查网络连接或稍后重试')
        throw error
      }
    },

    async downloadReportSeparately() {
      if (!this.fetchedData) return

      try {
        this.downloadSeparateLoading = true

        // 首先需要保存项目到数据库才能下载
        let projectId = null

        // 检查项目是否已存在
        const checkRes = await api.getProjects({ unit: '' })
        const existing = checkRes.data.find(p =>
          p.approval_number === this.fetchedData.approval_number
        )

        if (existing) {
          projectId = existing.id
        } else {
          // 保存项目
          const saveRes = await api.createProject(this.fetchedData)
          projectId = saveRes.project_id
        }

        // 重置下载状态，避免重复标题
        this.resetDownloadStatus()
        this.downloadProgress.show = true

        // 调用下载方法（下载方法内部会设置标题和消息）
        await this.downloadReportForProject(projectId)

      } catch (error) {
        ElMessage.error(error.message || '下载失败')
      } finally {
        this.downloadSeparateLoading = false
      }
    },

    async viewReport(reportId) {
      try {
        const res = await api.viewReport(reportId)
        if (res.success) {
          // 打开新窗口预览
          const url = `/api/pdf/preview/${reportId}`
          window.open(url, '_blank')
        } else {
          ElMessage.error(res.error || '预览失败')
        }
      } catch (error) {
        ElMessage.error(error.message || '预览失败')
      }
    },

    async downloadReport(reportId) {
      try {
        const res = await api.downloadReport(reportId)
        const url = window.URL.createObjectURL(new Blob([res], { type: 'application/pdf' }))
        const link = document.createElement('a')
        link.href = url
        link.download = this.reportResult.filename
        link.click()
        window.URL.revokeObjectURL(url)
        ElMessage.success('下载开始')
      } catch (error) {
        ElMessage.error(error.message || '下载失败')
      }
    },

    resetDownloadStatus() {
      this.downloadProgress = {
        show: false,
        message: '',
        title: '正在提取项目信息...',
        type: 'info',
        current_page: 0,
        collected_pages: 0,
        total_pages: null
      }
      this.reportResult = {
        show: false,
        success: false,
        title: '',
        type: 'info',
        filename: '',
        page_count: 0,
        report_id: '',
        message: ''
      }
    },

    resetForm() {
      this.fetchForm = { url: '', autoDownload: false }
      this.fetchedData = null
      this.resetDownloadStatus()
      if (this.$refs.fetchForm) {
        this.$refs.fetchForm.resetFields()
      }
    },

    async handleSearch() {
      if (!this.searchForm.unit && !this.searchForm.code) {
        ElMessage.warning('请输入查询条件')
        return
      }

      this.searchLoading = true
      this.searchExecuted = true

      try {
        const params = {
          page: this.pagination.page,
          per_page: this.pagination.per_page
        }

        if (this.searchForm.unit) params.unit = this.searchForm.unit
        if (this.searchForm.code) params.code = this.searchForm.code

        const res = await api.getProjects(params)

        if (res.success) {
          this.searchResults = res.data
          this.pagination = res.pagination
        } else {
          ElMessage.error(res.error || '查询失败')
        }
      } catch (error) {
        ElMessage.error(error.message || '查询失败')
      } finally {
        this.searchLoading = false
      }
    },

    resetSearch() {
      this.searchForm = { unit: '', code: '' }
      this.searchResults = []
      this.searchExecuted = false
      this.pagination = { page: 1, per_page: 20, total: 0, totalPages: 0 }
    },

    async handlePageChange(page) {
      this.pagination.page = page
      await this.handleSearch()
    },

    async exportResults() {
      try {
        const params = {}
        if (this.searchForm.unit) params.unit = this.searchForm.unit
        if (this.searchForm.code) params.code = this.searchForm.code

        const res = await api.exportProjects(params)

        // 创建下载链接
        const url = window.URL.createObjectURL(new Blob([res], { type: 'text/csv;charset=utf-8;' }))
        const link = document.createElement('a')
        link.href = url
        link.download = `projects_${new Date().getTime()}.csv`
        link.click()
        window.URL.revokeObjectURL(url)

        ElMessage.success('导出成功')
      } catch (error) {
        ElMessage.error(error.message || '导出失败')
      }
    },

    goToDetail(row) {
      this.$router.push(`/project/${row.id}`)
    }
  }
}
</script>

<style scoped>
.search-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.search-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.search-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

h4 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #303133;
}

.el-descriptions {
  margin-top: 12px;
}

.el-descriptions :deep(.el-descriptions__header) {
  margin-bottom: 12px;
}

.el-descriptions :deep(.el-descriptions__title) {
  font-weight: 600;
}

.mt-20 {
  margin-top: 20px;
}

.mb-20 {
  margin-bottom: 20px;
}

.download-progress {
  animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

.code-block {
  background-color: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 12px;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  color: #303133;
}
</style>
