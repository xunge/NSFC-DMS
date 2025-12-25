#!/bin/bash

echo "========================================="
echo "国家自然科学基金查询系统启动脚本"
echo "========================================="

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到Python3，请先安装Python 3.7+"
    exit 1
fi

# 检查Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 错误：未找到Node.js，请先安装Node.js 16+"
    exit 1
fi

echo "✅ 环境检查通过"

# 安装后端依赖
echo ""
echo "📦 安装后端依赖..."
cd backend
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ 后端依赖安装失败"
    exit 1
fi
echo "✅ 后端依赖安装完成"
cd ..

# 安装前端依赖
echo ""
echo "📦 安装前端依赖..."
cd frontend
npm install
if [ $? -ne 0 ]; then
    echo "❌ 前端依赖安装失败"
    exit 1
fi
echo "✅ 前端依赖安装完成"
cd ..

echo ""
echo "========================================="
echo "启动服务..."
echo "========================================="

# 启动后端
echo "🚀 启动后端服务 (端口: 5000)..."
cd backend
source venv/bin/activate
python app.py &
BACKEND_PID=$!
cd ..

# 等待后端启动
echo "等待后端服务启动..."
sleep 3

# 检查后端是否正常启动
if curl -s http://localhost:5000/api/health > /dev/null; then
    echo "✅ 后端服务启动成功"
else
    echo "❌ 后端服务启动失败"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# 启动前端
echo "🚀 启动前端服务 (端口: 3000)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# 等待前端启动
echo "等待前端服务启动..."
sleep 5

# 检查前端是否正常启动
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ 前端服务启动成功"
else
    echo "❌ 前端服务启动失败"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 1
fi

echo ""
echo "========================================="
echo "🎉 系统启动成功！"
echo "========================================="
echo "前端访问: http://localhost:3000"
echo "后端API: http://localhost:5000"
echo ""
echo "按 Ctrl+C 停止服务"
echo "========================================="

# 等待用户中断
trap "echo ''; echo '正在停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '服务已停止'; exit 0" INT
wait
