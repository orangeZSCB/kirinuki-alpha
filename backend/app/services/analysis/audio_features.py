import numpy as np
import librosa
from typing import Dict, List

class AudioFeatureExtractor:
    """音频特征提取器"""

    @staticmethod
    def extract_features(audio_path: str, sr: int = 16000) -> Dict:
        """提取音频特征"""
        # 加载音频
        y, sr = librosa.load(audio_path, sr=sr)

        # 计算 RMS 能量
        rms = librosa.feature.rms(y=y)[0]

        # 计算短时能量变化
        energy = np.array([
            np.sum(np.abs(y[i:i+sr//10])**2)
            for i in range(0, len(y), sr//10)
        ])

        # 检测静音段
        silence_threshold = np.percentile(rms, 20)
        silence_frames = rms < silence_threshold

        # 检测音量峰值
        volume_threshold = np.percentile(rms, 80)
        peak_frames = rms > volume_threshold

        # 计算每秒的特征
        frame_rate = len(rms) / (len(y) / sr)

        return {
            "rms": rms.tolist(),
            "energy": energy.tolist(),
            "silence_frames": silence_frames.tolist(),
            "peak_frames": peak_frames.tolist(),
            "frame_rate": frame_rate,
            "duration": len(y) / sr
        }

    @staticmethod
    def score_segment(features: Dict, start_sec: float, end_sec: float) -> float:
        """为音频片段打分"""
        # 如果特征为空或缺失关键字段，返回 0
        if not features or "frame_rate" not in features or "rms" not in features:
            return 0.0

        frame_rate = features["frame_rate"]
        start_frame = int(start_sec * frame_rate)
        end_frame = int(end_sec * frame_rate)

        rms = np.array(features["rms"][start_frame:end_frame])
        peak_frames = np.array(features.get("peak_frames", [])[start_frame:end_frame])
        silence_frames = np.array(features.get("silence_frames", [])[start_frame:end_frame])

        if len(rms) == 0:
            return 0.0

        score = 0.0

        # 高音量峰值加分
        peak_ratio = np.sum(peak_frames) / len(peak_frames)
        score += peak_ratio * 3.0

        # 音量变化加分
        if len(rms) > 1:
            volume_variance = np.std(rms)
            score += min(volume_variance * 2.0, 2.0)

        # 长静音减分
        silence_ratio = np.sum(silence_frames) / len(silence_frames)
        score -= silence_ratio * 2.0

        return max(0.0, score)
