from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class TranscriptSegment:
    """转录段落"""
    start: float
    end: float
    text: str

class TranscriptionProvider(ABC):
    """转录 Provider 抽象基类"""

    @abstractmethod
    async def transcribe(self, audio_path: str, language: str = "ja") -> List[TranscriptSegment]:
        """转录音频文件"""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """测试连接"""
        pass
