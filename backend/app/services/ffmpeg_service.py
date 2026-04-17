import subprocess
import json
from pathlib import Path
from typing import Dict, Any
from app.core.config import settings

class FFmpegService:
    """FFmpeg 视频处理服务"""

    @staticmethod
    def probe_video(video_path: str) -> Dict[str, Any]:
        """使用 ffprobe 获取视频元信息"""
        cmd = [
            settings.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"ffprobe 失败: {result.stderr}")

        data = json.loads(result.stdout)

        # 提取视频流信息
        video_stream = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
        audio_stream = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)

        if not video_stream:
            raise Exception("未找到视频流")

        # 计算 FPS
        fps = None
        if "r_frame_rate" in video_stream:
            num, den = map(int, video_stream["r_frame_rate"].split("/"))
            fps = num / den if den != 0 else None

        return {
            "duration": float(data["format"].get("duration", 0)),
            "width": int(video_stream.get("width", 0)),
            "height": int(video_stream.get("height", 0)),
            "fps": fps,
            "has_audio": audio_stream is not None,
            "format_name": data["format"].get("format_name", ""),
        }

    @staticmethod
    def extract_audio(video_path: str, output_path: str) -> str:
        """从视频中提取音频为 WAV 格式"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            settings.ffmpeg_path,
            "-i", video_path,
            "-vn",  # 不处理视频
            "-acodec", "pcm_s16le",  # PCM 16-bit
            "-ar", "16000",  # 16kHz 采样率（Whisper 推荐）
            "-ac", "1",  # 单声道
            "-y",  # 覆盖输出文件
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"音频提取失败: {result.stderr}")

        return output_path

    @staticmethod
    def extract_keyframes(video_path: str, output_dir: str, start_seconds: float, end_seconds: float, interval: float = 2.0):
        """提取关键帧"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        duration = end_seconds - start_seconds
        num_frames = max(1, int(duration / interval))

        keyframes = []
        for i in range(num_frames):
            timestamp = start_seconds + (i * interval)
            if timestamp >= end_seconds:
                break

            output_file = Path(output_dir) / f"frame_{timestamp:.2f}.jpg"
            cmd = [
                settings.ffmpeg_path,
                "-ss", str(timestamp),
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "2",
                "-y",
                str(output_file)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                keyframes.append(str(output_file))

        return keyframes
