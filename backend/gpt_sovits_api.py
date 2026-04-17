"""
GPT-SoVITS 音频处理 API
提供给 kirinuki 使用的音频处理服务

功能：
1. UVR5 人声分离（HP5_only_main_vocal）
2. 语音切分（Slicer）
3. Faster Whisper 语音识别

启动方式：
    python backend/gpt_sovits_api.py --port 9000
"""

import argparse
import os
import sys
import traceback
import uuid
from pathlib import Path
from typing import Optional

import torch
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# 添加 GPT-SoVITS 路径
GPT_SOVITS_DIR = Path(__file__).parent / "GPT-SoVITS-main"
sys.path.insert(0, str(GPT_SOVITS_DIR))
sys.path.insert(0, str(GPT_SOVITS_DIR / "tools"))

from tools.uvr5.vr import AudioPre
from tools.slicer2 import Slicer
from tools.my_utils import load_audio
from faster_whisper import WhisperModel

app = FastAPI(title="GPT-SoVITS Audio Processing API", version="1.0.0")

# 全局配置
CONFIG = {
    "device": "cuda" if torch.cuda.is_available() else "cpu",
    "is_half": True if torch.cuda.is_available() else False,
    "temp_dir": "/tmp/gpt_sovits_api",
    "uvr5_model": "HP5_only_main_vocal",
    "whisper_model": None,  # 延迟加载
}

# 确保临时目录存在
os.makedirs(CONFIG["temp_dir"], exist_ok=True)


# ── 数据模型 ──────────────────────────────────────────────────────────────────

class ProcessResponse(BaseModel):
    job_id: str
    status: str
    vocal_path: Optional[str] = None
    sliced_dir: Optional[str] = None
    transcription_path: Optional[str] = None
    transcription: Optional[list] = None
    error: Optional[str] = None


# ── UVR5 人声分离 ──────────────────────────────────────────────────────────────

def separate_vocals(audio_path: str, output_dir: str) -> str:
    """
    使用 UVR5 HP5_only_main_vocal 模型分离人声

    Args:
        audio_path: 输入音频路径
        output_dir: 输出目录

    Returns:
        分离后的人声文件路径
    """
    model_path = GPT_SOVITS_DIR / "tools/uvr5/uvr5_weights" / f"{CONFIG['uvr5_model']}.pth"

    if not model_path.exists():
        raise FileNotFoundError(f"UVR5 模型不存在: {model_path}")

    # 初始化 UVR5 模型
    pre_fun = AudioPre(
        agg=10,
        model_path=str(model_path),
        device=CONFIG["device"],
        is_half=CONFIG["is_half"],
    )

    os.makedirs(output_dir, exist_ok=True)
    vocal_dir = os.path.join(output_dir, "vocals")
    inst_dir = os.path.join(output_dir, "instruments")
    os.makedirs(vocal_dir, exist_ok=True)
    os.makedirs(inst_dir, exist_ok=True)

    try:
        # HP5 模型：is_hp3=False，vocal_root 保存主人声
        pre_fun._path_audio_(
            audio_path,
            ins_root=inst_dir,
            vocal_root=vocal_dir,
            format="wav",
            is_hp3=False
        )

        # 查找生成的人声文件
        vocal_files = list(Path(vocal_dir).glob("vocal_*.wav"))
        if not vocal_files:
            raise RuntimeError("UVR5 未生成人声文件")

        return str(vocal_files[0])

    finally:
        # 清理模型
        try:
            del pre_fun.model
            del pre_fun
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except:
            pass


# ── 语音切分 ──────────────────────────────────────────────────────────────────

