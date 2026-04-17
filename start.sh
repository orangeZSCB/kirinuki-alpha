#!/bin/bash

# KiriNuki 启动脚本

echo "=== KiriNuki 启动 ==="
echo ""

# 检查依赖
command -v python3 >/dev/null 2>&1 || { echo "错误: 未找到 Python3"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "错误: 未找到 Node.js"; exit 1; }
command -v ffmpeg >/dev/null 2>&1 || { echo "错误: 未找到 FFmpeg"; exit 1; }

# 启动后端
echo "启动后端..."
cd backend
source venv/bin/activate
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
deactivate
cd ..

# 等待后端启动
sleep 3

# 启动前端
echo "启动前端..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# 启动 irasutoya 服务（可选）
if [ -d "irasutoya-client" ]; then
    echo "启动 irasutoya 服务..."
    cd irasutoya-client
    npm start &
    IRASUTOYA_PID=$!
    cd ..
fi

echo ""
echo "=== 服务已启动 ==="
echo "后端: http://localhost:8000"
echo "前端: http://localhost:5173"
echo "API 文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待中断信号
trap "echo ''; echo '停止服务...'; kill $BACKEND_PID $FRONTEND_PID $IRASUTOYA_PID 2>/dev/null; exit" INT TERM

wait
