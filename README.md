# KiriNuki - VTuber 直播切片辅助系统

自动从长直播中筛选高光片段，生成可编辑的剪辑工程文件。



## 功能特性

- ✅ 自动转录（支持本地/远程 Whisper）
- ✅ 音频特征分析
- ✅ 多阶段智能筛选（规则 + 文本模型 + 多模态）
- ✅ 候选片段人工审核
- ❎ **待优化** 导出 FCPXML 1.13（兼容 DaVinci Resolve / Premiere Pro）
- ✅ 自定义 API 配置（Whisper / 多模态模型）
- ❎ **待实现** irasutoya 插画搜索

## 系统要求

- Python 3.11+
- Node.js 18+
- FFmpeg
- （可选）CUDA GPU（用于本地 Whisper）

## 快速开始

### 1. 安装依赖

**后端:**
```bash
cd backend
pip install -r requirements.txt
```

**前端:**
```bash
cd frontend
npm install
```

**GPT-SoVITS 服务:**
```bash
cd backend
conda create -n kiriasr python=3.10
pip install -r ./requirements.txt
```

### 2. 启动服务

**启动后端:**
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**启动前端:**
```bash
cd frontend
npm run dev
```

**启动 GPT-SoVITS 服务（可选）:**
```bash
cd irasutoya-client
conda activate kiriasr
python gpt_sovits_api.py
```

### 3. 访问应用

打开浏览器访问: http://localhost:5173

## 使用流程

1. **配置 Provider**
   - 进入"设置"页面
   - 配置 Whisper（本地或远程）
   - 配置多模态模型（强烈建议使用 kiriasr (based on GPT-SoVITS)）

2. **创建项目**
   - 点击"新建项目"
   - 输入项目名称和视频文件路径
   - 选择语言（默认日语）

3. **运行 Pipeline**
   - 进入项目详情页
   - 点击"运行 Pipeline"
   - 等待处理完成（可实时查看进度）

4. **审核候选片段**
   - 查看自动识别的候选片段
   - 编辑标题
   - 标记保留/拒绝

5. **导出 FCPXML**
   - 点击"导出 FCPXML"
   - 下载生成的 .fcpxml 文件
   - 导入 DaVinci Resolve 或 Premiere Pro 继续编辑

## 配置说明

### Whisper 配置

**本地模式:**
- 模型大小: tiny / base / small / medium / large-v3
- 设备: CUDA (GPU) / CPU
- 需要下载模型（首次运行自动下载）

**远程模式:**
- Base URL: API 端点（如 `https://api.openai.com/v1`）
- API Key: 你的 API 密钥
- 模型 ID: 如 `whisper-1`

### 多模态模型配置

- Base URL: API 端点（如 `https://api.anthropic.com`）
- API Key: 你的 API 密钥
- 模型名称: 如 `claude-3-5-sonnet-20241022` 或 `gpt-4-vision-preview`

支持任何 OpenAI-compatible 的多模态 API。

## Pipeline 步骤

1. **Ingest**: 提取视频元信息和音频
2. **Transcribe**: 转录音频为文本
3. **Extract Features**: 提取音频特征（音量、峰值、静音）
4. **Chunk and Screen**: 5分钟分块 + 低成本初筛
5. **Generate Candidates**: 生成候选片段
6. **Multimodal Review**: 多模态模型复审（可选）

## 成本优化

- 音频特征预筛：过滤 75-80% 无效片段
- 5 分钟分块：限制 prompt 长度
- 多模态只看候选：仅分析已筛选的片段
- 预期成本：4 小时直播 → 10-15 次多模态调用

## 项目结构

```
kirinuki/
├── backend/          # FastAPI 后端
├── frontend/         # React 前端
├── irasutoya-client/ # irasutoya 插画搜索服务
└── data/             # 工作目录（自动创建）
    ├── projects/     # 项目数据
    └── exports/      # 导出文件
```

## 故障排除

**问题: 本地 Whisper 加载失败**
- 确保已安装 CUDA（GPU 模式）
- 或切换到 CPU 模式
- 首次运行会自动下载模型，需要网络连接

**问题: 多模态分析失败**
- 检查 API Key 是否正确
- 检查 Base URL 是否正确
- 确保模型支持视觉输入

**问题: FFmpeg 未找到**
- 确保已安装 FFmpeg
- 检查 PATH 环境变量

## 开发

**后端测试:**
```bash
cd backend
pytest
```

**前端开发:**
```bash
cd frontend
npm run dev
```

## 许可证

MIT

## 致谢

- [faster-whisper](https://github.com/guillaumekln/faster-whisper)
- [irasutoya](https://www.irasutoya.com/)
- DaVinci Resolve / Premiere Pro