def slice_audio(
    vocal_path: str,
    output_dir: str,
    threshold: int = -40,
    min_length: int = 4000,
    min_interval: int = 100,
    hop_size: int = 10,
    max_sil_kept: int = 500,
) -> str:
    """
    使用 Slicer 切分音频

    Args:
        vocal_path: 人声文件路径
        output_dir: 输出目录
        threshold: 音量阈值（dB）
        min_length: 最小片段长度（ms）
        min_interval: 最小切割间隔（ms）
        hop_size: 帧移（ms）
        max_sil_kept: 保留的最大静音长度（ms）

    Returns:
        切分后的文件夹路径
    """
    os.makedirs(output_dir, exist_ok=True)

    slicer = Slicer(
        sr=32000,
        threshold=threshold,
        min_length=min_length,
        min_interval=min_interval,
        hop_size=hop_size,
        max_sil_kept=max_sil_kept,
    )

    audio = load_audio(vocal_path, 32000)
    name = Path(vocal_path).stem

    import numpy as np
    from scipy.io import wavfile

    for chunk, start, end in slicer.slice(audio):
        tmp_max = np.abs(chunk).max()
        if tmp_max > 1:
            chunk /= tmp_max

        output_path = os.path.join(output_dir, f"{name}_{start:010d}_{end:010d}.wav")
        wavfile.write(
            output_path,
            32000,
            (chunk * 32767).astype(np.int16),
        )

    return output_dir


# ── Faster Whisper 识别 ────────────────────────────────────────────────────────

def transcribe_audio(
    sliced_dir: str,
    output_dir: str,
    language: str = "ja",
    model_size: str = "large-v3",
    precision: str = "float16",
) -> tuple[str, list]:
    """
    使用 Faster Whisper 识别音频

    Args:
        sliced_dir: 切分后的音频目录
        output_dir: 输出目录
        language: 语言代码
        model_size: 模型大小
        precision: 精度

    Returns:
        (转录文件路径, 转录结果列表)
    """
    if CONFIG["whisper_model"] is None:
        print(f"加载 Whisper 模型: {model_size}")

        # CPU 不支持 float16，自动切换到 int8
        if CONFIG["device"] == "cpu" and precision == "float16":
            precision = "int8"
            print(f"  CPU 模式，自动切换精度: {precision}")

        # 尝试使用本地模型路径
        local_model_paths = [
            f"~/.cache/huggingface/hub/models--Systran--faster-whisper-{model_size}",
            f"/home/orange/.cache/huggingface/hub/models--Systran--faster-whisper-{model_size}",
            f"models/faster-whisper-{model_size}",
        ]

        model_path = None
        for path in local_model_paths:
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path):
                # 查找 snapshots 目录
                snapshots_dir = os.path.join(expanded_path, "snapshots")
                if os.path.exists(snapshots_dir):
                    # 使用第一个 snapshot
                    snapshots = os.listdir(snapshots_dir)
                    if snapshots:
                        model_path = os.path.join(snapshots_dir, snapshots[0])
                        print(f"  找到本地模型: {model_path}")
                        break

        if model_path and os.path.exists(model_path):
            # 使用本地模型
            CONFIG["whisper_model"] = WhisperModel(
                model_path,
                device=CONFIG["device"],
                compute_type=precision,
                local_files_only=True
            )
        else:
            # 尝试下载模型
            print(f"  本地模型不存在，尝试下载...")
            try:
                CONFIG["whisper_model"] = WhisperModel(
                    model_size,
                    device=CONFIG["device"],
                    compute_type=precision
                )
            except Exception as e:
                raise Exception(
                    f"无法加载 Whisper 模型 '{model_size}'。\n"
                    f"错误: {str(e)}\n"
                    f"请确保:\n"
                    f"1. 网络可以访问 huggingface.co，或\n"
                    f"2. 本地已下载模型到 ~/.cache/huggingface/hub/\n"
                    f"3. 或使用已下载的模型大小"
                )

    model = CONFIG["whisper_model"]

    input_files = sorted(os.listdir(sliced_dir))
    results = []

    for file_name in input_files:
        if not file_name.endswith(".wav"):
            continue

        file_path = os.path.join(sliced_dir, file_name)

        try:
            segments, info = model.transcribe(
                audio=file_path,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=700),
                language=language if language != "auto" else None,
            )

            text = ""
            for segment in segments:
                text += segment.text

            results.append({
                "file": file_name,
                "language": info.language,
                "text": text.strip(),
            })

        except Exception as e:
            print(f"识别失败 {file_name}: {e}")
            results.append({
                "file": file_name,
                "error": str(e),
            })

    # 保存结果
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "transcription.txt")

    with open(output_file, "w", encoding="utf-8") as f:
        for item in results:
            if "text" in item:
                f.write(f"{item['file']}|{item['language']}|{item['text']}\n")

    return output_file, results


# ── API 路由 ──────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "service": "GPT-SoVITS Audio Processing API",
        "version": "1.0.0",
        "device": CONFIG["device"],
    }


