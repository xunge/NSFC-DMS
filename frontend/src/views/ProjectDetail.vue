<template>
  <div class="project-detail" style="height: 100%; overflow-y: auto;">
    <div class="container" style="min-height: 100%;">
      <div class="detail-header">
          <div class="header-left">
            <el-button @click="$router.back()" class="back-btn"><el-icon><ArrowLeft /></el-icon>返回</el-button>
            <div class="header-title">
              <h2 class="page-title">项目详情</h2>
              <span class="subtitle">查看和管理项目详细信息</span>
            </div>
          </div>
        <div class="header-actions">
          <el-button type="primary" @click="editProject"><el-icon><Edit /></el-icon>编辑项目</el-button>
          <el-button type="danger" @click="deleteProject"><el-icon><Delete /></el-icon>删除项目</el-button>
        </div>
      </div>

      <div v-if="loading" class="loading-container">
        <div class="loading-spinner">加载中...</div>
      </div>

      <div v-else-if="project" class="mt-20">
        <!-- 基本信息卡片 -->
        <div class="card">
          <h3>基本信息</h3>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="项目名称" :span="2">
              {{ project.title }}
            </el-descriptions-item>
            <el-descriptions-item label="项目批准号">
              {{ project.approval_number || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="申请代码">
              {{ project.application_code || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="项目负责人">
              {{ project.leader || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="依托单位">
              {{ project.unit || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="研究期限">
              {{ project.start_date }} 至 {{ project.end_date }}
            </el-descriptions-item>
            <el-descriptions-item label="资助经费">
              {{ project.funding ? project.funding + ' 万元' : '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">
              {{ formatDate(project.created_at) }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 摘要信息 -->
        <div class="card" v-if="project.abstract || project.conclusion_abstract">
          <h3>摘要信息</h3>
          
          <div v-if="project.abstract" class="mb-20">
            <h4>项目摘要</h4>
            <div class="code-block">{{ project.abstract }}</div>
          </div>

          <div v-if="project.conclusion_abstract">
            <h4>结题摘要</h4>
            <div class="code-block">{{ project.conclusion_abstract }}</div>
          </div>
        </div>

        <!-- 项目链接 -->
        <div class="card" v-if="project.url">
          <h3>项目链接</h3>
          <el-link type="primary" :href="project.url" target="_blank" style="font-size: 14px;">
            {{ project.url }}
          </el-link>
        </div>

        <!-- 结题报告管理 -->
        <div class="card">
          <div class="report-header">
            <h3>结题报告</h3>
            <el-button type="primary" size="small" @click="showUpload = true"><el-icon><Upload /></el-icon>
              上传报告
            </el-button>
          </div>

          <div v-if="project.reports && project.reports.length > 0" class="mt-20">
            <el-table :data="project.reports" stripe border>
              <el-table-column prop="filename" label="文件名" min-width="200" show-overflow-tooltip />
              <el-table-column prop="file_size" label="文件大小" width="120" align="center">
                <template #default="scope">
                  {{ formatFileSize(scope.row.file_size) }}
                </template>
              </el-table-column>
              <el-table-column prop="upload_date" label="上传时间" width="160" align="center">
                <template #default="scope">
                  {{ formatDate(scope.row.upload_date) }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="200" align="center">
                <template #default="scope">
                  <el-button size="small" @click="viewReport(scope.row.id)">
                    查看
                  </el-button>
                  <el-button size="small" type="primary" @click="downloadReport(scope.row.id)">
                    下载
                  </el-button>
                  <el-button size="small" type="danger" @click="deleteReport(scope.row.id)">
                    删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <div v-else class="empty-state mt-20">
            <el-empty description="暂无结题报告">
              <el-button type="primary" @click="showUpload = true">上传报告</el-button>
            </el-empty>
          </div>
        </div>

        <!-- 操作按钮组 -->
        <!-- <div class="card">
          <h3>操作</h3>
          <el-button-group>
            <el-button @click="editProject" icon="Edit">编辑信息</el-button>
            <el-button type="danger" @click="deleteProject" icon="Delete">删除项目</el-button>
          </el-button-group>
        </div> -->
      </div>

      <!-- 上传报告对话框 -->
      <el-dialog
        v-model="showUpload"
        title="上传结题报告"
        width="500px"
        :before-close="handleUploadClose"
      >
        <el-form :model="uploadForm" ref="uploadForm" label-position="top">
          <el-form-item 
            label="选择PDF文件" 
            prop="file"
            :rules="[{ required: true, message: '请选择PDF文件', trigger: 'change' }]"
          >
            <el-upload
              ref="upload"
              action="#"
              :auto-upload="false"
              :on-change="handleFileChange"
              :file-list="fileList"
              accept=".pdf"
              :limit="1"
            >
              <template #trigger>
                <el-button type="primary">选择文件</el-button>
              </template>
              <div class="upload-tip" style="margin-top: 8px; font-size: 12px; color: #909399;">
                只支持PDF格式，文件大小不超过1000MB<br>
                文件名格式：申请代码_项目名称_项目批准号.pdf
              </div>
            </el-upload>
          </el-form-item>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="showUpload = false">取消</el-button>
            <el-button type="primary" @click="handleUpload" :loading="uploading">
              {{ uploading ? '上传中...' : '上传' }}
            </el-button>
          </span>
        </template>
      </el-dialog>

      <!-- 查看PDF对话框 -->
      <el-dialog
        v-model="showPdfViewer"
        title="PDF预览"
        width="90%"
        fullscreen
        :before-close="handlePdfClose"
      >
        <div v-if="pdfUrl" class="pdf-preview-container">
          <iframe 
            :src="pdfUrl" 
            width="100%" 
            height="100%"
            frameborder="0"
            style="border: none; border-radius: 8px;"
          >
          </iframe>
        </div>
        <div v-else class="loading-container">
          <div class="loading-spinner">正在加载PDF...</div>
        </div>
      </el-dialog>

      <!-- 编辑对话框 -->
      <el-dialog
        v-model="showEdit"
        title="编辑项目信息"
        width="700px"
        :before-close="handleEditClose"
      >
        <el-form :model="editForm" :rules="editRules" ref="editForm" label-position="top">
          <el-row :gutter="16">
            <el-col :span="24">
              <el-form-item label="项目名称" prop="title">
                <el-input v-model="editForm.title" placeholder="请输入项目名称" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="项目批准号" prop="approval_number">
                <el-input v-model="editForm.approval_number" placeholder="请输入批准号" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="申请代码" prop="application_code">
                <el-input v-model="editForm.application_code" placeholder="请输入申请代码" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="项目负责人" prop="leader">
                <el-input v-model="editForm.leader" placeholder="请输入负责人姓名" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="依托单位" prop="unit">
                <el-input v-model="editForm.unit" placeholder="请输入依托单位" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="开始日期" prop="start_date">
                <el-date-picker
                  v-model="editForm.start_date"
                  type="date"
                  placeholder="选择开始日期"
                  format="YYYY-MM-DD"
                  value-format="YYYY-MM-DD"
                  style="width: 100%;"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="结束日期" prop="end_date">
                <el-date-picker
                  v-model="editForm.end_date"
                  type="date"
                  placeholder="选择结束日期"
                  format="YYYY-MM-DD"
                  value-format="YYYY-MM-DD"
                  style="width: 100%;"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="资助经费（万元）" prop="funding">
                <el-input-number 
                  v-model="editForm.funding" 
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
                  v-model="editForm.abstract"
                  type="textarea"
                  :rows="3"
                  placeholder="请输入项目摘要"
                />
              </el-form-item>
            </el-col>
            <el-col :span="24">
              <el-form-item label="结题摘要" prop="conclusion_abstract">
                <el-input
                  v-model="editForm.conclusion_abstract"
                  type="textarea"
                  :rows="3"
                  placeholder="请输入结题摘要"
                />
              </el-form-item>
            </el-col>
            <el-col :span="24">
              <el-form-item label="项目链接" prop="url">
                <el-input v-model="editForm.url" placeholder="请输入项目详情URL" />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="showEdit = false">取消</el-button>
            <el-button type="primary" @click="handleUpdate" :loading="updating">
              {{ updating ? '更新中...' : '更新' }}
            </el-button>
          </span>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script>
import api from '../services/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Edit,
  Delete,
  Upload,
  Download,
  View,
  ArrowLeft
} from '@element-plus/icons-vue'

export default {
  name: 'ProjectDetail',
  components: {
    Edit,
    Delete,
    Upload,
    Download,
    View,
    ArrowLeft
  },
  props: ['id'],
  data() {
    return {
      project: null,
      loading: false,
      
      // 上传相关
      showUpload: false,
      uploading: false,
      uploadForm: {
        file: null
      },
      fileList: [],
      
      // PDF查看相关
      showPdfViewer: false,
      pdfUrl: null,
      
      // 编辑相关
      showEdit: false,
      updating: false,
      editForm: {
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
      editRules: {
        title: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
        approval_number: [{ required: true, message: '请输入批准号', trigger: 'blur' }],
        unit: [{ required: true, message: '请输入依托单位', trigger: 'blur' }]
      }
    }
  },
  mounted() {
    this.loadProject()
  },
  methods: {
    async loadProject() {
      this.loading = true
      try {
        const res = await api.getProjectDetail(this.id)
        if (res.success) {
          this.project = res.data
        } else {
          ElMessage.error(res.error || '加载失败')
        }
      } catch (error) {
        ElMessage.error(error.message || '加载失败')
      } finally {
        this.loading = false
      }
    },

    formatDate(date) {
      if (!date) return '-'
      return new Date(date).toLocaleString('zh-CN')
    },

    formatFileSize(bytes) {
      if (!bytes) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    },

    handleFileChange(file) {
      this.uploadForm.file = file.raw
      this.fileList = [file]
    },

    async handleUpload() {
      try {
        await this.$refs.uploadForm.validate()
        
        if (!this.uploadForm.file) {
          ElMessage.warning('请选择要上传的文件')
          return
        }

        this.uploading = true
        
        const formData = new FormData()
        formData.append('file', this.uploadForm.file)
        formData.append('project_id', this.id)

        const res = await api.uploadReport(formData)

        if (res.success) {
          ElMessage.success('上传成功')
          this.showUpload = false
          this.uploadForm.file = null
          this.fileList = []
          this.loadProject() // 刷新数据
        } else {
          ElMessage.error(res.error || '上传失败')
        }
      } catch (error) {
        ElMessage.error(error.message || '上传失败')
      } finally {
        this.uploading = false
      }
    },

    handleUploadClose() {
      this.showUpload = false
      this.uploadForm.file = null
      this.fileList = []
    },

    async viewReport(reportId) {
      this.showPdfViewer = true
      this.pdfUrl = null

      try {
        // 使用专门的预览接口
        const baseUrl = window.location.origin
        const pdfUrl = `${baseUrl}/api/pdf/preview/${reportId}`
        
        // 验证PDF文件是否存在
        const testResponse = await fetch(pdfUrl, { method: 'HEAD' })
        if (!testResponse.ok) {
          throw new Error('PDF文件不存在或无法访问')
        }
        
        // 设置iframe的src，浏览器会自动预览
        this.pdfUrl = pdfUrl
        
      } catch (error) {
        ElMessage.error('预览失败: ' + error.message)
        this.showPdfViewer = false
      }
    },

    handlePdfClose() {
      this.showPdfViewer = false
      this.pdfUrl = null
    },

    async downloadReport(reportId) {
      try {
        const res = await api.downloadReport(reportId)
        
        // 获取文件名
        const report = this.project.reports.find(r => r.id === reportId)
        const filename = report ? report.filename : 'report.pdf'
        
        // 创建下载链接
        const url = window.URL.createObjectURL(new Blob([res], { type: 'application/pdf' }))
        const link = document.createElement('a')
        link.href = url
        link.download = filename
        
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
        
        ElMessage.success('下载成功')
      } catch (error) {
        ElMessage.error(error.message || '下载失败')
      }
    },

    async deleteReport(reportId) {
      try {
        await ElMessageBox.confirm(
          '确定要删除这个报告文件吗？此操作不可恢复。',
          '警告',
          { type: 'warning' }
        )

        const res = await api.deleteReport(reportId)
        if (res.success) {
          ElMessage.success('删除成功')
          this.loadProject() // 刷新数据
        } else {
          ElMessage.error(res.error || '删除失败')
        }
      } catch (error) {
        if (error.message !== 'cancel') {
          ElMessage.error(error.message || '删除失败')
        }
      }
    },

    editProject() {
      // 填充编辑表单
      this.editForm = {
        title: this.project.title,
        approval_number: this.project.approval_number || '',
        application_code: this.project.application_code || '',
        leader: this.project.leader || '',
        unit: this.project.unit || '',
        start_date: this.project.start_date,
        end_date: this.project.end_date,
        funding: this.project.funding || 0,
        abstract: this.project.abstract || '',
        conclusion_abstract: this.project.conclusion_abstract || '',
        url: this.project.url || ''
      }
      this.showEdit = true
    },

    handleEditClose() {
      this.showEdit = false
      this.$refs.editForm?.resetFields()
    },

    async handleUpdate() {
      try {
        await this.$refs.editForm.validate()
        this.updating = true

        const res = await api.updateProject(this.id, this.editForm)

        if (res.success) {
          ElMessage.success('更新成功')
          this.showEdit = false
          this.loadProject() // 刷新详情
        } else {
          ElMessage.error(res.error || '更新失败')
        }
      } catch (error) {
        ElMessage.error(error.message || '更新失败')
      } finally {
        this.updating = false
      }
    },

    async deleteProject() {
      try {
        await ElMessageBox.confirm(
          '确定要删除这个项目吗？所有关联的报告文件也将被删除，此操作不可恢复。',
          '严重警告',
          { type: 'danger' }
        )

        const res = await api.deleteProject(this.id)
        if (res.success) {
          ElMessage.success('删除成功')
          this.$router.back() // 返回上一页
        } else {
          ElMessage.error(res.error || '删除失败')
        }
      } catch (error) {
        if (error.message !== 'cancel') {
          ElMessage.error(error.message || '删除失败')
        }
      }
    }
  }
}
</script>

<style scoped>
/* 头部样式 */
.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding: 20px;
  background: linear-gradient(135deg, #409EFF 0%, #337ecc 100%);
  border-radius: 12px;
  color: white;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.back-btn {
  background: rgba(255, 255, 255, 0.2) !important;
  border: 1px solid rgba(255, 255, 255, 0.3) !important;
  color: white !important;
  font-weight: 500;
  transition: all 0.3s ease;
}

.back-btn:hover {
  background: rgba(255, 255, 255, 0.3) !important;
  transform: translateX(-2px);
}

.header-title {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.header-title .page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: white;
}

.header-title .subtitle {
  font-size: 13px;
  opacity: 0.9;
  font-weight: 400;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.header-actions .el-button {
  height: 36px;
  padding: 0 16px;
  border-radius: 6px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.header-actions .el-button--primary {
  background: #fff;
  color: #409EFF;
  border: none;
}

.header-actions .el-button--primary:hover {
  background: #f5f5f5;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(255, 255, 255, 0.3);
}

.header-actions .el-button--danger {
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
}

.header-actions .el-button--danger:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: translateY(-1px);
}

/* 报告头部样式 */
.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.report-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

/* 上传提示 */
.upload-tip {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}

/* PDF预览容器 */
.pdf-preview-container {
  background: #fff;
  height: 100%;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #ebeef5;
}

.pdf-preview-container iframe {
  background: #fff;
  min-height: 80vh;
}

/* PDF查看器（文本模式，备用） */
.pdf-viewer {
  background: #fff;
  padding: 20px;
  max-height: 70vh;
  overflow-y: auto;
  line-height: 1.8;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

.pdf-viewer pre {
  white-space: pre-wrap;
  word-break: break-all;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  color: #303133;
}

/* 对话框样式 */
.el-dialog :deep(.el-dialog__body) {
  padding: 20px;
}

.el-dialog :deep(.el-dialog__header) {
  background: #f5f7fa;
  border-bottom: 1px solid #ebeef5;
  padding: 16px 20px;
}

.el-dialog :deep(.el-dialog__title) {
  font-weight: 600;
  color: #303133;
}

/* 描述列表 */
.el-descriptions {
  margin-top: 12px;
}

.el-descriptions :deep(.el-descriptions__header) {
  margin-bottom: 12px;
}

.el-descriptions :deep(.el-descriptions__title) {
  font-weight: 600;
  color: #303133;
}

.el-descriptions :deep(.el-descriptions__table) {
  border-radius: 6px;
  overflow: hidden;
}

.el-descriptions :deep(.el-descriptions__label) {
  background: #f5f7fa;
  font-weight: 500;
  color: #606266;
}

.el-descriptions :deep(.el-descriptions__content) {
  color: #303133;
}

/* 表单样式 */
.el-form-item {
  margin-bottom: 16px;
}

.el-form-item :deep(.el-form-item__label) {
  font-weight: 500;
  color: #303133;
  margin-bottom: 8px;
}

.el-input-number {
  width: 100%;
}

/* 按钮组 */
.el-button-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.el-button-group .el-button {
  border-radius: 6px;
  font-weight: 500;
}

/* 表格样式 */
.el-table {
  border-radius: 8px;
  overflow: hidden;
}

.el-table :deep(.el-table__header-wrapper) {
  background: #f5f7fa;
}

.el-table :deep(.el-table__header) {
  background: #f5f7fa;
}

.el-table :deep(.el-table__header th) {
  background: #f5f7fa;
  color: #606266;
  font-weight: 600;
}

.el-table :deep(.el-table__body tr:hover) {
  background: #f5f7fa;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 40px 20px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px dashed #d9d9d9;
}

.empty-state :deep(.el-empty__description) {
  color: #909399;
}

/* 工具类 */
.mt-20 {
  margin-top: 20px;
}

.mb-20 {
  margin-bottom: 20px;
}

.loading-container {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-spinner {
  font-size: 16px;
  color: #909399;
  padding: 20px;
  text-align: center;
}

.loading-spinner::after {
  content: '';
  display: block;
  width: 20px;
  height: 20px;
  margin: 10px auto;
  border: 2px solid #409EFF;
  border-radius: 50%;
  border-top-color: transparent;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .detail-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  
  .header-left {
    width: 100%;
    justify-content: space-between;
  }
  
  .header-actions {
    width: 100%;
    justify-content: flex-end;
  }
  
  .header-title .page-title {
    font-size: 20px;
  }
}

/* 动画效果 */
.detail-header {
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 自定义滚动条 */
.project-detail::-webkit-scrollbar {
  width: 8px;
}

.project-detail::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.project-detail::-webkit-scrollbar-thumb {
  background: #c0c4cc;
  border-radius: 4px;
}

.project-detail::-webkit-scrollbar-thumb:hover {
  background: #909399;
}
</style>
