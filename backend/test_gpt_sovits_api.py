#!/usr/bin/env python3
"""
GPT-SoVITS API 测试脚本
"""

import requests
import sys
from pathlib import Path

API_URL = "http://localhost:9000"


def test_health():
    """测试健康检查"""
    print("=== 测试健康检查 ===")
    resp = requests.get(f"{API_URL}/health")
    print(f"状态码: {resp.status_code}")
    print(f"响应: {resp.json()}")
    print()


def test_process(audio_file: str, language: str = "ja", skip_uvr: bool = False):
    """测试完整处理流程"""
    print(f"=== 测试完整处理流程 ===")
    print(f"音频文件: {audio_file}")
    print(f"语言: {language}")
    print(f"跳过 UVR: {skip_uvr}")

    if not Path(audio_file).exists():
        print(f"❌ 文件不存在: {audio_file}")
        return

    with open(audio_file, "rb") as f:
        files = {"file": (Path(audio_file).name, f, "audio/wav")}
        data = {
            "language": language,
            "model_size": "large-v3",
            "skip_uvr": str(skip_uvr).lower(),
            "skip_slice": "false",
        }

        print("发送请求...")
        resp = requests.post(f"{API_URL}/process", files=files, data=data)

        print(f"状态码: {resp.status_code}")

        if resp.status_code == 200:
            result = resp.json()
            print(f"✅ 处理成功!")
            print(f"Job ID: {result['job_id']}")
            print(f"状态: {result['status']}")
            print(f"人声路径: {result.get('vocal_path')}")
            print(f"切分目录: {result.get('sliced_dir')}")
            print(f"转录路径: {result.get('transcription_path')}")

            if result.get('transcription'):
                print("\n转录结果:")
                for item in result['transcription'][:5]:  # 只显示前5个
                    if 'text' in item:
                        print(f"  {item['file']}: {item['text'][:50]}...")
                if len(result['transcription']) > 5:
                    print(f"  ... 还有 {len(result['transcription']) - 5} 个结果")
        else:
            print(f"❌ 处理失败: {resp.text}")

    print()


def test_separate_only(audio_file: str):
    """测试仅人声分离"""
    print(f"=== 测试仅人声分离 ===")
    print(f"音频文件: {audio_file}")

    if not Path(audio_file).exists():
        print(f"❌ 文件不存在: {audio_file}")
        return

    with open(audio_file, "rb") as f:
        files = {"file": (Path(audio_file).name, f, "audio/wav")}

        print("发送请求...")
        resp = requests.post(f"{API_URL}/separate", files=files)

        print(f"状态码: {resp.status_code}")

        if resp.status_code == 200:
            result = resp.json()
            print(f"✅ 分离成功!")
            print(f"Job ID: {result['job_id']}")
            print(f"人声路径: {result['vocal_path']}")
        else:
            print(f"❌ 分离失败: {resp.text}")

    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python test_gpt_sovits_api.py health")
        print("  python test_gpt_sovits_api.py process <audio_file> [language] [skip_uvr]")
        print("  python test_gpt_sovits_api.py separate <audio_file>")
        print()
        print("示例:")
        print("  python test_gpt_sovits_api.py health")
        print("  python test_gpt_sovits_api.py process test.wav ja false")
        print("  python test_gpt_sovits_api.py separate test.wav")
        sys.exit(1)

    command = sys.argv[1]

    if command == "health":
        test_health()

    elif command == "process":
        if len(sys.argv) < 3:
            print("❌ 缺少音频文件参数")
            sys.exit(1)

        audio_file = sys.argv[2]
        language = sys.argv[3] if len(sys.argv) > 3 else "ja"
        skip_uvr = sys.argv[4].lower() == "true" if len(sys.argv) > 4 else False

        test_process(audio_file, language, skip_uvr)

    elif command == "separate":
        if len(sys.argv) < 3:
            print("❌ 缺少音频文件参数")
            sys.exit(1)

        audio_file = sys.argv[2]
        test_separate_only(audio_file)

    else:
        print(f"❌ 未知命令: {command}")
        sys.exit(1)