@app.post("/process", response_model=ProcessResponse)
async def process_audio(
    file: UploadFile = File(...),
    language: str = Form("ja"),
    model_size: str = Form("large-v3"),
    skip_uvr: bool = Form(False),
    skip_slice: bool = Form(False),
):
    """
    完整的音频处理流程

    Args:
        file: 音频文件
        language: 语言代码（ja/zh/en/auto）
        model_size: Whisper 模型大小
        skip_uvr: 跳过 UVR5 人声分离
        skip_slice: 跳过语音切分
    """
    job_id = uuid.uuid4().hex[:8]
    job_dir = Path(CONFIG["temp_dir"]) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # 保存上传的文件
    suffix = Path(file.filename or "audio").suffix or ".wav"
    input_path = job_dir / f"input{suffix}"

    try:
        with open(input_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    result = ProcessResponse(job_id=job_id, status="processing")

    try:
        # Step 1: UVR5 人声分离
        if not skip_uvr:
            print(f"[{job_id}] 开始 UVR5 人声分离...")
            vocal_path = separate_vocals(str(input_path), str(job_dir / "uvr5"))
            result.vocal_path = vocal_path
            print(f"[{job_id}] UVR5 完成: {vocal_path}")
        else:
            vocal_path = str(input_path)
            result.vocal_path = vocal_path

        # Step 2: 语音切分
        if not skip_slice:
            print(f"[{job_id}] 开始语音切分...")
            sliced_dir = slice_audio(vocal_path, str(job_dir / "sliced"))
            result.sliced_dir = sliced_dir
            print(f"[{job_id}] 切分完成: {sliced_dir}")
        else:
            # 如果跳过切分，创建一个目录并复制文件
            sliced_dir = str(job_dir / "sliced")
            os.makedirs(sliced_dir, exist_ok=True)
            import shutil
            shutil.copy(vocal_path, os.path.join(sliced_dir, Path(vocal_path).name))
            result.sliced_dir = sliced_dir

        # Step 3: Faster Whisper 识别
        print(f"[{job_id}] 开始 Whisper 识别...")
        trans_path, trans_results = transcribe_audio(
            sliced_dir,
            str(job_dir / "transcription"),
            language=language,
            model_size=model_size,
        )
        result.transcription_path = trans_path
        result.transcription = trans_results
        print(f"[{job_id}] 识别完成: {trans_path}")

        result.status = "completed"
        return result

    except Exception as e:
        print(f"[{job_id}] 处理失败: {str(e)}")
        traceback.print_exc()
        result.status = "failed"
        result.error = str(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/separate")
async def separate_only(file: UploadFile = File(...)):
    """仅执行 UVR5 人声分离"""
    job_id = uuid.uuid4().hex[:8]
    job_dir = Path(CONFIG["temp_dir"]) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or "audio").suffix or ".wav"
    input_path = job_dir / f"input{suffix}"

    try:
        with open(input_path, "wb") as f:
            content = await file.read()
            f.write(content)

        vocal_path = separate_vocals(str(input_path), str(job_dir / "uvr5"))

        return JSONResponse({
            "job_id": job_id,
            "status": "completed",
            "vocal_path": vocal_path,
        })

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {
        "status": "ok",
        "device": CONFIG["device"],
        "cuda_available": torch.cuda.is_available(),
    }


# ── 入口 ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=9000, help="监听端口")
    parser.add_argument("--device", default=None, help="设备 (cuda/cpu)")
    parser.add_argument("--temp_dir", default="/tmp/gpt_sovits_api", help="临时目录")
    args = parser.parse_args()

    if args.device:
        CONFIG["device"] = args.device
        CONFIG["is_half"] = args.device == "cuda"

    if args.temp_dir:
        CONFIG["temp_dir"] = args.temp_dir
        os.makedirs(CONFIG["temp_dir"], exist_ok=True)

    print(f"✅ GPT-SoVITS API 启动于 {args.host}:{args.port}")
    print(f"   设备: {CONFIG['device']}")
    print(f"   临时目录: {CONFIG['temp_dir']}")
    print(f"   UVR5 模型: {CONFIG['uvr5_model']}")

    uvicorn.run(app, host=args.host, port=args.port)
