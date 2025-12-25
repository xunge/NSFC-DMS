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
        </el-form>

        <div v-if="fetchedData" class="mt-20">
          <el-alert
            title="获取成功！"
            type="success"
            :closable="false"
            class="mb-20"
          >
            项目信息已提取，您可以保存到数据库
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
            <el-button type="primary" @click="saveToDatabase">保存到数据库</el-button>
            <el-button @click="fetchedData = null">清空</el-button>
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
                  @keyup.enter="handleSearch"
                />
              </el-form-item>
            </el-col>
          </el-row>
          
          <div class="search-actions">
            <el-button type="primary" @click="handleSearch" :loading="searchLoading">
              {{ searchLoading ? '查询中...' : '查询' }}
            </el-button>
            <el-button @click="resetSearch">重置</el-button>
            <el-button type="success" @click="exportResults" :disabled="searchResults.length === 0">
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
        url: ''
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
        
        const res = await api.fetchProject(this.fetchForm.url)
        
        if (res.success && res.data) {
          this.fetchedData = res.data
          ElMessage.success('项目信息获取成功')
        } else {
          ElMessage.error(res.error || '获取失败')
        }
      } catch (error) {
        ElMessage.error(error.message || '获取失败')
      } finally {
        this.loading = false
      }
    },

    async saveToDatabase() {
      if (!this.fetchedData) return

      try {
        // 检查是否已存在 - 查询所有项目，然后根据批准号过滤
        const checkRes = await api.getProjects({ unit: '' }) // 查询所有项目
        const exists = checkRes.data.some(p => 
          p.approval_number === this.fetchedData.approval_number
        )

        if (exists) {
          const confirm = await ElMessageBox.confirm(
            '该批准号的项目已存在，是否覆盖更新？',
            '提示',
            { type: 'warning' }
          )
          
          if (confirm === 'confirm') {
            const existing = checkRes.data.find(p => 
              p.approval_number === this.fetchedData.approval_number
            )
            await api.updateProject(existing.id, this.fetchedData)
            ElMessage.success('项目信息已更新')
          }
        } else {
          await api.createProject(this.fetchedData)
          ElMessage.success('项目已保存到数据库')
        }

        this.fetchedData = null
        this.fetchForm.url = ''
      } catch (error) {
        if (error.message !== 'cancel') {
          ElMessage.error(error.message || '保存失败')
        }
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
</style>
