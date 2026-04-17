# KiriNuki 项目文档

**重要：每次对话结束后，AI 必须更新此文档，记录新的改动、决策和上下文。**

---

## 项目概述

**KiriNuki** 是一个面向 VTuber 直播录播的自动切片辅助系统。通过 AI 分析长视频，自动识别高光片段（B 站观众喜欢的内容），生成可编辑的剪辑工程文件。

### 核心价值
从几小时的直播录像中，自动找出"能火的片段"，并生成 B 站风格的标题和标签，最后导出专业剪辑工程文件。

### 核心功能
1. **音频转录**：支持本地/远程 Whisper、GPT-SoVITS（UVR5 + 切分 + Whisper）
2. **智能筛选**：音频特征 + 文本分析 + 多模态视觉分析（判断哪些片段是 B 站观众喜欢的）
3. **候选生成**：自动生成高光片段候选，并生成 B 站风格的标题和标签
4. **人工审核**：用户可以微调标题/标签，标记保留/拒绝片段（节省算力和时间）
5. **专业导出**：FCPXML 1.13 格式，兼容 DaVinci Resolve / Premiere Pro / Final Cut Pro
6. **插画增强**（规划中）：自动搜索插画并插入到视频 timeline，用多模态模型分析插画应该放在哪一帧到哪一帧的哪个位置

---

## 技术架构

### 后端 (FastAPI + Python)
- **框架**：FastAPI 0.115.0
- **数据库**：SQLAlchemy 2.0.36 + SQLite
- **音频处理**：FFmpeg, librosa, faster-whisper
- **AI 模型**：Whisper (转录), 多模态模型 (视觉分析)

### 前端 (React + TypeScript)
- **框架**：React 19.2.4 + TypeScript 6.0.2
- **构建工具**：Vite 8.0.4
- **路由**：React Router 7.1.3
- **样式**：内联样式（简洁 MVP）

### 数据库模型
```
Project (项目)
  ├─ ProjectRun (运行记录)
  │   └─ PipelineStep (步骤)
  ├─ TranscriptSegment (转录片段)
  ├─ AnalysisChunk (分析块)
  ├─ ClipCandidate (候选片段)
  └─ Export (导出记录)

ProviderConfig (Provider 配置)
  ├─ whisper (转录)
  └─ multimodal (多模态)
```

---

## Pipeline 流程

### 1. Ingest (素材导入)
- 使用 FFmpeg 提取视频元信息
- 提取音频为 16kHz WAV
- 保存到 `data/projects/{project_id}/audio.wav`

### 2. Transcribe (转录)
**支持三种模式：**

#### 本地 Whisper
- 使用 faster-whisper
- 支持 CUDA 加速
- 模型：tiny/base/small/medium/large-v3

#### 远程 Whisper API
- OpenAI-compatible API
- 自动切分大文件（>20MB）
- 支持自定义 endpoint

#### GPT-SoVITS (新增)
- **UVR5 人声分离**：去除直播 BGM，提取主人声
- **Slicer 语音切分**：根据静音自动切分
- **Faster Whisper 识别**：高精度转录
- **输出**：
  - 数据库：TranscriptSegment (带时间戳)
  - 文件：`data/projects/{project_id}/transcription.srt`

**关键设计：**
- 去 BGM 的音频仅用于识别
- 最终剪辑使用原始音频（保留 BGM）
- SRT 时间戳基于切分后的采样数（32000 Hz）

### 3. Extract Features (特征提取)
- 使用 librosa 分析音频
- 提取 RMS、峰值、静音检测
- 保存到 PipelineStep.output_data

### 4. Multimodal Analysis (多模态分析) - **两阶段分析**
**核心作用**：分两阶段分析视频，找出所有高光片段并生成标题标签。

**阶段 1：纯文本分析**
- **输入**：完整转录文本（带时间戳）
- **处理**：调用多模态模型（纯文本 API）
- **输出**：高光片段的时间范围列表（JSON 格式）
- **优势**：上行流量小，速度快

