"""
多模态分析器 - 重写版本（两阶段分析）

设计方案：
- 第一阶段：纯文本分析，找出高光片段的时间范围
- 第二阶段：对每个片段提取关键帧，生成标题和标签
- 超时时间：30 分钟（1800 秒）
"""

from typing import List, Dict, Optional
import httpx
import base64
import json
import re
import logging
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ClipSegment:
    """高光片段"""
    start_time: float  # 开始时间（秒）
    end_time: float    # 结束时间（秒）
    title: str         # B站风格标题
    tags: List[str]    # 标签列表
    score: float       # 评分 0-10
    reason: str        # 为什么这个片段能火


class MultimodalAnalyzer:
    """多模态分析器 - 两阶段分析"""

    def __init__(self, config: dict):
        self.base_url = config.get("base_url")
        self.api_key = config.get("api_key")
        self.model = config.get("model")
        self.timeout = config.get("timeout_seconds", 1800)  # 默认 30 分钟
        self.provider_type = config.get("provider_type", "openai_compatible")  # anthropic 或 openai_compatible
        self.supports_vision = config.get("supports_vision", True)  # 是否支持多模态（图片）

    async def analyze_full_video(
        self,
        transcript_segments: List[Dict],  # 转录片段列表 [{text, start, end}, ...]
        video_path: str,  # 视频文件路径
        video_duration: float,  # 视频总时长（秒）
        ffmpeg_service  # FFmpeg 服务实例
    ) -> Dict:
        """
        两阶段分析整个视频

        阶段 1：纯文本分析，找出高光片段的时间范围
        阶段 2：对每个片段提取关键帧，生成标题和标签

        返回：
        {
            "markdown_summary": "人类可读的分析报告",
            "clips": [ClipSegment, ...],
            "raw_response_stage1": "阶段1原始响应",
            "raw_response_stage2": "阶段2原始响应"
        }
        """
        # 阶段 1：纯文本分析
        print("  🔍 [阶段 1/2] 纯文本分析，找出高光片段...")
        full_transcript = self._build_full_transcript(transcript_segments)
        stage1_response = await self._stage1_text_analysis(full_transcript, video_duration)

        # 解析阶段 1 结果
        time_ranges = self._extract_time_ranges(stage1_response)
        print(f"  ✓ 找到 {len(time_ranges)} 个候选片段")

        # 检查是否支持视觉分析
        if not self.supports_vision:
            print(f"  ⚠️  当前模型不支持多模态（图片）分析，跳过阶段 2")
            print(f"  ⚠️  将使用纯文本分析结果，可能降低识别准确度")

            # 仅使用阶段 1 的结果，生成简化的片段数据
            clips = []
            for time_range in time_ranges:
                clips.append(ClipSegment(
                    start_time=time_range['start'],
                    end_time=time_range['end'],
                    title=time_range.get('brief_reason', '未命名片段'),
                    tags=[],  # 纯文本模式无标签
                    score=5.0,  # 默认评分
                    reason=time_range.get('brief_reason', '')
                ))

            markdown_summary = self._generate_markdown_summary(clips, video_duration)

            return {
                "markdown_summary": markdown_summary,
                "clips": clips,
                "raw_response_stage1": stage1_response,
                "raw_response_stage2": "(跳过视觉分析 - 模型不支持多模态)"
            }

        # 阶段 2：对每个片段分析关键帧
        print(f"  🎬 [阶段 2/2] 对每个片段提取关键帧并生成标题...")
        clips = []
        stage2_responses = []

        for i, time_range in enumerate(time_ranges):
            print(f"    [{i+1}/{len(time_ranges)}] 分析片段 {time_range['start']:.1f}s - {time_range['end']:.1f}s")

            # 提取该片段的关键帧
            keyframe_dir = Path(f"/tmp/kirinuki_keyframes_{i}")
            keyframe_dir.mkdir(parents=True, exist_ok=True)

            keyframes = ffmpeg_service.extract_keyframes(
                video_path,
                str(keyframe_dir),
                start_seconds=time_range['start'],
                end_seconds=time_range['end'],
                interval=3.0  # 每 3 秒一帧
            )

            # 获取该片段的转录文本
            segment_text = self._get_segment_text(
                transcript_segments,
                time_range['start'],
                time_range['end']
            )

            # 调用阶段 2 分析
            stage2_response = await self._stage2_visual_analysis(
                segment_text,
                keyframe_dir,
                time_range['start'],
                time_range['end']
            )

            stage2_responses.append(stage2_response)

            # 解析结果
            clip_data = self._extract_clip_data(stage2_response)
            clips.append(ClipSegment(
                start_time=time_range['start'],
                end_time=time_range['end'],
                title=clip_data.get('title', '未命名片段'),
                tags=clip_data.get('tags', []),
                score=clip_data.get('score', 5.0),
                reason=clip_data.get('reason', '')
            ))

            print(f"    ✓ {clip_data.get('title', '未命名片段')} (评分: {clip_data.get('score', 5.0):.1f})")

        # 生成 Markdown 总结
        markdown_summary = self._generate_markdown_summary(clips, video_duration)

        return {
            "markdown_summary": markdown_summary,
            "clips": clips,
            "raw_response_stage1": stage1_response,
            "raw_response_stage2": "\n\n---\n\n".join(stage2_responses)
        }

    def _build_full_transcript(self, segments: List[Dict]) -> str:
        """构建完整转录文本，带时间戳"""
        lines = []
        for seg in segments:
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            text = seg.get("text", "").strip()
            if text:
                start_str = self._format_timestamp(start)
                end_str = self._format_timestamp(end)
                lines.append(f"[{start_str} - {end_str}] {text}")
        return "\n".join(lines)

    def _format_timestamp(self, seconds: float) -> str:
        """格式化时间戳为 HH:MM:SS"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _get_segment_text(self, segments: List[Dict], start: float, end: float) -> str:
        """获取指定时间范围内的转录文本"""
        texts = []
        for seg in segments:
            seg_start = seg.get("start", 0)
            seg_end = seg.get("end", 0)
            # 如果片段与时间范围有重叠
            if seg_start < end and seg_end > start:
                texts.append(seg.get("text", "").strip())
        return " ".join(texts)

    async def _stage1_text_analysis(self, full_transcript: str, video_duration: float) -> str:
        """阶段 1：纯文本分析，找出高光片段"""
        duration_str = self._format_timestamp(video_duration)

        prompt = f"""你是一个专业的 VTuber 直播切片分析师。你的任务是分析这个直播录像的转录文本，找出所有适合做成切片视频的高光片段。

