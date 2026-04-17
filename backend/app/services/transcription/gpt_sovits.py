from typing import List
import httpx
from pathlib import Path
import logging
import re
from app.services.transcription.base import TranscriptionProvider, TranscriptSegment

logger = logging.getLogger(__name__)

# 从文件名解析时间戳（samples）
SEGMENT_RE = re.compile(r"_(\d{1,})_(\d{1,})\.wav$", re.IGNORECASE)
SAMPLE_RATE = 32000


def samples_to_seconds(samples: int) -> float:
    """将采样数转换为秒"""
    return samples / SAMPLE_RATE


def samples_to_srt_time(samples: int) -> str:
    """将采样数转换为 SRT 时间格式"""
    total_ms = round(samples * 1000 / SAMPLE_RATE)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


class GPTSoVITSProvider(TranscriptionProvider):
    """
    GPT-SoVITS Provider

    调用 GPT-SoVITS API 完成：
    1. UVR5 人声分离（去除 BGM）
    2. Slicer 语音切分
    3. Faster Whisper 识别
    4. 生成 SRT 字幕文件
    """

    def __init__(self, config: dict):
        self.base_url = config.get("base_url", "http://localhost:9000")
        self.model_size = config.get("model_size", "large-v3")
        self.skip_uvr = config.get("skip_uvr", False)
        self.skip_slice = config.get("skip_slice", False)

    async def transcribe(self, audio_path: str, language: str = "ja") -> List[TranscriptSegment]:
        """
        通过 GPT-SoVITS API 转录音频

        Args:
            audio_path: 原始音频路径
            language: 语言代码

        Returns:
            转录片段列表（带时间戳）
        """
        logger.info(f"📡 调用 GPT-SoVITS API: {self.base_url}")
        logger.info(f"  音频: {audio_path}")
        logger.info(f"  语言: {language}")
        logger.info(f"  模型: {self.model_size}")
        logger.info(f"  跳过 UVR: {self.skip_uvr}")
        logger.info(f"  跳过切分: {self.skip_slice}")

        url = f"{self.base_url.rstrip('/')}/process"

        try:
            # 读取音频文件
            with open(audio_path, "rb") as f:
                audio_content = f.read()

            # 调用 API
            async with httpx.AsyncClient(timeout=3600.0) as client:
                files = {"file": (Path(audio_path).name, audio_content, "audio/wav")}
                data = {
                    "language": language,
                    "model_size": self.model_size,
                    "skip_uvr": str(self.skip_uvr).lower(),
                    "skip_slice": str(self.skip_slice).lower(),
                }

                logger.info("  ⏳ 等待 API 处理...")
                response = await client.post(url, files=files, data=data)
                response.raise_for_status()

                result = response.json()
                logger.info(f"  ✅ API 处理完成")
                logger.info(f"  Job ID: {result['job_id']}")

                # 解析转录结果
                transcription = result.get("transcription", [])
                if not transcription:
                    logger.warning("  ⚠️  API 返回空转录结果")
                    return []

                logger.info(f"  📝 收到 {len(transcription)} 个转录片段")

                # 转换为 TranscriptSegment
                segments = []
                for item in transcription:
                    if "error" in item:
                        logger.warning(f"  ⚠️  片段识别失败: {item['file']} - {item['error']}")
                        continue

                    # 从文件名解析时间戳
                    filename = item.get("file", "")
                    match = SEGMENT_RE.search(filename)
                    if not match:
                        logger.warning(f"  ⚠️  无法解析时间戳: {filename}")
                        continue

                    start_samples = int(match.group(1))
                    end_samples = int(match.group(2))
                    text = item.get("text", "").strip()

                    if not text:
                        continue

                    segments.append(TranscriptSegment(
                        start=samples_to_seconds(start_samples),
                        end=samples_to_seconds(end_samples),
                        text=text
                    ))

                # 按时间排序
                segments.sort(key=lambda s: (s.start, s.end))

                logger.info(f"  🎉 转录完成！共 {len(segments)} 个有效片段")
                return segments

        except httpx.HTTPStatusError as e:
            logger.error(f"  ❌ API 返回错误: {e.response.status_code}")
            logger.error(f"  响应内容: {e.response.text}")
            raise Exception(f"GPT-SoVITS API 错误: {e.response.text}")
        except Exception as e:
            logger.error(f"  ❌ 转录失败: {str(e)}")
            raise

    async def test_connection(self) -> bool:
        """测试 GPT-SoVITS API 连接"""
        try:
            url = f"{self.base_url.rstrip('/')}/health"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"✅ GPT-SoVITS API 连接成功")
                    logger.info(f"  设备: {result.get('device', 'unknown')}")
                    logger.info(f"  CUDA: {result.get('cuda_available', False)}")
                    return True
                return False
        except Exception as e:
            logger.error(f"❌ GPT-SoVITS API 连接失败: {str(e)}")
            return False

    def save_srt(self, segments: List[TranscriptSegment], output_path: str) -> None:
        """
        保存为 SRT 字幕文件

        Args:
            segments: 转录片段列表
            output_path: 输出文件路径
        """
        with open(output_path, "w", encoding="utf-8", newline="\n") as f:
            for index, seg in enumerate(segments, start=1):
                # 转换为 SRT 时间格式
                start_samples = int(seg.start * SAMPLE_RATE)
                end_samples = int(seg.end * SAMPLE_RATE)

                start_time = samples_to_srt_time(start_samples)
                end_time = samples_to_srt_time(end_samples)

                f.write(f"{index}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{seg.text}\n\n")

        logger.info(f"💾 SRT 字幕已保存: {output_path}")