**阶段 2：视觉分析**
- **输入**：每个片段的转录文本 + 关键帧（每 3 秒一帧）
- **处理**：对每个片段单独调用多模态模型（多模态 API）
- **输出**：B 站风格的标题、标签、评分、理由
- **优势**：分析更精准，失败影响小

**完整流程**：
1. 加载所有转录片段
2. **阶段 1**：发送完整转录文本，获取高光片段时间范围
3. **阶段 2**：对每个片段：
   - 提取该片段的关键帧（按需提取）
   - 获取该片段的转录文本
   - 调用多模态模型生成标题和标签
4. 生成 Markdown 分析报告
5. 创建 ClipCandidate 记录

**输出**：
- **Markdown 分析报告**（人类可读）：保存到 `data/projects/{project_id}/analysis_report.md`
- **JSON 结构化数据**（给 KiriNuki）：直接创建 ClipCandidate 记录

**关键设计决策**：
- 文本和关键帧分开分析，避免上行流量过大
- 关键帧按需提取，不预先提取整个视频
- 超时时间：30 分钟（1800 秒）
- 支持两种 API 格式：Anthropic (`/v1/messages`) 和 OpenAI-compatible (`/chat/completions`)
- 用户在前端可以微调标题/标签或删除不想要的片段

### 5. Export (导出)
- 生成 FCPXML 1.13
- 精确时间码转换（Fraction）
- 保留原始素材引用

---

## 废弃的 Pipeline 步骤

以下步骤在重写后已不再使用：

### ~~4. Chunk and Screen (分块筛选)~~
- ~~5 分钟分块~~
- ~~规则打分（音量、关键词）~~
- ~~文本模型初筛~~
- ~~保存到 AnalysisChunk~~

### ~~5. Generate Candidates (生成候选)~~
- ~~选择高分块（Top 15）~~
- ~~扩展时间范围（前 -15s，后 +20s）~~
- ~~合并相邻片段~~
- ~~保存到 ClipCandidate~~

### ~~6. Multimodal Review (多模态复审)~~
- ~~提取关键帧（每 3 秒）~~
- ~~逐个复审候选片段~~
- ~~更新评分和标题~~

**为什么废弃**：
- 旧方案需要多次调用多模态模型（每个候选片段一次）
- 新方案只需调用一次，让模型自己决定哪些片段值得剪辑
- 更符合"整个视频一次性分析"的设计目标

---

## 文件结构

```
kirinuki/
├── backend/
│   ├── app/
│   │   ├── api/routes/          # API 路由
│   │   │   ├── projects.py      # 项目管理
│   │   │   ├── pipeline.py      # Pipeline 控制
│   │   │   ├── candidates.py    # 候选片段
│   │   │   ├── exports.py       # 导出
│   │   │   ├── settings.py      # Provider 配置
│   │   │   └── irasutoya.py     # 插画搜索
│   │   ├── core/
│   │   │   ├── config.py        # 配置
│   │   │   └── database.py      # 数据库
│   │   ├── models/
│   │   │   └── db.py            # 数据模型
│   │   ├── schemas/
│   │   │   └── api.py           # Pydantic 模型
│   │   ├── services/
│   │   │   ├── transcription/   # 转录服务
│   │   │   │   ├── base.py      # 抽象基类
│   │   │   │   ├── local.py     # 本地 Whisper
│   │   │   │   ├── remote.py    # 远程 Whisper
│   │   │   │   └── gpt_sovits.py # GPT-SoVITS
│   │   │   ├── analysis/        # 分析服务
│   │   │   │   ├── audio_features.py
│   │   │   │   ├── chunker.py
│   │   │   │   ├── cheap_ranker.py
│   │   │   │   └── multimodal_ranker.py
│   │   │   ├── pipeline/
│   │   │   │   └── orchestrator.py # Pipeline 编排
│   │   │   ├── export/fcpxml/   # FCPXML 导出
│   │   │   ├── ffmpeg_service.py
│   │   │   └── irasutoya/       # irasutoya 桥接
│   │   └── main.py              # FastAPI 入口
│   ├── gpt_sovits_api.py        # GPT-SoVITS API 服务
│   ├── GPT-SoVITS-main/         # GPT-SoVITS 源码
│   ├── requirements.txt
│   └── gpt_sovits_requirements.txt
├── frontend/
│   └── src/
│       ├── api/client.ts        # API 客户端
│       ├── components/
│       │   ├── candidate/CandidateList.tsx
│       │   └── pipeline/PipelineStatus.tsx
│       ├── pages/
│       │   ├── Dashboard.tsx    # 项目列表
│       │   ├── ProjectDetail.tsx # 项目详情
│       │   └── Settings.tsx     # 设置
│       ├── types/api.ts
│       └── main.tsx
├── irasutoya-client/            # irasutoya 插画搜索（Node.js 服务）
│   ├── lib/
│   │   ├── api.js               # irasutoya.com API 封装
│   │   ├── server.js            # Express 服务器
│   │   └── model.js             # 数据模型
│   └── index.js                 # 入口文件
├── data/                        # 工作目录
│   ├── projects/
│   │   └── {project_id}/
│   │       ├── audio.wav        # 原始音频
│   │       ├── transcription.srt # SRT 字幕（GPT-SoVITS）
│   │       └── keyframes/       # 关键帧
│   └── exports/                 # 导出文件
└── kirinuki.db                  # SQLite 数据库
```

