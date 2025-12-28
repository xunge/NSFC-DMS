# NSFC-DMS - 国家自然科学基金查询系统

<div align="center">

![NSFC-DMS](https://img.shields.io/badge/NSFC--DMS-国家自然科学基金查询系统-blue)
![Python](https://img.shields.io/badge/Python-3.7%2B-blue)
![Flask](https://img.shields.io/badge/Flask-2.3.3-green)
![Vue.js](https://img.shields.io/badge/Vue-3.3.4-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

一个基于 Flask + Vue 3 的国家自然科学基金项目信息管理系统，支持自动抓取、数据管理、PDF报告上传与预览

</div>

## ✨ 功能特性

### 🔍 数据获取
- **URL 导入**: 支持通过项目详情页 URL 快速导入项目数据
- **自动抓取**: 通过 Selenium + Edge 浏览器自动从 NSFC 官网抓取项目信息
- **智能解析**: 自动提取项目名称、批准号、负责人、依托单位、资助经费、摘要等关键信息

### 📊 数据管理
- **项目管理**: 完整的 CRUD 操作（创建、读取、更新、删除）
- **条件查询**: 支持按依托单位、申请代码进行筛选查询
- **分页展示**: 支持分页加载，优化大数据量展示
- **数据导出**: 支持导出项目列表为 CSV 格式（Excel 兼容）

### 📄 PDF 报告管理
- **PDF 上传**: 支持上传结题报告 PDF 文件
- **智能命名**: 自动生成规范文件名（申请代码_项目名称_批准号.pdf）
- **内容预览**: 在线提取并显示 PDF 文本内容
- **文件下载**: 支持 PDF 文件下载
- **文件预览**: 浏览器原生 PDF 预览支持

### 🔍 搜索历史
- **记录追踪**: 自动记录所有搜索操作
- **历史查看**: 支持查看最近的搜索记录
- **清空功能**: 可一键清空搜索历史

## 🏗️ 项目架构

```
NSFC-DMS/
├── backend/                    # 后端服务 (Flask)
│   ├── app.py                 # 主应用文件（API 接口）
│   ├── requirements.txt       # Python 依赖
│   ├── nsfc.db               # SQLite 数据库
│   ├── uploads/              # PDF 文件存储目录
│   └── venv/                 # Python 虚拟环境
├── frontend/                  # 前端服务 (Vue 3)
│   ├── src/
│   │   ├── App.vue          # 根组件
│   │   ├── main.js          # 入口文件
│   │   ├── router/          # 路由配置
│   │   ├── services/        # API 服务
│   │   └── views/           # 页面组件
│   ├── package.json         # Node.js 依赖
│   └── vite.config.js       # Vite 配置
├── drivers/                  # 浏览器驱动
│   └── msedgedriver        # Edge 驱动程序
├── start.sh                 # 一键启动脚本
├── README.md                # 项目文档
└── LICENSE                  # MIT 许可证
```

## 🚀 快速开始

### 前置要求

- **Python**: 3.7+
- **Node.js**: 16+
- **Microsoft Edge**: 已安装（用于 Selenium 自动化）
- **msedgedriver**: 需与 Edge 版本匹配

### 安装步骤

#### 1. 克隆项目
```bash
git clone <repository-url>
cd NSFC-DMS
```

#### 2. 准备浏览器驱动
确保 `drivers/msedgedriver` 存在且可执行：
```bash
# Linux/macOS
chmod +x drivers/msedgedriver

# Windows
# 确保 msedgedriver.exe 在 drivers/ 目录下
```

#### 3. 一键启动（推荐）
```bash
./start.sh
```

脚本会自动：
- 检查环境依赖
- 创建 Python 虚拟环境
- 安装前后端依赖
- 启动后端服务（端口 5002）
- 启动前端服务（端口 3000）

#### 4. 手动启动

**后端服务：**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

**前端服务：**
```bash
cd frontend
npm install
npm run dev
```

### 访问系统

- **前端**: http://localhost:3000
- **后端 API**: http://localhost:5002
- **健康检查**: http://localhost:5002/api/health

## 📖 使用指南

### 1. 项目查询页面

**自动抓取项目信息：**
1. 访问 NSFC 官网找到目标项目
2. 复制项目详情页 URL
3. 在"项目查询"页面粘贴 URL
4. 点击"抓取项目信息"
5. 系统自动保存项目到数据库

**查询已有项目：**
- 按依托单位筛选
- 按申请代码筛选
- 支持分页浏览

### 2. 数据管理页面

**项目管理：**
- 查看所有项目列表
- 点击"详情"查看完整信息
- 支持手动添加新项目
- 编辑或删除项目

**PDF 报告管理：**
- 上传结题报告 PDF
- 在线预览 PDF 内容
- 下载 PDF 文件
- 删除 PDF 文件

### 3. 数据导出

在数据管理页面点击"导出 CSV"，可将当前筛选结果导出为 Excel 兼容的 CSV 文件。

## 🔧 API 接口文档

### 健康检查
```
GET /api/health
```

### 项目操作

**获取项目列表**
```
GET /api/projects?unit=&code=&page=1&per_page=20
```

**获取项目详情**
```
GET /api/projects/<project_id>
```

**自动抓取项目**
```
POST /api/projects/fetch
Body: { "url": "https://kd.nsfc.gov.cn/..." }
```

**创建项目**
```
POST /api/projects
Body: { "title": "...", "approval_number": "...", ... }
```

**更新项目**
```
PUT /api/projects/<project_id>
Body: { "title": "...", ... }
```

**删除项目**
```
DELETE /api/projects/<project_id>
```

### PDF 报告操作

**上传 PDF**
```
POST /api/reports/upload
Form: { "file": <pdf-file>, "project_id": "..." }
```

**查看 PDF 内容**
```
GET /api/reports/<report_id>/view
```

**下载 PDF**
```
GET /api/reports/<report_id>/download
```

**预览 PDF**
```
GET /api/pdf/preview/<report_id>
```

**删除 PDF**
```
DELETE /api/reports/<report_id>
```

### 数据导出

**导出项目列表**
```
GET /api/export/projects?unit=&code=
```

### 搜索历史

**获取搜索历史**
```
GET /api/search/history?limit=10
```

**清空搜索历史**
```
DELETE /api/search/history
```

## 🗄️ 数据库结构

### projects 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT | 主键 UUID |
| title | TEXT | 项目名称 |
| approval_number | TEXT | 项目批准号 |
| application_code | TEXT | 申请代码 |
| leader | TEXT | 项目负责人 |
| unit | TEXT | 依托单位 |
| start_date | TEXT | 开始日期 |
| end_date | TEXT | 结束日期 |
| funding | REAL | 资助经费（万元） |
| abstract | TEXT | 项目摘要 |
| conclusion_abstract | TEXT | 结题摘要 |
| url | TEXT | 项目 URL |
| created_at | TIMESTAMP | 创建时间 |

### reports 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT | 主键 UUID |
| project_id | TEXT | 外键，关联项目 |
| filename | TEXT | 文件名 |
| file_path | TEXT | 文件路径 |
| file_size | INTEGER | 文件大小 |
| upload_date | TIMESTAMP | 上传时间 |

### search_history 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键自增 |
| keyword | TEXT | 搜索关键词 |
| search_type | TEXT | 搜索类型 |
| results_count | INTEGER | 结果数量 |
| created_at | TIMESTAMP | 创建时间 |

## 🔧 技术栈

### 后端
- **Flask**: Web 框架
- **Flask-CORS**: 跨域支持
- **SQLite**: 数据库
- **Selenium**: 自动化浏览器
- **PyMuPDF**: PDF 处理
- **BeautifulSoup**: HTML 解析

### 前端
- **Vue 3**: 渐进式框架
- **Vue Router**: 路由管理
- **Element Plus**: UI 组件库
- **Axios**: HTTP 客户端
- **Vite**: 构建工具

## ⚙️ 配置说明

### 后端配置 (app.py)
```python
# 上传配置
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
MAX_CONTENT_LENGTH = 1000 * 1024 * 1024  # 1000MB

# 数据库
DATABASE = 'nsfc.db'

# 服务配置
HOST = '0.0.0.0'
PORT = 5002
```

### 前端配置 (vite.config.js)
```javascript
export default defineConfig({
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5002',
        changeOrigin: true
      }
    }
  }
})
```

## 🐛 常见问题

### Q: 自动抓取失败？
**A:** 检查以下几点：
1. Edge 浏览器已安装
2. msedgedriver 版本匹配
3. 网络连接正常
4. URL 格式正确（必须包含 kd.nsfc.cn）

### Q: PDF 上传失败？
**A:** 检查：
1. 文件大小是否超过 1000MB 限制
2. 文件格式是否为 PDF
3. 项目 ID 是否正确

### Q: 前端无法连接后端？
**A:** 检查：
1. 后端服务是否正常运行
2. 端口是否被占用（默认 5002）
3. CORS 配置是否正确

### Q: 数据库初始化失败？
**A:** 检查：
1. 文件读写权限
2. 磁盘空间是否充足
3. 删除 nsfc.db 重新启动（数据会丢失）

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [Flask](https://flask.palletsprojects.com/) - Python Web 框架
- [Vue.js](https://vuejs.org/) - 前端框架
- [Element Plus](https://element-plus.org/) - UI 组件库
- [Selenium](https://www.selenium.dev/) - 自动化测试工具

## 📞 联系方式

如有问题或建议，请通过 Issue 提交。

---

<div align="center">
Made with ❤️ for xunge research
</div>
