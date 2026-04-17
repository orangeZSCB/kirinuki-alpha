from typing import List
from faster_whisper import WhisperModel
from app.services.transcription.base import TranscriptionProvider, TranscriptSegment

class LocalWhisperProvider(TranscriptionProvider):
    """本地 Whisper Provider"""

    def __init__(self, config: dict):
        self.model_size = config.get("model_size", "large-v3")
        self.device = config.get("device", "cuda")
        self.compute_type = config.get("compute_type", "float16")
        self.model = None

    def _load_model(self):
        """延迟加载模型"""
        if self.model is None:
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )

    async def transcribe(self, audio_path: str, language: str = "ja") -> List[TranscriptSegment]:
        """转录音频"""
        self._load_model()

        segments, info = self.model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )

        results = []
        for segment in segments:
            results.append(TranscriptSegment(
                start=segment.start,
                end=segment.end,
                text=segment.text.strip()
            ))

        return results

    async def test_connection(self) -> bool:
        """测试本地模型"""
        try:
            self._load_model()
            return True
        except Exception:
            return False
