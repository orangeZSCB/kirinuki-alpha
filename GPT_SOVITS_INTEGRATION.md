# GPT-SoVITS 集成到 KiriNuki 完成报告

## 概述

成功将 GPT-SoVITS 音频处理流程集成到 KiriNuki 项目，替换原有的 Whisper 转录逻辑。

## 新增文件

### 1. GPT-SoVITS API 服务
- **`backend/gpt_sovits_api.py`** - 独立的 FastAPI 服务
  - UVR5 人声分离（HP5_only_main_vocal 模型）
  - Slicer 语音切分
  - Faster Whisper 识别
  - 三个 API 端点：`/process`、`/separate`、`/health`

### 2. 依赖和安装
- **`backend/gpt_sovits_requirements.txt`** - GPT-SoVITS API 依赖列表
- **`backend/setup_gpt_sovits.sh`** - 自动安装脚本
- **`backend/test_gpt_sovits_api.py`** - API 测试脚本
- **`backend/GPT_SOVITS_API.md`** - 完整使用文档

### 3. KiriNuki 集成
- **`backend/app/services/transcription/gpt_sovits.py`** - GPT-SoVITS Provider
  - 实现 `TranscriptionProvider` 接口
  - 调用 GPT-SoVITS API
  - 解析切分后的识别结果
  - 生成 SRT 字幕文件

## 修改文件

### 1. 后端
- **`backend/app/services/pipeline/orchestrator.py`**
  - 导入 `GPTSoVITSProvider`
  - 在 `_step_transcribe` 中添加 `gpt_sovits` 模式支持
  - 自动保存 SRT 字幕文件到 `data/projects/{project_id}/transcription.srt`

### 2. 前端
- **`frontend/src/pages/Settings.tsx`**
  - 添加 "GPT-SoVITS" 模式选项
  - 配置表单支持：
    - GPT-SoVITS API URL
    - Whisper 模型大小
    - 跳过 UVR5 选项
    - 跳过切分选项
  - 显示配置时区分三种模式

## 工作流程

### 原始流程（已替换）
```
原始音频 → Whisper 识别 → 转录文本
```

### 新流程（GPT-SoVITS 模式）
```
原始音频 
  ↓
GPT-SoVITS API
  ├─ UVR5 人声分离（去除 BGM）
  ├─ Slicer 语音切分
  └─ Faster Whisper 识别
  ↓
转录片段（带时间戳）
  ↓
保存到数据库 + 生成 SRT 字幕
  ↓
LLM 分析
```

### 关键特性
1. **去除 BGM**：使用 UVR5 HP5 模型提取主人声
2. **精确切分**：Slicer 根据静音自动切分语音片段
3. **时间戳保留**：从文件名解析切分时间戳（采样数）
4. **SRT 输出**：生成标准 SRT 字幕文件供后续使用
5. **原始音频保留**：最终剪辑使用原始音频，不用去 BGM 的

## 使用方法

### 1. 启动 GPT-SoVITS API

```bash
cd backend

# 安装依赖
./setup_gpt_sovits.sh

# 启动服务（默认端口 9000）
python gpt_sovits_api.py --port 9000
```

### 2. 在 KiriNuki 中配置

1. 打开 KiriNuki 前端：http://localhost:5173
2. 进入"设置"页面
3. 点击"添加 Whisper 配置"
4. 选择模式：**GPT-SoVITS (UVR5 + 切分 + Whisper)**
5. 填写配置：
   - 配置名称：如 "GPT-SoVITS 本地"
   - API URL：`http://localhost:9000`
   - Whisper 模型：`large-v3`（推荐）
   - 可选：勾选"跳过 UVR5"（如果音频已是纯人声）
   - 可选：勾选"跳过切分"（如果不需要切分）
6. 点击"创建"

### 3. 运行 Pipeline