---

## irasutoya 插画系统

### 当前状态
**已实现**：
1. **irasutoya-client**（Node.js 服务，端口 3000）
   - `/search?query=关键词` - 搜索插画
   - `/random` - 获取随机插画
   - `/random?raw=true` - 获取随机插画的原始图片

2. **KiriNuki 后端桥接**（`backend/app/services/irasutoya/bridge.py`）
   - `IrasutoyaBridge` 类调用 irasutoya-client 服务
   - API 路由：`/api/irasutoya/search` 和 `/api/irasutoya/random`

**未实现**：
- ❌ 插画搜索未集成到 Pipeline 流程
- ❌ 多模态模型未分析"插画应该放在哪一帧到哪一帧的哪个位置"
- ❌ FCPXML 导出未包含插画图层

### 设计目标
学习 irasutoya-client 的插画搜索方式，让 KiriNuki 能够：
1. 根据片段内容自动搜索相关插画
2. 用多模态模型分析：
   - 插画应该在视频的哪个时间段出现（起始帧 → 结束帧）
   - 插画应该放在画面的哪个位置（左上/右下/居中等）
   - 插画的大小和透明度
3. 将插画信息写入 FCPXML，作为独立的图层导出

### 工作流程（规划）
```
候选片段 + 转录文本
  ↓
多模态模型分析
  ├─ 提取关键词（如"笑"、"哭"、"惊讶"）
  └─ 调用 irasutoya API 搜索插画
  ↓
多模态模型决策
  ├─ 选择最合适的插画
  ├─ 决定插画的时间范围（起始帧 → 结束帧）
  ├─ 决定插画的位置（x, y, width, height）
  └─ 决定插画的透明度和动画效果
  ↓
保存到数据库（新表：ClipIllustration）
  ↓
FCPXML 导出时，将插画作为独立图层插入
```

---

## 最近改动

### 2026-04-15: 修复多模态 API 调用问题

**问题：**
1. **400 Bad Request 错误**：代码根据 URL/模型名判断 API 类型，导致使用错误的 endpoint
2. **前端硬编码 provider_type**：无法选择 API 类型（Anthropic vs OpenAI-compatible）

**修复：**
1. **后端判断逻辑**：改为根据配置中的 `provider_type` 字段判断 API 类型
   - `anthropic` → `/v1/messages` (Anthropic 格式)
   - `openai_compatible` → `/chat/completions` (OpenAI 格式)
   
2. **前端添加选择框**：在设置页面添加 API 类型下拉框
   - "OpenAI Compatible (通用)"
   - "Anthropic (Claude)"

