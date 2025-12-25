<template>
  <div class="manage" style="height: 100%; overflow-y: auto;">
    <div class="container" style="min-height: 100%;">
      <h2 class="page-title">数据管理</h2>
      
      <div class="card mb-20">
        <h3>手动添加项目</h3>
        <el-form :model="manualForm" :rules="manualRules" ref="manualForm" label-position="top">
          <el-row :gutter="16">
            <el-col :xs="24" :sm="12">
              <el-form-item label="项目名称" prop="title">
                <el-input v-model="manualForm.title" placeholder="请输入项目名称" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="项目批准号" prop="approval_number">
                <el-input v-model="manualForm.approval_number" placeholder="请输入批准号" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="申请代码" prop="application_code">
                <el-input v-model="manualForm.application_code" placeholder="请输入申请代码" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="项目负责人" prop="leader">
                <el-input v-model="manualForm.leader" placeholder="请输入负责人姓名" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="依托单位" prop="unit">
                <el-input v-model="manualForm.unit" placeholder="请输入依托单位" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="开始日期" prop="start_date">
                <el-date-picker
                  v-model="manualForm.start_date"
                  type="date"
                  placeholder="选择开始日期"
                  format="YYYY-MM-DD"
                  value-format="YYYY-MM-DD"
                  style="width: 100%;"
                />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="结束日期" prop="end_date">
                <el-date-picker
                  v-model="manualForm.end_date"
                  type="date"
                  placeholder="选择结束日期"
                  format="YYYY-MM-DD"
                  value-format="YYYY-MM-DD"
                  style="width: 100%;"
                />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="资助经费（万元）" prop="funding">
                <el-input-number 
                  v-model="manualForm.funding" 
                  :precision="1" 
                  :step="0.1" 
                  :min="0"
                  style="width: 100%;"
                />
              </el-form-item>
            </el-col>
            <el-col :span="24">
              <el-form-item label="项目摘要" prop="abstract">
                <el-input
                  v-model="manualForm.abstract"
                  type="textarea"
                  :rows="2"
                  placeholder="请输入项目摘要"
                />
              </el-form-item>
            </el-col>
            <el-col :span="24">
              <el-form-item label="结题摘要" prop="conclusion_abstract">
                <el-input
                  v-model="manualForm.conclusion_abstract"
                  type="textarea"
                  :rows="2"
                  placeholder="请输入结题摘要"
                />
              </el-form-item>
            </el-col>
            <el-col :span="24">
              <el-form-item label="项目链接" prop="url">
                <el-input v-model="manualForm.url" placeholder="请输入项目详情URL（可选）" />
              </el-form-item>
            </el-col>
          </el-row>
          
          <div class="form-actions">
            <el-button type="primary" @click="handleManualAdd" :loading="adding">
              {{ adding ? '添加中...' : '添加项目' }}
            </el-button>
            <el-button @click="resetManualForm">重置</el-button>
          </div>
        </el-form>
      </div>

      <div class="card">
        <div class="search-header">
          <h3>项目列表</h3>
          <div class="header-actions">
            <el-button type="success" @click="exportAll" :disabled="allProjects.length === 0">
              导出全部
            </el-button>
            <el-button type="danger" @click="clearAll" :disabled="allProjects.length === 0">
              清空数据
            </el-button>
          </div>
        </div>

        <div class="search-form mb-20">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索项目名称、批准号、负责人、单位..."
            clearable
            @keyup.enter="handleSearch"
            @clear="handleSearch"
          >
            <template #append>
              <el-button @click="handleSearch" :loading="searchLoading">
                搜索
              </el-button>
            </template>
          </el-input>
        </div>

        <div v-if="filteredProjects.length > 0">
          <el-table
            :data="paginatedProjects"
            stripe
            border
            style="width: 100%"
            @row-click="goToDetail"
          >
            <el-table-column prop="title" label="项目名称" min-width="200" show-overflow-tooltip />
            <el-table-column prop="approval_number" label="批准号" width="120" />
            <el-table-column prop="leader" label="负责人" width="100" />
            <el-table-column prop="unit" label="依托单位" min-width="150" show-overflow-tooltip />
            <el-table-column prop="funding" label="经费" width="90" align="center">
              <template #default="scope">
                {{ scope.row.funding ? scope.row.funding.toFixed(1) : '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="reports_count" label="报告数" width="90" align="center">
              <template #default="scope">
                <el-tag :type="scope.row.reports_count > 0 ? 'success' : 'info'" size="small">
                  {{ scope.row.reports_count || 0 }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160" align="center">
              <template #default="scope">
                <el-button size="small" @click.stop="goToDetail(scope.row)">
                  详情
                </el-button>
                <el-button size="small" type="danger" @click.stop="deleteProject(scope.row.id)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-container mt-20" v-if="totalPages > 1">
            <el-pagination
              background
              layout="prev, pager, next, total, sizes"
              :current-page="currentPage"
              :page-size="pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="filteredProjects.length"
              @current-change="handlePageChange"
              @size-change="handleSizeChange"
            />
          </div>
        </div>

        <div v-else class="empty-state mt-20">
          <el-empty description="暂无项目数据">
            <div style="margin-top: 12px;">
              <p style="color: #909399; margin-bottom: 8px;">您可以：</p>
              <el-button type="primary" @click="$router.push('/query')">
                去获取项目信息
              </el-button>
            </div>
          </el-empty>
        </div>
      </div>

      <!-- 搜索历史 -->
      <div class="card mt-20" v-if="searchHistory.length > 0">
        <div class="search-header">
          <h3>搜索历史</h3>
          <el-button size="small" type="danger" @click="clearHistory">
            清空历史
          </el-button>
        </div>
        <el-timeline style="margin-top: 16px;">
          <el-timeline-item
            v-for="item in searchHistory"
            :key="item.id"
            :timestamp="formatDate(item.created_at)"
            placement="top"
          >
            <el-card>
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <span class="history-keyword">{{ item.keyword }}</span>
                  <el-tag size="small" style="margin-left: 8px;">
                    {{ item.search_type === 'unit' ? '机构' : item.search_type === 'code' ? '代码' : 'URL' }}
                  </el-tag>
                </div>
                <el-tag type="info" size="small">{{ item.results_count }} 条结果</el-tag>
              </div>
            </el-card>
          </el-timeline-item>
        </el-timeline>
      </div>
    </div>
  </div>
</template>

<script>
import api from '../services/api'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'Manage',
  data() {
    return {
      manualForm: {
        title: '',
        approval_number: '',
        application_code: '',
        leader: '',
        unit: '',
        start_date: '',
        end_date: '',
        funding: 0,
        abstract: '',
        conclusion_abstract: '',
        url: ''
      },
      manualRules: {
        title: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
        approval_number: [{ required: true, message: '请输入批准号', trigger: 'blur' }],
        unit: [{ required: true, message: '请输入依托单位', trigger: 'blur' }]
      },
      adding: false,
      
      allProjects: [],
      searchKeyword: '',
      searchLoading: false,
      currentPage: 1,
      pageSize: 10,
      
      searchHistory: []
    }
  },
  computed: {
    filteredProjects() {
      if (!this.searchKeyword) return this.allProjects
      
      const keyword = this.searchKeyword.toLowerCase()
      return this.allProjects.filter(project => {
        return (
          (project.title && project.title.toLowerCase().includes(keyword)) ||
          (project.approval_number && project.approval_number.toLowerCase().includes(keyword)) ||
          (project.leader && project.leader.toLowerCase().includes(keyword)) ||
          (project.unit && project.unit.toLowerCase().includes(keyword))
        )
      })
    },
    
    paginatedProjects() {
      const start = (this.currentPage - 1) * this.pageSize
      const end = start + this.pageSize
      return this.filteredProjects.slice(start, end)
    },
    
    totalPages() {
      return Math.ceil(this.filteredProjects.length / this.pageSize)
    }
  },
  methods: {
    async handleManualAdd() {
      try {
        await this.$refs.manualForm.validate()
        this.adding = true

        const res = await api.createProject(this.manualForm)

        if (res.success) {
          ElMessage.success('项目添加成功')
          this.resetManualForm()
          this.loadAllProjects()
        } else {
          ElMessage.error(res.error || '添加失败')
        }
      } catch (error) {
        ElMessage.error(error.message || '添加失败')
      } finally {
        this.adding = false
      }
    },

    resetManualForm() {
      this.manualForm = {
        title: '',
        approval_number: '',
        application_code: '',
        leader: '',
        unit: '',
        start_date: '',
        end_date: '',
        funding: 0,
        abstract: '',
        conclusion_abstract: '',
        url: ''
      }
      this.$refs.manualForm?.resetFields()
    },

    async loadAllProjects() {
      try {
        const res = await api.getProjects({ per_page: 1000 })
        if (res.success) {
          // 获取每个项目的报告数量
          this.allProjects = await Promise.all(
            res.data.map(async (project) => {
              const detailRes = await api.getProjectDetail(project.id)
              if (detailRes.success) {
                project.reports_count = detailRes.data.reports ? detailRes.data.reports.length : 0
              } else {
                project.reports_count = 0
              }
              return project
            })
          )
        }
      } catch (error) {
        ElMessage.error(error.message || '加载数据失败')
      }
    },

    async handleSearch() {
      if (!this.searchKeyword) {
        this.loadAllProjects()
        return
      }

      this.searchLoading = true
      try {
        const params = { per_page: 1000 }
        const keyword = this.searchKeyword.toLowerCase()
        
        // 先搜索所有项目
        const res = await api.getProjects(params)
        
        if (res.success) {
          // 过滤结果
          this.allProjects = res.data.filter(project => {
            return (
              (project.title && project.title.toLowerCase().includes(keyword)) ||
              (project.approval_number && project.approval_number.toLowerCase().includes(keyword)) ||
              (project.leader && project.leader.toLowerCase().includes(keyword)) ||
              (project.unit && project.unit.toLowerCase().includes(keyword))
            )
          })
          
          this.currentPage = 1
        }
      } catch (error) {
        ElMessage.error(error.message || '搜索失败')
      } finally {
        this.searchLoading = false
      }
    },

    async deleteProject(projectId) {
      try {
        await ElMessageBox.confirm(
          '确定要删除这个项目吗？关联的报告文件也将被删除。',
          '警告',
          { type: 'warning' }
        )

        const res = await api.deleteProject(projectId)
        if (res.success) {
          ElMessage.success('删除成功')
          this.loadAllProjects() // 刷新
        } else {
          ElMessage.error(res.error || '删除失败')
        }
      } catch (error) {
        if (error.message !== 'cancel') {
          ElMessage.error(error.message || '删除失败')
        }
      }
    },

    async clearAll() {
      try {
        await ElMessageBox.confirm(
          '确定要清空所有项目数据吗？所有报告文件也将被删除，此操作不可恢复！',
          '严重警告',
          { type: 'danger' }
        )

        // 获取所有项目
        const res = await api.getProjects({ per_page: 1000 })
        
        // 删除所有报告和项目
        for (const project of res.data) {
          if (project.reports) {
            for (const report of project.reports) {
              await api.deleteReport(report.id)
            }
          }
          await api.deleteProject(project.id)
        }

        ElMessage.success('所有数据已清空')
        this.allProjects = []
        this.searchKeyword = ''
        this.currentPage = 1
        
      } catch (error) {
        if (error.message !== 'cancel') {
          ElMessage.error(error.message || '清空失败')
        }
      }
    },

    async exportAll() {
      try {
        const res = await api.exportProjects()
        
        // 创建下载链接
        const url = window.URL.createObjectURL(new Blob([res], { type: 'text/csv;charset=utf-8;' }))
        const link = document.createElement('a')
        link.href = url
        link.download = `all_projects_${new Date().getTime()}.csv`
        link.click()
        window.URL.revokeObjectURL(url)

        ElMessage.success('导出成功')
      } catch (error) {
        ElMessage.error(error.message || '导出失败')
      }
    },

    async loadSearchHistory() {
      try {
        const res = await api.getSearchHistory(10)
        if (res.success) {
          this.searchHistory = res.data
        }
      } catch (error) {
        console.error('加载搜索历史失败:', error)
      }
    },

    async clearHistory() {
      try {
        await ElMessageBox.confirm('确定要清空搜索历史吗？', '提示', { type: 'warning' })
        await api.clearSearchHistory()
        this.searchHistory = []
        ElMessage.success('搜索历史已清空')
      } catch (error) {
        if (error.message !== 'cancel') {
          ElMessage.error(error.message || '清空失败')
        }
      }
    },

    formatDate(date) {
      if (!date) return '-'
      return new Date(date).toLocaleString('zh-CN')
    },

    handlePageChange(page) {
      this.currentPage = page
    },

    handleSizeChange(size) {
      this.pageSize = size
      this.currentPage = 1
    },

    goToDetail(row) {
      this.$router.push(`/project/${row.id}`)
    }
  },
  mounted() {
    this.loadAllProjects()
    this.loadSearchHistory()
  }
}
</script>

<style scoped>
.search-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.search-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.form-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}

.search-form {
  display: flex;
  gap: 8px;
  align-items: center;
}

.search-form .el-input {
  flex: 1;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.history-keyword {
  font-weight: 600;
  color: #409EFF;
}

.el-timeline-item :deep(.el-card) {
  background: #f5f7fa;
  border: none;
}

.el-timeline-item :deep(.el-card__body) {
  padding: 8px 12px;
}

.mt-20 {
  margin-top: 20px;
}

.mb-20 {
  margin-bottom: 20px;
}

.el-input-number {
  width: 100%;
}
</style>
