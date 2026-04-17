# KiriNuki 使用指南

## 快速开始

### 1. 安装依赖

运行安装脚本：
```bash
./setup.sh
```

或手动安装：

**后端:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**前端:**
```bash
cd frontend
npm install
```

**irasutoya:**
```bash
cd irasutoya-client
npm install
```

### 2. 启动服务

**方式一：使用启动脚本（推荐）**
```bash
./start.sh
```

**方式二：手动启动**

终端 1 - 后端:
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

终端 2 - 前端:
```bash
cd frontend
npm run dev
```

终端 3 - irasutoya (可选):
```bash
cd irasutoya-client
npm start
```

### 3. 访问应用

- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

## 使用流程

### 第一步：配置 Provider

1. 访问 http://localhost:5173
2. 点击右上角"设置"
3. 配置 Whisper Provider（选择本地或远程）
4. 配置多模态模型 Provider

**Whisper 本地配置示例:**
- 配置名称: 本地 Whisper
- 模式: 本地
- 模型大小: large-v3
- 设备: CUDA (如果有 GPU) 或 CPU

**Whisper 远程配置示例:**
- 配置名称: OpenAI Whisper
- 模式: 远程
- Base URL: https://api.openai.com/v1
- API Key: sk-...
- 模型 ID: whisper-1

**多模态模型配置示例:**
- 配置名称: Claude Sonnet
- Base URL: https://api.anthropic.com
- API Key: sk-ant-...
- 模型名称: claude-3-5-sonnet-20241022

### 第二步：创建项目

1. 点击"新建项目"
2. 输入项目名称（如：某某直播 2024-04-13）
3. 输入视频文件路径（绝对路径，如：/path/to/video.mp4）
4. 选择语言（默认日语）
5. 点击"创建"

### 第三步：运行 Pipeline

1. 进入项目详情页
2. 点击"运行 Pipeline"
3. 等待处理完成（可实时查看各步骤进度）

**Pipeline 步骤说明:**
- 素材导入: 提取视频信息和音频（约 1-2 分钟）
- 转录: Whisper 转录音频（4 小时视频约 10-20 分钟）
- 特征提取: 分析音频特征（约 2-3 分钟）
- 分块筛选: 5 分钟分块并初筛（约 1-2 分钟）
- 生成候选: 生成候选片段（约 1 分钟）
- 多模态复审: 对候选片段进行视觉分析（约 5-10 分钟）

**预计总时长:** 4 小时视频约 20-40 分钟

### 第四步：审核候选片段

1. Pipeline 完成后，查看候选片段列表
2. 每个候选片段显示：
   - 标题（可点击编辑）
   - 时间范围
   - 摘要
   - 得分（音频、文本、多模态、总分）
   - 标签
3. 操作：
   - 点击标题可编辑
   - 点击"保留"标记为保留
   - 点击"拒绝"标记为拒绝

### 第五步：导出 FCPXML

1. 点击"导出 FCPXML"
2. 等待导出完成（约 10 秒）
3. 自动下载 .fcpxml 文件

### 第六步：导入剪辑软件

**DaVinci Resolve:**
1. 打开 DaVinci Resolve
2. File → Import → Timeline
3. 选择导出的 .fcpxml 文件
4. 时间线会自动创建，包含所有候选片段

**Premiere Pro:**
1. 打开 Premiere Pro
2. File → Import
3. 选择导出的 .fcpxml 文件
4. 时间线会自动创建

**Final Cut Pro:**
1. 打开 Final Cut Pro
2. File → Import → XML
3. 选择导出的 .fcpxml 文件

## 常见问题

### Q: 本地 Whisper 首次运行很慢？
A: 首次运行会自动下载模型（约 3GB），需要等待。后续运行会直接使用缓存的模型。

### Q: 多模态分析失败？
A: 检查：
1. API Key 是否正确
2. Base URL 是否正确（注意不要包含 /chat/completions）
3. 模型是否支持视觉输入
4. 网络连接是否正常

### Q: 候选片段太少或太多？
A: 这是正常的。系统会根据内容自动筛选。你可以：
1. 在候选列表中手动标记保留/拒绝
2. 调整后续版本的筛选阈值（需修改代码）

### Q: 导出的 FCPXML 无法导入？
A: 检查：
1. 视频文件路径是否正确
2. 视频文件是否存在
3. 剪辑软件版本是否支持 FCPXML 1.13

### Q: 如何使用本地多模态模型？
A: 如果你有本地部署的多模态模型（如 LLaVA），只需：
1. 确保模型提供 OpenAI-compatible API
2. 在设置中配置 Base URL 为本地地址（如 http://localhost:8080/v1）
3. API Key 可以随意填写（如果本地模型不需要）

## 性能优化建议

### 本地 Whisper
- 使用 GPU（CUDA）可提速 5-10 倍
- 如果只有 CPU，建议使用 medium 或 small 模型
- large-v3 模型准确度最高但最慢

### 多模态分析
- 系统已自动优化，只分析筛选后的候选片段
- 4 小时视频通常只需 10-15 次多模态调用
- 如果成本敏感，可以跳过多模态步骤（在配置中不设置多模态 Provider）

### 硬件建议
- CPU: 4 核以上
- 内存: 8GB 以上（本地 Whisper 需要）
- GPU: NVIDIA GPU with CUDA（可选，用于加速 Whisper）
- 存储: 至少 20GB 可用空间

## 技术支持

如有问题，请查看：
1. 后端日志（终端输出）
2. 前端控制台（浏览器 F12）
3. 项目 README.md

## 下一步

完成基础流程后，你可以：
1. 尝试不同的 Whisper 模型大小
2. 尝试不同的多模态模型
3. 使用 irasutoya 搜索功能查找配图素材
4. 在 DaVinci Resolve 中精修导出的时间线
