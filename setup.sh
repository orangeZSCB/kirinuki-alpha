#!/bin/bash

# KiriNuki 快速启动指南

echo "=== KiriNuki 快速启动指南 ==="
echo ""

# 检查依赖
echo "检查依赖..."
MISSING_DEPS=0

if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    MISSING_DEPS=1
else
    echo "✓ Python3: $(python3 --version)"
fi

if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装"
    MISSING_DEPS=1
else
    echo "✓ Node.js: $(node --version)"
fi

if ! command -v npm &> /dev/null; then
    echo "❌ npm 未安装"
    MISSING_DEPS=1
else
    echo "✓ npm: $(npm --version)"
fi

if ! command -v ffmpeg &> /dev/null; then
    echo "❌ FFmpeg 未安装"
    MISSING_DEPS=1
else
    echo "✓ FFmpeg: $(ffmpeg -version | head -1)"
fi

if [ $MISSING_DEPS -eq 1 ]; then
    echo ""
    echo "请先安装缺失的依赖"
    exit 1
fi

echo ""
echo "=== 安装项目依赖 ==="

# 安装后端依赖
echo ""
echo "安装后端依赖..."
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt
deactivate
cd ..

# 安装前端依赖
echo ""
echo "安装前端依赖..."
cd frontend
npm install
cd ..

# 安装 irasutoya 依赖
echo ""
echo "安装 irasutoya 依赖..."
cd irasutoya-client
npm install
cd ..

echo ""
echo "=== 安装完成 ==="
echo ""
echo "启动方式："
echo "1. 手动启动（推荐）："
echo "   终端1: cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo "   终端2: cd frontend && npm run dev"
echo "   终端3: cd irasutoya-client && npm start"
echo ""
echo "2. 使用启动脚本："
echo "   ./start.sh"
echo ""
echo "访问: http://localhost:5173"