**文件：**
- `backend/app/services/analysis/multimodal_analyzer.py` - 修改 API 判断逻辑
- `frontend/src/pages/Settings.tsx` - 添加 provider_type 选择框

---

### 2026-04-15: 两阶段多模态分析

**背景：**
- 一次性发送完整转录文本 + 所有关键帧导致：
  - 上行流量过大（132 个片段 + 多个关键帧 base64）
  - API 超时（ReadTimeout after 300s）
  - 模型处理时间过长

**新方案：两阶段分析**
1. **阶段 1：纯文本分析**
   - 只发送完整转录文本（不发图片）
   - 获取高光片段的时间范围（JSON 格式）
   - 速度快，流量小

2. **阶段 2：视觉分析**
   - 对每个片段单独提取关键帧（每 3 秒一帧）
   - 发送该片段的文本 + 关键帧
   - 生成标题、标签、评分、理由
   - 失败影响范围小

**实现：**
- `_stage1_text_analysis()` - 纯文本分析，调用 `_call_text_api()`
- `_stage2_visual_analysis()` - 视觉分析，调用 `_call_multimodal_api()`
- 超时时间从 300 秒延长至 1800 秒（30 分钟）
- 关键帧按需提取，不预先提取整个视频

**文件：**
- `backend/app/services/analysis/multimodal_analyzer.py` - 重写为两阶段分析
- `backend/app/services/pipeline/orchestrator.py` - 更新调用方式

---

### 2026-04-15: 重写多模态分析阶段

**背景：**
- 旧方案：先用规则/便宜模型初筛 → 生成候选片段 → 逐个调用多模态模型复审
- 问题：需要多次调用多模态模型，效率低，且初筛可能遗漏精彩片段

**新方案：**
- 一次性分析整个视频，让多模态模型自己决定哪些片段值得剪辑
- 依赖 Claude 200K context 的长文本能力
- 输出 Markdown 报告（人类可读）+ JSON 数据（结构化）

**实现：**
1. **创建 MultimodalAnalyzer** (`backend/app/services/analysis/multimodal_analyzer.py`)
   - `analyze_full_video()` 方法：分析整个视频
   - 输入：完整转录文本 + 关键帧
   - 输出：Markdown 报告 + ClipSegment 列表
   - 支持 Anthropic API 和 OpenAI-compatible API

2. **重写 Pipeline 步骤 6** (`backend/app/services/pipeline/orchestrator.py`)
   - 废弃步骤 4-5（分块筛选、生成候选）
   - 新的步骤 4：多模态分析（整个视频）
   - 直接创建 ClipCandidate 记录
   - 保存 Markdown 报告到 `data/projects/{project_id}/analysis_report.md`

3. **Pipeline 流程简化**
   - 旧流程：6 步（导入 → 转录 → 特征 → 分块 → 候选 → 复审）
   - 新流程：4 步（导入 → 转录 → 特征 → 多模态分析）

**关键设计决策：**
- 完全信任多模态模型的判断能力
- 不再需要规则打分和初筛
- 用户在前端做最后的人工审核

**文件：**
- `backend/app/services/analysis/multimodal_analyzer.py` - 新的多模态分析器
- `backend/app/services/pipeline/orchestrator.py` - 更新 Pipeline 流程
- `backend/app/services/analysis/multimodal_ranker.py` - 旧代码（已不再使用）

---

### 2026-04-15: GPT-SoVITS 集成

**背景：**
- 原有 Whisper 转录无法处理直播 BGM
- 需要去除背景音乐，提取主播人声
- 需要精确切分语音片段

**实现：**
1. **创建 GPT-SoVITS API 服务** (`backend/gpt_sovits_api.py`)
   - 独立 FastAPI 服务，端口 9000
   - 调用 GPT-SoVITS 原有代码（UVR5, Slicer, Whisper）
   - 三个端点：`/process`, `/separate`, `/health`

