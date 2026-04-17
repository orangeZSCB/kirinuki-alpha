from typing import List
import httpx
from pathlib import Path
import subprocess
import tempfile
import os
import logging
import asyncio
from app.services.transcription.base import TranscriptionProvider, TranscriptSegment

logger = logging.getLogger(__name__)

class RemoteWhisperProvider(TranscriptionProvider):
    """远程 Whisper Provider（OpenAI-compatible API）"""

    def __init__(self, config: dict):
        self.base_url = config.get("base_url")
        self.api_key = config.get("api_key")
        self.model_request_id = config.get("model_request_id", "whisper-1")
        self.endpoint_path = config.get("endpoint_path", "/audio/transcriptions")
        self.response_format = config.get("response_format", "verbose_json")
        self.max_file_size_mb = config.get("max_file_size_mb", 20)  # 默认 20MB，留点余量

    def _split_audio(self, audio_path: str, chunk_duration: int = 600) -> List[str]:
        """将音频切分成小块（默认 10 分钟）"""
        temp_dir = tempfile.mkdtemp()
        chunk_paths = []

        # 获取音频时长
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        duration = float(subprocess.check_output(probe_cmd).decode().strip())
        logger.info(f"  📏 音频总时长: {duration:.1f}秒")

        # 切分音频
        num_chunks = int(duration / chunk_duration) + 1
        logger.info(f"  ✂️  将切分为 {num_chunks} 个块（每块 {chunk_duration}秒）")

        for i in range(num_chunks):
            start_time = i * chunk_duration
            chunk_path = os.path.join(temp_dir, f"chunk_{i:03d}.wav")

            cmd = [
                "ffmpeg", "-y", "-i", audio_path,
                "-ss", str(start_time),
                "-t", str(chunk_duration),
                "-c", "copy",
                chunk_path
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            chunk_paths.append(chunk_path)

            chunk_size_mb = os.path.getsize(chunk_path) / (1024 * 1024)
            logger.info(f"    ✓ 块 {i+1}/{num_chunks}: {chunk_size_mb:.1f}MB")

        logger.info(f"  ✅ 切分完成")
        return chunk_paths

    async def _transcribe_single(self, audio_path: str, language: str, max_retries: int = 3) -> List[TranscriptSegment]:
        """转录单个音频文件，带重试机制"""
        url = f"{self.base_url.rstrip('/')}{self.endpoint_path}"

        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        logger.info(f"    📤 开始上传: {Path(audio_path).name} ({file_size_mb:.1f}MB)")

        with open(audio_path, "rb") as f:
            audio_content = f.read()

        for attempt in range(max_retries):
            try:
                logger.info(f"    ⏳ 等待 API 响应... (尝试 {attempt + 1}/{max_retries})")

                # 使用更短的超时，并且设置连接超时
                timeout = httpx.Timeout(10.0, read=180.0)  # 连接超时 10s，读取超时 3 分钟

                async with httpx.AsyncClient(timeout=timeout) as client:
                    files = {"file": (Path(audio_path).name, audio_content, "audio/wav")}
                    data = {
                        "model": self.model_request_id,
                        "language": language,
                        "response_format": self.response_format
                    }
                    headers = {"Authorization": f"Bearer {self.api_key}"}

                    response = await client.post(url, files=files, data=data, headers=headers)
                    response.raise_for_status()

                    # 调试：打印原始响应
                    logger.info(f"    🔍 API 响应状态: {response.status_code}")
                    logger.info(f"    🔍 响应头: {dict(response.headers)}")
                    raw_text = response.text
                    logger.info(f"    🔍 响应内容（前 500 字符）: {raw_text[:500]}")

                    result = response.json()
                    logger.info(f"    🔍 解析后的 JSON: {result}")

                    segments = []
                    if result and "segments" in result:
                        for seg in result["segments"]:
                            segments.append(TranscriptSegment(
                                start=seg["start"],
                                end=seg["end"],
                                text=seg["text"].strip()
                            ))
                    elif result and "text" in result:
                        segments.append(TranscriptSegment(
                            start=0.0,
                            end=0.0,
                            text=result["text"].strip()
                        ))

                    logger.info(f"    ✅ 转录完成: {Path(audio_path).name}，得到 {len(segments)} 个片段")
                    return segments

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                logger.warning(f"    ⚠️  请求超时或连接失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"    🔄 等待 5 秒后重试...")
                    await asyncio.sleep(5)
                else:
                    logger.error(f"    ❌ 重试 {max_retries} 次后仍然失败")
                    raise
            except Exception as e:
                logger.error(f"    ❌ 转录失败: {str(e)}")
                raise

    async def transcribe(self, audio_path: str, language: str = "ja") -> List[TranscriptSegment]:
        """通过远程 API 转录音频，自动处理大文件"""
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        logger.info(f"  📊 音频文件大小: {file_size_mb:.1f}MB")

        # 如果文件小于限制，直接转录
        if file_size_mb <= self.max_file_size_mb:
            logger.info(f"  ✓ 文件小于 {self.max_file_size_mb}MB，直接转录")
            return await self._transcribe_single(audio_path, language)

        # 大文件：切分后逐块转录
        logger.info(f"  ⚠️  文件超过 {self.max_file_size_mb}MB 限制，需要切分")
        chunk_paths = self._split_audio(audio_path, chunk_duration=600)
        all_segments = []

        try:
            total_chunks = len(chunk_paths)
            logger.info(f"  🔄 开始逐块转录（共 {total_chunks} 个块）")

            for i, chunk_path in enumerate(chunk_paths):
                logger.info(f"  📦 [{i+1}/{total_chunks}] 正在处理块 {i+1}...")
                chunk_segments = await self._transcribe_single(chunk_path, language)

                # 调整时间偏移
                time_offset = i * 600
                for seg in chunk_segments:
                    seg.start += time_offset
                    seg.end += time_offset
                    all_segments.append(seg)

                logger.info(f"  ✅ [{i+1}/{total_chunks}] 块 {i+1} 完成，累计 {len(all_segments)} 个片段")
        finally:
            # 清理临时文件
            logger.info("  🧹 清理临时文件...")
            for chunk_path in chunk_paths:
                try:
                    os.remove(chunk_path)
                except:
                    pass
            try:
                os.rmdir(os.path.dirname(chunk_paths[0]))
            except:
                pass

        logger.info(f"  🎉 转录完成！总共 {len(all_segments)} 个片段")
        return all_segments

    async def test_connection(self) -> bool:
        """测试远程 API 连接"""
        try:
            url = f"{self.base_url.rstrip('/')}/models"
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                response = await client.get(url, headers=headers)
                return response.status_code == 200
        except Exception:
            return False
