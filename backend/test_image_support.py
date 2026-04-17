#!/usr/bin/env python3
"""测试 API 是否支持图片（使用 Anthropic 官方格式）"""

import asyncio
import base64
import httpx
import json
from pathlib import Path

# 创建一个简单的测试图片（1x1 像素的红色 PNG）
TEST_IMAGE_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="

async def test_anthropic_format(api_url: str, api_key: str):
    """测试标准 Anthropic 格式"""
    print("=" * 60)
    print("测试 Anthropic 官方格式（带图片）")
    print("=" * 60)

    # 标准 Anthropic 格式
    payload = {
        "model": "claude-opus-4-6",
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": TEST_IMAGE_BASE64
                        }
                    },
                    {
                        "type": "text",
                        "text": "这是什么颜色的图片？请简短回答。"
                    }
                ]
            }
        ]
    }

    print(f"\n📤 请求 URL: {api_url}")
    print(f"📤 请求体:\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                api_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01"
                }
            )

            print(f"📥 响应状态码: {response.status_code}")
            print(f"📥 响应头: {dict(response.headers)}\n")

            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"✅ 成功！响应:\n{json.dumps(result, ensure_ascii=False, indent=2)}")
                    return True
                except json.JSONDecodeError as e:
                    print(f"❌ 响应不是有效 JSON: {e}")
                    print(f"原始响应: {response.text[:500]}")
                    return False
            else:
                print(f"❌ 请求失败")
                try:
                    error = response.json()
                    print(f"错误详情:\n{json.dumps(error, ensure_ascii=False, indent=2)}")
                except:
                    print(f"原始错误: {response.text[:500]}")
                return False

        except Exception as e:
            print(f"❌ 异常: {e}")
            return False


async def test_text_only(api_url: str, api_key: str):
    """测试纯文本（不带图片）"""
    print("\n" + "=" * 60)
    print("测试 Anthropic 官方格式（纯文本，不带图片）")
    print("=" * 60)

    payload = {
        "model": "claude-opus-4-6",
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": "你好，请用一句话介绍你自己。"
            }
        ]
    }

    print(f"\n📤 请求 URL: {api_url}")
    print(f"📤 请求体:\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                api_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01"
                }
            )

            print(f"📥 响应状态码: {response.status_code}")

            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"✅ 成功！响应:\n{json.dumps(result, ensure_ascii=False, indent=2)}")
                    return True
                except json.JSONDecodeError as e:
                    print(f"❌ 响应不是有效 JSON: {e}")
                    print(f"原始响应: {response.text[:500]}")
                    return False
            else:
                print(f"❌ 请求失败")
                try:
                    error = response.json()
                    print(f"错误详情:\n{json.dumps(error, ensure_ascii=False, indent=2)}")
                except:
                    print(f"原始错误: {response.text[:500]}")
                return False

        except Exception as e:
            print(f"❌ 异常: {e}")
            return False


async def main():
    # 从环境变量或配置读取
    API_URL = "https://cc-vibe.com/v1/messages"
    API_KEY = "sk-xxxxxxxx"  # 你需要填入真实的 API key

    print("🔍 测试 API 图片支持情况")
    print(f"API: {API_URL}\n")

    # 先测试纯文本
    text_ok = await test_text_only(API_URL, API_KEY)

    # 再测试带图片
    image_ok = await test_anthropic_format(API_URL, API_KEY)

    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    print(f"纯文本请求: {'✅ 支持' if text_ok else '❌ 不支持'}")
    print(f"图片请求: {'✅ 支持' if image_ok else '❌ 不支持'}")

    if text_ok and not image_ok:
        print("\n⚠️  结论: 该 API 仅支持纯文本，不支持多模态（图片）")
    elif text_ok and image_ok:
        print("\n✅ 结论: 该 API 完全支持多模态")
    else:
        print("\n❌ 结论: 该 API 可能有问题")


if __name__ == "__main__":
    asyncio.run(main())
