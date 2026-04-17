#!/bin/bash
# GPT-SoVITS API 安装脚本

set -e

echo "=== 安装 GPT-SoVITS API 依赖 ==="

# 检查是否在虚拟环境中
if [ -z "$VIRTUAL_ENV" ]; then
    echo "警告: 未检测到虚拟环境，建议先激活 venv"
    echo "运行: source venv/bin/activate"
    read -p "是否继续安装到系统 Python? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 安装依赖
echo "安装 Python 依赖..."
pip install -r gpt_sovits_requirements.txt

# 检查 CUDA
if python -c "import torch; print(torch.cuda.is_available())" | grep -q "True"; then
    echo "✅ CUDA 可用"
else
    echo "⚠️  CUDA 不可用，将使用 CPU（速度较慢）"
fi

# 检查 UVR5 模型
MODEL_PATH="GPT-SoVITS-main/tools/uvr5/uvr5_weights/HP5_only_main_vocal.pth"
if [ -f "$MODEL_PATH" ]; then
    echo "✅ UVR5 模型已存在: $MODEL_PATH"
else
    echo "❌ UVR5 模型不存在: $MODEL_PATH"
    echo "请手动下载 HP5_only_main_vocal.pth 模型到该路径"
fi

echo ""
echo "=== 安装完成 ==="
echo "启动服务: python gpt_sovits_api.py --port 9000"
