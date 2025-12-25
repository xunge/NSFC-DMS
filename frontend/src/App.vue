<template>
  <div id="app">
    <el-container class="layout">
      <el-header class="header">
        <div class="header-content">
          <h1 class="title">国家自然科学基金查询系统</h1>
          <div class="nav-actions">
            <el-button 
              type="primary" 
              plain 
              size="small"
              @click="$router.push('/')"
              :class="{ 'active': $route.path === '/' }"
            >
              首页
            </el-button>
            <el-button 
              type="primary" 
              plain 
              size="small"
              @click="$router.push('/query')"
              :class="{ 'active': $route.path === '/query' }"
            >
              项目查询
            </el-button>
            <el-button 
              type="primary" 
              plain 
              size="small"
              @click="$router.push('/manage')"
              :class="{ 'active': $route.path === '/manage' }"
            >
              数据管理
            </el-button>
          </div>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script>
export default {
  name: 'App'
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
  background-color: #f5f7fa;
}

.layout {
  min-height: 100vh;
}

.header {
  background: linear-gradient(135deg, #409EFF 0%, #337ecc 100%);
  color: white;
  padding: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  padding: 0 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.title {
  font-size: 20px;
  font-weight: 600;
  color: white;
  margin: 0;
}

.nav-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.nav-actions .el-button {
  border: 1px solid rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.1);
  color: white;
  font-weight: 500;
  transition: all 0.3s ease;
}

.nav-actions .el-button:hover {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.5);
  transform: translateY(-1px);
}

.nav-actions .el-button.active {
  background: white;
  color: #409EFF;
  border-color: white;
  box-shadow: 0 2px 8px rgba(255, 255, 255, 0.3);
}

.nav-actions .el-button--plain {
  background: rgba(255, 255, 255, 0.1);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.nav-actions .el-button--plain:hover {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.5);
}

.nav-actions .el-button--plain.is-active {
  background: white;
  color: #409EFF;
  border-color: white;
}

.main {
  padding: 0;
  background: #f5f7fa;
  height: calc(100vh - 60px);
  overflow-y: auto;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 20px;
  color: #303133;
}

.card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  margin-bottom: 20px;
}

.text-center {
  text-align: center;
}

.mt-20 {
  margin-top: 20px;
}

.mb-20 {
  margin-bottom: 20px;
}

.full-width {
  width: 100%;
}

/* Element Plus 自定义样式 */
.el-button--primary {
  background: #409EFF;
  border-color: #409EFF;
}

.el-button--primary:hover {
  background: #337ecc;
  border-color: #337ecc;
}

.el-input__wrapper {
  border-radius: 4px;
}

.el-card {
  border-radius: 8px;
  border: none;
}

.el-card__header {
  border-bottom: 1px solid #ebeef5;
  padding: 16px 20px;
  font-weight: 600;
  color: #303133;
}

.el-table {
  border-radius: 8px;
  overflow: hidden;
}

.el-table__header-wrapper {
  background: #f5f7fa;
}

.el-tag {
  border-radius: 4px;
}

.el-drawer__header {
  background: #f5f7fa;
  border-bottom: 1px solid #ebeef5;
  padding: 20px;
}

.el-drawer__body {
  padding: 20px;
}

.code-block {
  background: #f5f7fa;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 12px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
  color: #606266;
  white-space: pre-wrap;
  word-break: break-all;
}

.pdf-viewer {
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 16px;
  background: #fff;
  max-height: 500px;
  overflow-y: auto;
  line-height: 1.8;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #909399;
}

.empty-state .el-icon {
  font-size: 48px;
  margin-bottom: 16px;
  color: #c0c4cc;
}

.loading-container {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.search-form {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px;
  align-items: start;
}

@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    height: auto;
    padding: 10px;
  }
  
  .title {
    margin-bottom: 10px;
  }
  
  .search-form {
    grid-template-columns: 1fr;
  }
  
  .container {
    padding: 10px;
  }
}
</style>