# 视频信息
- 总时长：{duration_str}
- 完整转录文本（带时间戳）：

{full_transcript}

# 你的任务
仔细阅读转录文本，找出所有"B站观众喜欢的高光片段"，包括但不限于：
- 搞笑名场面（笑声、梗、整活）
- 情绪爆发（惊讶、感动、愤怒）
- 技术高光（游戏操作、唱歌高音）
- 互动名场面（与观众/其他主播的有趣互动）
- 意外事件（突发状况、翻车）

# 输出格式

在 ```json 代码块中输出所有高光片段的时间范围：

```json
{{
  "clips": [
    {{
      "start_time": 123.5,
      "end_time": 156.8,
      "brief_reason": "主播突然笑场"
    }},
    {{
      "start_time": 890.2,
      "end_time": 920.0,
      "brief_reason": "技术操作精彩"
    }}
  ]
}}
```

# 注意事项
- 时间戳必须精确（从转录文本中提取）
- 片段长度建议：30秒 - 3分钟
- 不要遗漏任何有潜力的片段
- brief_reason 简短说明（5-10 字）

现在开始分析吧！"""

        return await self._call_text_api(prompt)

    async def _stage2_visual_analysis(
        self,
        segment_text: str,
        keyframe_dir: Path,
        start_time: float,
        end_time: float
    ) -> str:
        """阶段 2：分析关键帧，生成标题和标签"""
        # 加载关键帧
        keyframe_images = self._load_keyframes(keyframe_dir)

        start_str = self._format_timestamp(start_time)
        end_str = self._format_timestamp(end_time)

        prompt = f"""你是一个专业的 VTuber 直播切片分析师。现在需要为这个高光片段生成 B 站风格的标题和标签。

# 片段信息
- 时间范围：{start_str} - {end_str}
- 转录文本：{segment_text}
- 关键帧：已提供 {len(keyframe_images)} 张

# 你的任务
综合分析转录文本和关键帧，生成：
1. B 站风格的标题（简短、吸引人、带梗、口语化）
2. 标签（2-3 个关键词）
3. 评分（0-10 分，越高越适合做切片）
4. 理由（为什么这个片段能火，1-2 句话）

# 输出格式

```json
{{
  "title": "主播笑死我了哈哈哈",
  "tags": ["搞笑", "名场面"],
  "score": 9.5,
  "reason": "主播突然笑场，情绪感染力强，弹幕肯定爆炸"
}}
```

现在开始分析吧！"""

        return await self._call_multimodal_api(prompt, keyframe_images)

    def _load_keyframes(self, keyframe_dir: Path) -> List[Dict]:
        """加载关键帧图片（base64编码）"""
        images = []
        if not keyframe_dir.exists():
            return images

        image_files = sorted(keyframe_dir.glob("*.jpg")) + sorted(keyframe_dir.glob("*.png"))

        for img_path in image_files:
            try:
                with open(img_path, "rb") as f:
                    img_data = base64.b64encode(f.read()).decode()
                    images.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": img_data
                        }
                    })
            except Exception as e:
                print(f"加载关键帧失败 {img_path}: {e}")
                continue

        return images

    async def _call_text_api(self, prompt: str) -> str:
        """调用纯文本 API"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 判断 API 类型（根据 provider_type）
                if self.provider_type == "anthropic":
                    # Anthropic API
                    response = await client.post(
                        f"{self.base_url.rstrip('/')}/v1/messages",
                        headers={
                            "x-api-key": self.api_key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json"
                        },
                        json={
                            "model": self.model,
                            "max_tokens": 4096,
                            "messages": [{"role": "user", "content": prompt}]
                        }
                    )
                else:
                    # OpenAI-compatible API
                    response = await client.post(
                        f"{self.base_url.rstrip('/')}/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={
                            "model": self.model,
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": 4096,
                            "temperature": 0.7
                        }
                    )

                response.raise_for_status()
                result = response.json()

                # 打印完整响应用于调试
                logger.info(f"  📥 文本 API 响应: {json.dumps(result, ensure_ascii=False, indent=2)[:2000]}")

                # 提取响应文本 - 兼容多种格式
                try:
                    # 标准 Anthropic 格式
                    if "content" in result and isinstance(result["content"], list):
                        # 遍历 content 数组，找到 type="text" 的元素
                        for item in result["content"]:
                            if isinstance(item, dict):
                                # 优先找 type="text" 的元素
                                if item.get("type") == "text" and "text" in item:
                                    return item["text"]
                        # 如果没有找到 type="text"，尝试第一个有 text 字段的元素
                        for item in result["content"]:
                            if isinstance(item, dict) and "text" in item:
                                return item["text"]
                        # 如果 content[0] 是字符串
                        if isinstance(result["content"][0], str):
                            return result["content"][0]
                    # OpenAI 格式
                    elif "choices" in result:
                        return result["choices"][0]["message"]["content"]
                    # 直接返回 content 字符串
                    elif "content" in result and isinstance(result["content"], str):
                        return result["content"]
                    else:
                        logger.error(f"  未知的响应格式: {json.dumps(result, ensure_ascii=False, indent=2)}")
                        raise ValueError(f"未知的响应格式，请检查日志")
                except (KeyError, IndexError, TypeError) as e:
                    logger.error(f"  解析响应失败: {e}")
                    logger.error(f"  完整响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                    raise ValueError(f"解析响应失败: {e}")

        except Exception as e:
            raise RuntimeError(f"文本 API 调用失败: {e}")

    async def _call_multimodal_api(self, prompt: str, images: List[Dict]) -> str:
        """调用多模态 API"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                content = [{"type": "text", "text": prompt}] + images

                # 判断 API 类型（根据 provider_type）
                if self.provider_type == "anthropic":
                    # Anthropic API
                    payload = {
                        "model": self.model,
                        "max_tokens": 2048,
                        "messages": [{"role": "user", "content": content}]
                    }
                    logger.info(f"  📤 发送 Anthropic API 请求: {len(images)} 张图片")
                    logger.debug(f"  请求 payload (不含图片): model={self.model}, max_tokens=2048, content_items={len(content)}")

                    response = await client.post(
                        f"{self.base_url.rstrip('/')}/v1/messages",
                        headers={
                            "x-api-key": self.api_key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json"
                        },
                        json=payload
                    )
                else:
                    # OpenAI-compatible API
                    openai_images = []
                    for img in images:
                        if img["type"] == "image":
                            img_data = img["source"]["data"]
                            openai_images.append({
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}
                            })

                    payload = {
                        "model": self.model,
                        "messages": [{
                            "role": "user",
                            "content": [{"type": "text", "text": prompt}] + openai_images
                        }],
                        "max_tokens": 2048,
                        "temperature": 0.7
                    }
                    logger.info(f"  📤 发送 OpenAI-compatible API 请求: {len(openai_images)} 张图片")
                    logger.debug(f"  请求 payload (不含图片): model={self.model}, max_tokens=2048, content_items={len(openai_images)+1}")

                    response = await client.post(
                        f"{self.base_url.rstrip('/')}/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json=payload
                    )

                response.raise_for_status()
                result = response.json()

                # 打印完整响应用于调试
                logger.info(f"  📥 文本 API 响应: {json.dumps(result, ensure_ascii=False, indent=2)[:2000]}")

                # 提取响应文本 - 兼容多种格式
                try:
                    # 标准 Anthropic 格式
                    if "content" in result and isinstance(result["content"], list):
                        # 遍历 content 数组，找到 type="text" 的元素
                        for item in result["content"]:
                            if isinstance(item, dict):
                                # 优先找 type="text" 的元素
                                if item.get("type") == "text" and "text" in item:
                                    return item["text"]
                        # 如果没有找到 type="text"，尝试第一个有 text 字段的元素
                        for item in result["content"]:
                            if isinstance(item, dict) and "text" in item:
                                return item["text"]
                        # 如果 content[0] 是字符串
                        if isinstance(result["content"][0], str):
                            return result["content"][0]
                    # OpenAI 格式
                    elif "choices" in result:
                        return result["choices"][0]["message"]["content"]
                    # 直接返回 content 字符串
                    elif "content" in result and isinstance(result["content"], str):
                        return result["content"]
                    else:
                        logger.error(f"  未知的响应格式: {json.dumps(result, ensure_ascii=False, indent=2)}")
                        raise ValueError(f"未知的响应格式，请检查日志")
                except (KeyError, IndexError, TypeError) as e:
                    logger.error(f"  解析响应失败: {e}")
                    logger.error(f"  完整响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                    raise ValueError(f"解析响应失败: {e}")

        except httpx.HTTPStatusError as e:
            # 打印详细的错误信息
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = f"\n错误详情: {json.dumps(error_body, ensure_ascii=False, indent=2)}"
            except:
                error_detail = f"\n错误响应: {e.response.text}"

            logger.error(f"多模态 API 返回错误 {e.response.status_code}: {error_detail}")

            # 如果是 Anthropic 格式失败且是 400 错误，自动尝试 OpenAI 格式
            if self.provider_type == "anthropic" and e.response.status_code == 400 and images:
                logger.warning(f"  ⚠️  Anthropic 格式失败，自动尝试 OpenAI-compatible 格式...")
                try:
                    # 临时切换到 OpenAI 格式重试
                    original_type = self.provider_type
                    self.provider_type = "openai_compatible"
                    result = await self._call_multimodal_api(prompt, images)
                    self.provider_type = original_type
                    logger.info(f"  ✅ OpenAI 格式成功！建议在前端设置中将 provider_type 改为 'openai_compatible'")
                    return result
                except Exception as retry_error:
                    self.provider_type = original_type
                    logger.error(f"  ❌ OpenAI 格式也失败: {retry_error}")

            raise RuntimeError(f"多模态 API 调用失败 ({e.response.status_code}): {error_detail}")
        except Exception as e:
            raise RuntimeError(f"多模态 API 调用失败: {e}")

    def _extract_time_ranges(self, response: str) -> List[Dict]:
        """从阶段 1 响应中提取时间范围"""
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        if not json_match:
            json_match = re.search(r'\{[^{}]*"clips"[^{}]*\[.*?\]\s*\}', response, re.DOTALL)

        if not json_match:
            print("警告：未找到 JSON 数据")
            return []

        try:
            data = json.loads(json_match.group(1) if json_match.lastindex else json_match.group(0))
            time_ranges = []

            for clip in data.get("clips", []):
                time_ranges.append({
                    "start": float(clip.get("start_time", 0)),
                    "end": float(clip.get("end_time", 0)),
                    "brief_reason": clip.get("brief_reason", "")
                })

            return time_ranges

        except json.JSONDecodeError as e:
            print(f"JSON 解析失败: {e}")
            return []

    def _extract_clip_data(self, response: str) -> Dict:
        """从阶段 2 响应中提取片段数据"""
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        if not json_match:
            json_match = re.search(r'\{[^{}]*"title"[^{}]*\}', response, re.DOTALL)

        if not json_match:
            return {
                "title": "未命名片段",
                "tags": [],
                "score": 5.0,
                "reason": ""
            }

        try:
            data = json.loads(json_match.group(1) if json_match.lastindex else json_match.group(0))
            return {
                "title": data.get("title", "未命名片段"),
                "tags": data.get("tags", []),
                "score": float(data.get("score", 5.0)),
                "reason": data.get("reason", "")
            }
        except json.JSONDecodeError:
            return {
                "title": "未命名片段",
                "tags": [],
                "score": 5.0,
                "reason": ""
            }

    def _generate_markdown_summary(self, clips: List[ClipSegment], video_duration: float) -> str:
        """生成 Markdown 总结"""
        duration_str = self._format_timestamp(video_duration)

        lines = [
            f"# 视频分析报告",
            f"",
            f"**视频时长**: {duration_str}",
            f"**找到高光片段**: {len(clips)} 个",
            f"",
            f"## 高光片段列表",
            f""
        ]

        for i, clip in enumerate(clips, 1):
            start_str = self._format_timestamp(clip.start_time)
            end_str = self._format_timestamp(clip.end_time)
            tags_str = ", ".join([f"#{tag}" for tag in clip.tags])

            lines.append(f"### {i}. {clip.title}")
            lines.append(f"")
            lines.append(f"- **时间**: {start_str} - {end_str}")
            lines.append(f"- **评分**: {clip.score:.1f}/10")
            lines.append(f"- **标签**: {tags_str}")
            lines.append(f"- **理由**: {clip.reason}")
            lines.append(f"")

        return "\n".join(lines)