2. **创建 GPTSoVITSProvider** (`backend/app/services/transcription/gpt_sovits.py`)
   - 实现 `TranscriptionProvider` 接口
   - 调用 GPT-SoVITS API
   - 解析切分文件名中的时间戳（采样数）
   - 生成 SRT 字幕文件

3. **修改 Pipeline** (`backend/app/services/pipeline/orchestrator.py`)
   - 添加 `gpt_sovits` 模式支持
   - 自动保存 SRT 到 `data/projects/{project_id}/transcription.srt`

4. **修改前端设置** (`frontend/src/pages/Settings.tsx`)
   - 添加 "GPT-SoVITS" 模式选项
   - 配置项：API URL, 模型大小, 跳过 UVR, 跳过切分

**工作流：**
```
原始音频 (带 BGM)
  ↓
GPT-SoVITS API
  ├─ UVR5: 去除 BGM → 纯人声
  ├─ Slicer: 切分 → vocal_xxx_0000000000_0000032000.wav
  └─ Whisper: 识别 → 转录文本
  ↓
KiriNuki
  ├─ 保存到数据库 (TranscriptSegment)
  └─ 生成 SRT 字幕
  ↓
LLM 分析 → 候选片段
  ↓
最终剪辑（使用原始音频，保留 BGM）
```

**关键设计决策：**
- 去 BGM 的音频仅用于识别，不用于最终剪辑
- 时间戳从文件名解析（`_起始采样数_结束采样数.wav`）
- 采样率固定 32000 Hz
- SRT 格式便于后续处理和调试

**文件：**
- `backend/gpt_sovits_api.py` - API 服务
- `backend/app/services/transcription/gpt_sovits.py` - Provider
- `backend/gpt_sovits_requirements.txt` - 依赖
- `backend/setup_gpt_sovits.sh` - 安装脚本
- `backend/test_gpt_sovits_api.py` - 测试脚本
- `backend/GPT_SOVITS_API.md` - API 文档
- `GPT_SOVITS_INTEGRATION.md` - 集成报告

---

## Provider 配置

### Whisper Provider
```json
{
  "provider_kind": "whisper",
  "name": "配置名称",
  "config": {
    "mode": "local|remote|gpt_sovits",
    
    // local 模式
    "model_size": "large-v3",
    "device": "cuda|cpu",
    "compute_type": "float16",
    
    // remote 模式
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-...",
    "model_request_id": "whisper-1",
    "endpoint_path": "/audio/transcriptions",
    "response_format": "verbose_json",
    
    // gpt_sovits 模式
    "base_url": "http://localhost:9000",
    "model_size": "large-v3",
    "skip_uvr": false,
    "skip_slice": false
  },
  "is_default": true
}
```

### 多模态 Provider
```json
{
  "provider_kind": "multimodal",
  "name": "配置名称",
  "config": {
    "provider_type": "openai_compatible",
    "base_url": "https://api.anthropic.com",
    "api_key": "sk-ant-...",
    "model": "claude-3-5-sonnet-20241022",
    "timeout_seconds": 120,
    "max_frames_per_candidate": 8
  },
  "is_default": true
}
```

---

## 开发规范

### 代码风格
- **Python**: PEP8, 类型注解
- **TypeScript**: 严格模式
- **注释**: 中文或英文，保持一致

### 数据库
- 使用 SQLAlchemy ORM
- 所有 ID 使用 UUID
- 时间戳使用 UTC

### API
- RESTful 风格
- 统一错误处理
- 日志记录关键操作

### 前端
- 组件化设计
- 类型安全
- 简洁 UI（MVP 阶段）

---

## 常见问题

### Q: 为什么 GPT-SoVITS 要单独启动？
A: 
1. GPT-SoVITS 依赖较重（PyTorch, UVR5 模型）
2. 可能需要 GPU，独立部署更灵活
3. 可以多个 KiriNuki 实例共享一个 GPT-SoVITS 服务

### Q: SRT 文件的作用？
A: 
1. 调试：方便查看转录结果
2. 备份：数据库之外的文本备份
3. 扩展：未来可能用于字幕轨导出

