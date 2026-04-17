from typing import List, Dict
import re

class CheapRanker:
    """低成本初筛器"""

    # 日语情绪关键词
    EMOTION_KEYWORDS = [
        "草", "笑", "やばい", "すごい", "えー", "マジ", "本当",
        "うそ", "嘘", "びっくり", "驚", "怖", "こわ", "かわいい",
        "可愛", "最高", "神", "ヤバ", "ガチ", "まじ", "ウケる",
        "爆笑", "面白", "おもしろ", "楽しい", "たのし", "嬉しい",
        "うれし", "悲しい", "かなし", "泣", "感動", "ありがと",
        "ごめん", "すみません", "助けて", "たすけて"
    ]

    @staticmethod
    def score_text(text: str, audio_score: float = 0.0) -> float:
        """基于文本和音频特征打分"""
        score = audio_score

        # 关键词密度
        keyword_count = sum(1 for kw in CheapRanker.EMOTION_KEYWORDS if kw in text)
        score += keyword_count * 0.5

        # 感叹号和问号
        exclamation_count = text.count("！") + text.count("!") + text.count("？") + text.count("?")
        score += min(exclamation_count * 0.3, 2.0)

        # 重复字符（表示强调）
        repeated_chars = len(re.findall(r'(.)\1{2,}', text))
        score += min(repeated_chars * 0.2, 1.0)

        # 文本长度（太短或太长都不好）
        text_length = len(text)
        if 50 < text_length < 500:
            score += 1.0
        elif text_length < 20:
            score -= 1.0

        return max(0.0, score)

    @staticmethod
    def rank_chunks(chunks: List[Dict]) -> List[Dict]:
        """对块进行排序并筛选"""
        # 按得分排序
        sorted_chunks = sorted(chunks, key=lambda x: x.get("score", 0.0), reverse=True)

        # 只保留前 25%
        threshold_index = max(1, len(sorted_chunks) // 4)
        return sorted_chunks[:threshold_index]
