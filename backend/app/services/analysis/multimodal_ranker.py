from typing import List, Dict
import httpx
import base64
from pathlib import Path

class MultimodalRanker:
    """多模态复审器"""

    def __init__(self, config: dict):
        self.base_url = config.get("base_url")
        self.api_key = config.get("api_key")
        self.model = config.get("model")
        self.timeout = config.get("timeout_seconds", 120)
        self.max_frames = config.get("max_frames_per_candidate", 8)

    async def review_candidate(
        self,
        transcript_text: str,
        keyframe_paths: List[str],
        audio_features: Dict
    ) -> Dict:
        """复审候选片段"""
        # 准备图片（base64 编码）
        images = []
        for path in keyframe_paths[:self.max_frames]:
            try:
                with open(path, "rb") as f:
                    img_data = base64.b64encode(f.read()).decode()
                    images.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_data}"
                        }
                    })
            except Exception:
                continue

        # 构建 prompt
        prompt = f"""分析这个直播片段是否适合作为切片视频。

转录文本：
{transcript_text}

音频特征：
- 音量峰值比例: {audio_features.get('peak_ratio', 0):.2f}
- 音量变化: {audio_features.get('volume_variance', 0):.2f}

请评估：
1. 这个片段的有趣程度（0-10分）
2. 推荐的标题（简短、吸引人）
3. 简短总结（1-2句话）
4. 标签（2-3个关键词）

以 JSON 格式返回：
{{
  "score": 8.5,
  "title": "标题",
  "summary": "总结",
  "tags": ["标签1", "标签2"]
}}"""

        # 调用 API
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            *images
                        ]
                    }
                ]

                response = await client.post(
                    f"{self.base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": 500,
                        "temperature": 0.7
                    }
                )

                response.raise_for_status()
                result = response.json()

                # 解析响应
                content = result["choices"][0]["message"]["content"]

                # 尝试提取 JSON
                import json
                import re
                json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    return {
                        "score": float(data.get("score", 5.0)),
                        "title": data.get("title", ""),
                        "summary": data.get("summary", ""),
                        "tags": data.get("tags", [])
                    }
                else:
                    return {
                        "score": 5.0,
                        "title": "未命名片段",
                        "summary": content[:100],
                        "tags": []
                    }

        except Exception as e:
            print(f"多模态分析失败: {e}")
            return {
                "score": 5.0,
                "title": "未命名片段",
                "summary": "",
                "tags": []
            }