### Q: 为什么不直接用去 BGM 的音频剪辑？
A: 
1. 去 BGM 后音质会下降
2. 直播 BGM 是氛围的一部分

### Q: Pipeline 可以断点续跑吗？
A: 
- ✅ **已支持**（2026-04-15 实现）
- 如果 Pipeline 运行失败，重新运行时会自动跳过已完成的步骤
- 每个步骤的状态保存在 `PipelineStep` 表中
- 只会执行未完成或失败的步骤

### Q: 多模态模型的作用是什么？
A:
- 不只是"看画面"，而是**综合分析文本+画面**
- 判断"这段内容能不能火"（是否是 B 站观众喜欢的内容）
- 生成 B 站风格的标题和标签
- 未来还会用于分析插画应该放在哪里

### Q: irasutoya 插画系统为什么还没集成到 Pipeline？
A:
- 之前的 agent 只实现了插画搜索的 API 桥接
- 但没有集成到 Pipeline 流程中
- 也没有实现多模态模型分析插画位置的功能
- 这是下一步要做的工作

---

## TODO / 未来计划

### 短期
- [ ] 添加单元测试
- [ ] 优化前端样式
- [ ] 添加进度百分比显示
- [ ] 添加日志查看功能
- [ ] **集成 irasutoya 插画系统到 Pipeline**
  - [ ] 创建 ClipIllustration 数据模型
  - [ ] 多模态模型分析插画位置和时间范围
  - [ ] FCPXML 导出支持插画图层

### 中期
- [ ] EDL / OTIO 导出支持
- [ ] 关键帧缩略图预览
- [ ] 波形图显示
- [ ] 批量项目处理
- [ ] Pipeline 断点续跑

### 长期
- [ ] 自动字幕轨导出
- [ ] 自动插图插入（irasutoya）- 完整实现
- [ ] 插画动画效果（淡入淡出、缩放等）
- [ ] 弹幕联动分析
- [ ] 多用户支持
- [ ] 云端部署

---

## 更新日志

### 2026-04-15
- ✅ 集成 GPT-SoVITS (UVR5 + Slicer + Whisper)
- ✅ 添加 GPT-SoVITS Provider
- ✅ 自动生成 SRT 字幕文件
- ✅ 前端添加 GPT-SoVITS 配置界面
- ✅ 创建完整的集成文档
- ✅ 修正 CLAUDE.md 中对多模态模型作用的描述
- ✅ 补充 irasutoya 插画系统的当前状态和设计目标
- ⚠️ 发现问题：irasutoya 插画搜索只有 API 桥接，未集成到 Pipeline
- ✅ **重写多模态分析阶段**
  - 创建 MultimodalAnalyzer（一次性分析整个视频）
  - 废弃步骤 4-5（分块筛选、生成候选）
  - Pipeline 从 6 步简化为 4 步
  - 输出 Markdown 报告 + JSON 数据
- ✅ **修复数据库问题**
  - 从内存数据库改为持久化 SQLite 文件
  - 解决 FastAPI hot reload 导致数据丢失的问题
- ✅ **实现断点续跑功能**
  - Pipeline 失败后可以从断点继续
  - 自动跳过已完成的步骤
  - 只执行未完成或失败的步骤

### 2026-04-13
- ✅ 完成 MVP 实现
- ✅ 后端 41 个源代码文件
- ✅ 前端 9 个组件/页面
- ✅ 完整的 Pipeline 流程
- ✅ FCPXML 1.13 导出

---

## 注意事项

### 给 AI 的指示

**每次对话结束后，你必须：**
1. 更新此 CLAUDE.md 文件
2. 在"最近改动"部分记录新的修改
3. 在"更新日志"部分添加日期条目
4. 更新相关的技术细节和设计决策
5. 如果有新的 TODO，添加到"TODO / 未来计划"

**更新格式：**
- 使用清晰的标题和分节
- 记录"为什么"而不仅仅是"做了什么"
- 包含关键代码路径和文件名
- 记录设计决策和权衡

