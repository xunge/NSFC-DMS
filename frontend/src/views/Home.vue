<template>
  <div class="home" style="height: 100%; overflow-y: auto;">
    <div class="container" style="min-height: 100%;">
      <div class="hero-section">
        <h1>国家自然科学基金查询系统</h1>
        <p>帮助科研人员快速查询和管理历年国家自然科学基金资助情况</p>
        
        <div class="features">
          <el-row :gutter="20">
            <el-col :xs="24" :sm="8">
              <div class="feature-card">
                <div class="feature-icon">🔍</div>
                <h3>智能查询</h3>
                <p>支持按机构名称、学科领域等多维度查询</p>
              </div>
            </el-col>
            <el-col :xs="24" :sm="8">
              <div class="feature-card">
                <div class="feature-icon">📄</div>
                <h3>报告管理</h3>
                <p>支持结题报告PDF上传、在线查看和下载</p>
              </div>
            </el-col>
            <el-col :xs="24" :sm="8">
              <div class="feature-card">
                <div class="feature-icon">📊</div>
                <h3>数据导出</h3>
                <p>一键导出查询结果为CSV格式</p>
              </div>
            </el-col>
          </el-row>
        </div>

        <div class="quick-actions">
          <el-button type="primary" size="large" @click="$router.push('/query')">
            开始查询
          </el-button>
          <el-button size="large" @click="$router.push('/manage')">
            数据管理
          </el-button>
        </div>
      </div>

      <div class="card mt-20">
        <h3>使用说明</h3>
        <el-steps :active="3" finish-status="success" simple>
          <el-step title="获取项目链接" description="访问kd.nsfc.cn找到目标项目"></el-step>
          <el-step title="提取项目信息" description="输入URL获取项目基本信息"></el-step>
          <el-step title="管理数据" description="上传报告、查询、导出"></el-step>
        </el-steps>
      </div>

      <div class="card">
        <h3>注意事项</h3>
        <el-alert
          title="系统说明"
          type="info"
          :closable="false"
        >
          <ul style="margin: 10px 0; padding-left: 20px;">
            <li>系统不支持批量爬取，避免IP被封禁</li>
            <li>每次只能获取单个项目的详细信息</li>
            <li>结题报告需要通过浏览器插件下载后上传</li>
            <li>支持在线查看PDF内容</li>
          </ul>
        </el-alert>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Home'
}
</script>

<style scoped>
.home {
  min-height: calc(100vh - 120px);
}

.hero-section {
  text-align: center;
  padding: 40px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px;
  margin-bottom: 20px;
}

.hero-section h1 {
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 12px;
}

.hero-section p {
  font-size: 18px;
  opacity: 0.9;
  margin-bottom: 30px;
}

.features {
  margin: 30px 0;
}

.feature-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  padding: 24px;
  height: 100%;
  transition: all 0.3s ease;
}

.feature-card:hover {
  background: rgba(255, 255, 255, 0.15);
  transform: translateY(-2px);
}

.feature-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.feature-card h3 {
  font-size: 18px;
  margin-bottom: 8px;
  font-weight: 600;
}

.feature-card p {
  font-size: 14px;
  opacity: 0.8;
  line-height: 1.5;
}

.quick-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 30px;
}

.card h3 {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 16px;
  color: #303133;
}

.el-steps {
  margin-top: 16px;
}

@media (max-width: 768px) {
  .hero-section h1 {
    font-size: 28px;
  }
  
  .hero-section p {
    font-size: 16px;
  }
  
  .quick-actions {
    flex-direction: column;
  }
  
  .quick-actions .el-button {
    width: 100%;
  }
}
</style>
