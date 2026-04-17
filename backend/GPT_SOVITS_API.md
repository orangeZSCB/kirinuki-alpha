# GPT-SoVITS API 使用文档

基于 GPT-SoVITS 的音频处理 API，为 kirinuki 项目提供人声分离、语音切分和识别服务。

## 功能

1. **UVR5 人声分离**: 使用 HP5_only_main_vocal 模型提取主人声
2. **语音切分**: 使用 Slicer 自动切分音频片段
3. **Faster Whisper 识别**: 高精度语音识别

## 安装

```bash
cd backend

# 安装依赖
./setup_gpt_sovits.sh

# 或手动安装
pip install -r gpt_sovits_requirements.txt
```

## 启动服务

```bash
# 默认端口 9000
python gpt_sovits_api.py

# 自定义端口
python gpt_sovits_api.py --port 9001

# 指定设备
python gpt_sovits_api.py --device cuda

# 自定义临时目录
python gpt_sovits_api.py --temp_dir /path/to/temp
```

## API 接口

### 1. 健康检查

```bash
GET /health
```

响应:
```json
{
  "status": "ok",
  "device": "cuda",
  "cuda_available": true
}
```

### 2. 完整处理流程

```bash
POST /process
```

参数:
- `file`: 音频文件（multipart/form-data）
- `language`: 语言代码（ja/zh/en/auto，默认 ja）
- `model_size`: Whisper 模型大小（默认 large-v3）
- `skip_uvr`: 跳过 UVR5 人声分离（默认 false）
- `skip_slice`: 跳过语音切分（默认 false）

响应:
```json
{
  "job_id": "abc12345",
  "status": "completed",
  "vocal_path": "/tmp/gpt_sovits_api/abc12345/uvr5/vocals/vocal_input_10.wav",
  "sliced_dir": "/tmp/gpt_sovits_api/abc12345/sliced",
  "transcription_path": "/tmp/gpt_sovits_api/abc12345/transcription/transcription.txt",
  "transcription": [
    {
      "file": "vocal_input_10_0000000000_0000032000.wav",
      "language": "ja",
      "text": "こんにちは"
    }
  ]
}
```

### 3. 仅人声分离

```bash
POST /separate
```

参数:
- `file`: 音频文件（multipart/form-data）

响应:
```json
{
  "job_id": "abc12345",
  "status": "completed",
  "vocal_path": "/tmp/gpt_sovits_api/abc12345/uvr5/vocals/vocal_input_10.wav"
}
```

## 测试

```bash
# 健康检查
python test_gpt_sovits_api.py health

# 完整处理流程
python test_gpt_sovits_api.py process test.wav ja false

# 仅人声分离
python test_gpt_sovits_api.py separate test.wav
```

## 在 kirinuki 中使用

在 kirinuki 的转录服务中调用此 API：

```python
import httpx

async def transcribe_with_gpt_sovits(audio_path: str, language: str = "ja"):
    """使用 GPT-SoVITS API 进行转录"""
    
    async with httpx.AsyncClient(timeout=3600.0) as client:
        with open(audio_path, "rb") as f:
            files = {"file": (Path(audio_path).name, f, "audio/wav")}
            data = {
                "language": language,
                "model_size": "large-v3",
                "skip_uvr": "false",
                "skip_slice": "false",
            }
            
            response = await client.post(
                "http://localhost:9000/process",
                files=files,
                data=data,
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["transcription"]
            else:
                raise Exception(f"API 调用失败: {response.text}")
```

## 模型要求

### UVR5 模型
- 路径: `backend/GPT-SoVITS-main/tools/uvr5/uvr5_weights/HP5_only_main_vocal.pth`
- 下载: 需要手动下载或从 GPT-SoVITS 项目获取

### Whisper 模型
- 首次运行时自动下载
- 支持模型: tiny, base, small, medium, large-v3
- 默认使用: large-v3

## 性能优化

1. **使用 GPU**: 确保安装了 CUDA 和 PyTorch GPU 版本
2. **调整批处理大小**: 根据显存调整 Whisper 的 batch_size
3. **跳过不需要的步骤**: 
   - 如果音频已经是纯人声，设置 `skip_uvr=true`
   - 如果不需要切分，设置 `skip_slice=true`

## 故障排除

### 1. CUDA 不可用
```bash
# 检查 PyTorch CUDA
python -c "import torch; print(torch.cuda.is_available())"

# 重新安装 PyTorch GPU 版本
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### 2. UVR5 模型不存在
```bash
# 检查模型文件
ls backend/GPT-SoVITS-main/tools/uvr5/uvr5_weights/HP5_only_main_vocal.pth

# 如果不存在，需要手动下载
```

### 3. Whisper 模型下载失败
```bash
# 设置镜像
export HF_ENDPOINT=https://hf-mirror.com

# 手动下载模型
python -c "from faster_whisper import WhisperModel; WhisperModel('large-v3')"
```

## 目录结构

```
backend/
├── gpt_sovits_api.py              # API 主程序
├── gpt_sovits_requirements.txt    # 依赖列表
├── setup_gpt_sovits.sh            # 安装脚本
├── test_gpt_sovits_api.py         # 测试脚本
└── GPT-SoVITS-main/               # GPT-SoVITS 源码
    └── tools/
        ├── uvr5/                  # UVR5 人声分离
        ├── slicer2.py             # 语音切分
        └── asr/                   # Faster Whisper
```

## 许可证

基于 GPT-SoVITS 项目，遵循其原始许可证。