**不要：**
- 删除历史记录
- 过度简化技术细节
- 忽略重要的上下文

---

## 联系方式

- 项目路径: `/run/media/orange/活爹_分裂副本 2/proj/kirinuki`
- 数据库: `backend/kirinuki.db`
- 工作目录: `data/`

### 2026-04-15: CPU float16 精度问题

**问题：**
- CPU 不支持 float16：`Requested float16 compute type, but the target device or backend do not support efficient float16 computation`

**解决方案：**
- 自动检测设备类型
- CPU 模式自动切换到 int8 精度
- GPU 模式保持 float16

**修改文件：**
- `backend/gpt_sovits_api.py` - 添加精度自动切换逻辑

---

### 2026-04-15: Whisper 模型加载问题

**问题：**
- Whisper 模型下载失败：`Connection to huggingface.co timed out`
- 网络无法访问 huggingface.co

**解决方案：**
1. 添加本地模型路径检测
2. 优先使用本地已下载的模型
3. 检查路径：
   - `~/.cache/huggingface/hub/models--Systran--faster-whisper-{model_size}/snapshots/`
   - `/home/orange/.cache/huggingface/hub/models--Systran--faster-whisper-{model_size}/snapshots/`
4. 如果本地模型不存在，给出清晰的错误提示

**修改文件：**
- `backend/gpt_sovits_api.py` - 添加本地模型路径支持

**手动下载模型（如果需要）：**
```bash
# 使用 huggingface-cli 下载
huggingface-cli download Systran/faster-whisper-small

# 或使用镜像
export HF_ENDPOINT=https://hf-mirror.com
huggingface-cli download Systran/faster-whisper-small
```

---

## 最新问题和解决方案

### 2026-04-15: GPT-SoVITS API 启动问题

**问题：**
1. 默认环境没有 torch：`ModuleNotFoundError: No module named 'torch'`
2. sovits conda 环境有 CUDA 版本不匹配：`libcudart.so.13: cannot open shared object file`
3. 导入了不必要的 `funasr_asr` 导致 torchaudio 加载失败

**解决方案：**
1. 移除了 `from tools.asr.fasterwhisper_asr import execute_asr` 导入（不需要）
2. 直接使用 `faster_whisper.WhisperModel`
3. 需要在 sovits conda 环境中运行：
   ```bash
   conda activate sovits
   python backend/gpt_sovits_api.py --port 9000
   ```

**修改文件：**
- `backend/gpt_sovits_api.py` - 移除不必要的导入

**注意事项：**
- GPT-SoVITS API 必须在有 PyTorch 的环境中运行
- 推荐使用独立的 conda 环境（如 sovits）
- 如果遇到 CUDA 版本问题，检查 PyTorch 和 CUDA 版本是否匹配

---

**最后更新**: 2026-04-15
**更新者**: Claude (Opus 4.6)
**更新内容**: 
- 修正了对多模态模型作用的描述（不只是看画面，而是综合分析文本+画面，判断"能不能火"）
- 补充了 irasutoya 插画系统的详细设计目标和当前状态
- 发现并记录了问题：irasutoya 只有 API 桥接，未集成到 Pipeline 流程
- 更新了 TODO 列表，添加了插画系统集成任务
- **重写了多模态分析阶段**：
  - 创建全新的 MultimodalAnalyzer（一次性分析整个视频）
  - 废弃了旧的分块筛选和候选生成步骤
  - Pipeline 从 6 步简化为 4 步
  - 输出 Markdown 报告（人类可读）+ JSON 数据（结构化）
  - 完全信任多模态模型的判断能力，不再需要规则打分和初筛
- **修复了数据库问题**：
  - 从内存数据库（`:memory:`）改为持久化 SQLite 文件（`kirinuki.db`）
  - 解决了 FastAPI hot reload 导致数据丢失的问题
- **实现了断点续跑功能**：
  - Pipeline 失败后可以从断点继续运行
  - 自动检查并跳过已完成的步骤
  - 只执行未完成或失败的步骤
