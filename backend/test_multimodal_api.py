#!/usr/bin/env python3
"""
测试多模态 API 的两种格式
"""
import asyncio
import httpx
import base64
import json
from pathlib import Path

# 从数据库读取配置
import sqlite3
db_path = Path(__file__).parent / "kirinuki.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT config FROM provider_configs WHERE provider_kind = 'multimodal' LIMIT 1")
row = cursor.fetchone()
config = json.loads(row[0])
conn.close()

BASE_URL = config["base_url"]
API_KEY = base64.b64decode(config["api_key"]).decode()
MODEL = config["model"]
PROVIDER_TYPE = config.get("provider_type", "anthropic")

print(f"配置信息:")
print(f"  BASE_URL: {BASE_URL}")
print(f"  MODEL: {MODEL}")
print(f"  PROVIDER_TYPE: {PROVIDER_TYPE}")
print()

# 创建一个简单的测试图片（1x1 红色像素）
test_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="

async def test_anthropic_format():
    """测试 Anthropic 格式"""
    print("=" * 60)
    print("测试 Anthropic 格式 (/v1/messages)")
    print("=" * 60)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "model": MODEL,
                "max_tokens": 100,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "这是什么颜色？"},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": test_image_base64
                            }
                        }
                    ]
                }]
            }

            print(f"请求 URL: {BASE_URL.rstrip('/')}/v1/messages")
            print(f"请求头: x-api-key, anthropic-version")
            print(f"请求体: {json.dumps({k: v for k, v in payload.items() if k != 'messages'}, indent=2)}")
            print(f"  + 1 条消息（1 文本 + 1 图片）")
            print()

            response = await client.post(
                f"{BASE_URL.rstrip('/')}/v1/messages",
                headers={
                    "x-api-key": API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json=payload
            )

            print(f"响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"✅ 成功！")
                print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}")
            else:
                print(f"❌ 失败！")
                try:
                    error = response.json()
                    print(f"错误详情: {json.dumps(error, ensure_ascii=False, indent=2)}")
                except:
                    print(f"错误响应: {response.text}")

    except Exception as e:
        print(f"❌ 异常: {e}")

    print()

async def test_openai_format():
    """测试 OpenAI-compatible 格式"""
    print("=" * 60)
    print("测试 OpenAI-compatible 格式 (/chat/completions)")
    print("=" * 60)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "model": MODEL,
                "max_tokens": 100,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "这是什么颜色？"},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{test_image_base64}"}
                        }
                    ]
                }]
            }

            print(f"请求 URL: {BASE_URL.rstrip('/')}/chat/completions")
            print(f"请求头: Authorization: Bearer ***")
            print(f"请求体: {json.dumps({k: v for k, v in payload.items() if k != 'messages'}, indent=2)}")
            print(f"  + 1 条消息（1 文本 + 1 图片）")
            print()

            response = await client.post(
                f"{BASE_URL.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {API_KEY}"},
                json=payload
            )

            print(f"响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"✅ 成功！")
                print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}")
            else:
                print(f"❌ 失败！")
                try:
                    error = response.json()
                    print(f"错误详情: {json.dumps(error, ensure_ascii=False, indent=2)}")
                except:
                    print(f"错误响应: {response.text}")

    except Exception as e:
        print(f"❌ 异常: {e}")

    print()

async def main():
    # 测试两种格式
    await test_anthropic_format()
    await test_openai_format()

    print("=" * 60)
    print("测试完成")
    print("=" * 60)
    print()
    print("建议：")
    print("  - 如果 Anthropic 格式成功，保持当前配置")
    print("  - 如果 OpenAI 格式成功，修改数据库配置：")
    print("    UPDATE provider_configs SET config = json_set(config, '$.provider_type', 'openai_compatible') WHERE provider_kind = 'multimodal';")

if __name__ == "__main__":
    asyncio.run(main())
