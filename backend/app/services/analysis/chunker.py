from typing import List, Tuple

class Chunker:
    """将长视频分块"""

    @staticmethod
    def create_chunks(
        duration_seconds: float,
        chunk_size: int = 300,  # 5 分钟
        overlap: int = 15  # 15 秒重叠
    ) -> List[Tuple[float, float]]:
        """创建时间块"""
        chunks = []
        start = 0.0

        while start < duration_seconds:
            end = min(start + chunk_size, duration_seconds)
            chunks.append((start, end))

            # 下一个块的起点考虑重叠
            start = end - overlap
            if start >= duration_seconds:
                break

        return chunks