创建项目后，点击"运行 Pipeline"，系统会自动：
1. 提取音频
2. 调用 GPT-SoVITS API 处理
3. 保存转录结果到数据库
4. 生成 SRT 字幕文件
5. 继续后续分析步骤

## 输出文件

每个项目会生成：
- **`data/projects/{project_id}/audio.wav`** - 原始音频（用于最终剪辑）
- **`data/projects/{project_id}/transcription.srt`** - SRT 字幕文件
- 数据库中的转录片段（带时间戳）

## 配置选项

### GPT-SoVITS Provider 配置
```json
{
  "mode": "gpt_sovits",
  "base_url": "http://localhost:9000",
  "model_size": "large-v3",
  "skip_uvr": false,
  "skip_slice": false
}
```

### 参数说明
- **base_url**: GPT-SoVITS API 地址
- **model_size**: Whisper 模型大小（tiny/base/small/medium/large-v3）
- **skip_uvr**: 跳过 UVR5 人声分离（适用于已是纯人声的音频）
- **skip_slice**: 跳过语音切分（适用于不需要切分的场景）

## 技术细节

### 时间戳解析
GPT-SoVITS 切分后的文件名格式：
```
vocal_input_10_0000000000_0000032000.wav
                ↑          ↑
            起始采样数   结束采样数
```

采样率：32000 Hz
转换公式：`秒 = 采样数 / 32000`

### SRT 格式
```srt
1
00:00:00,000 --> 00:00:03,200
こんにちは

2
00:00:03,200 --> 00:00:06,400
今日はいい天気ですね
```

## 测试

### 测试 GPT-SoVITS API
```bash
# 健康检查
python test_gpt_sovits_api.py health

# 完整处理流程
python test_gpt_sovits_api.py process test.wav ja false

# 仅人声分离
python test_gpt_sovits_api.py separate test.wav
```

### 测试 KiriNuki 集成
1. 创建测试项目
2. 上传测试视频
3. 配置 GPT-SoVITS Provider
4. 运行 Pipeline
5. 检查生成的 SRT 文件和数据库记录

## 依赖要求

### GPT-SoVITS API
- Python 3.8+
- PyTorch (GPU 推荐)
- faster-whisper
- librosa
- soundfile
- scipy

### UVR5 模型
- 路径：`backend/GPT-SoVITS-main/tools/uvr5/uvr5_weights/HP5_only_main_vocal.pth`
- 需要手动下载或从 GPT-SoVITS 项目获取

## 性能优化

1. **使用 GPU**：确保 CUDA 可用，大幅提升处理速度
2. **调整模型大小**：
   - `tiny/base`：快速但精度较低
   - `medium`：平衡
   - `large-v3`：最高精度（推荐）
3. **跳过不需要的步骤**：
   - 纯人声音频：`skip_uvr=true`
   - 不需要切分：`skip_slice=true`

## 故障排除

### 1. GPT-SoVITS API 无法启动
- 检查依赖是否安装：`pip list | grep torch`
- 检查 UVR5 模型是否存在
- 查看错误日志

### 2. KiriNuki 无法连接 API
- 确认 GPT-SoVITS API 正在运行
- 检查 URL 配置是否正确
- 测试连接：`curl http://localhost:9000/health`

### 3. 转录结果为空
- 检查音频文件是否有效
- 查看 GPT-SoVITS API 日志
- 尝试降低 Whisper 模型大小

## 总结

✅ **完成的工作**
- 创建独立的 GPT-SoVITS API 服务
- 实现 GPTSoVITSProvider 集成到 KiriNuki
- 修改 Pipeline 支持新的转录模式
- 添加前端配置界面
- 自动生成 SRT 字幕文件
- 完整的文档和测试脚本

✅ **核心优势**
- 去除直播 BGM，提取纯净主人声
- 自动切分语音片段
- 精确的时间戳
- 标准 SRT 格式输出
- 保留原始音频用于最终剪辑

✅ **用户体验**
- 一键配置
- 自动化处理
- 进度可视化
- 灵活的选项配置
