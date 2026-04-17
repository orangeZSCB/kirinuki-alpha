from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

# Project schemas
class ProjectCreate(BaseModel):
    name: str
    source_video_path: str
    language: str = "ja"

class ProjectResponse(BaseModel):
    id: str
    name: str
    source_video_path: str
    language: str
    status: str
    duration_seconds: Optional[float] = None
    fps: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Pipeline schemas
class PipelineStepResponse(BaseModel):
    id: str
    step_name: str
    status: str
    progress: float
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

class ProjectRunResponse(BaseModel):
    id: str
    project_id: str
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None
    steps: List[PipelineStepResponse] = []

    class Config:
        from_attributes = True

# Candidate schemas
class CandidateUpdate(BaseModel):
    start_seconds: Optional[float] = None
    end_seconds: Optional[float] = None
    title: Optional[str] = None
    manual_keep: Optional[bool] = None
    manual_reject: Optional[bool] = None

class CandidateResponse(BaseModel):
    id: str
    project_id: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    heuristic_score: Optional[float] = None
    cheap_model_score: Optional[float] = None
    multimodal_score: Optional[float] = None
    final_score: Optional[float] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[List[str]] = None
    status: str
    manual_keep: Optional[bool] = None
    manual_reject: Optional[bool] = None
    keyframes: Optional[List[str]] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Export schemas
class ExportCreate(BaseModel):
    format: str = "fcpxml"
    version: Optional[str] = "1.13"

class ExportResponse(BaseModel):
    id: str
    project_id: str
    format: str
    version: Optional[str] = None
    status: str
    file_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Provider config schemas
class WhisperLocalConfig(BaseModel):
    mode: str = "local"
    model_size: str = "large-v3"
    device: str = "cuda"
    compute_type: str = "float16"
    language: str = "ja"

class WhisperRemoteConfig(BaseModel):
    mode: str = "remote"
    base_url: str
    api_key: str
    model_request_id: str = "whisper-1"
    endpoint_path: str = "/audio/transcriptions"
    response_format: str = "verbose_json"

class MultimodalConfig(BaseModel):
    provider_type: str = "openai_compatible"
    base_url: str
    api_key: str
    model: str
    timeout_seconds: int = 120
    max_frames_per_candidate: int = 8
    supports_vision: bool = True  # 是否支持多模态（图片）分析

class ProviderConfigCreate(BaseModel):
    provider_kind: str  # whisper/multimodal
    name: str
    config: dict
    is_default: bool = False

class ProviderConfigResponse(BaseModel):
    id: str
    provider_kind: str
    name: str
    config: dict
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Transcript schemas
class TranscriptSegmentResponse(BaseModel):
    id: str
    start_seconds: float
    end_seconds: float
    text: str

    class Config:
        from_attributes = True

# Analysis chunk schemas
class AnalysisChunkResponse(BaseModel):
    id: str
    chunk_index: int
    start_seconds: float
    end_seconds: float
    transcript_summary: Optional[str] = None
    heuristic_score: Optional[float] = None
    cheap_model_score: Optional[float] = None
    selected_for_mm: bool

    class Config:
        from_attributes = True

# irasutoya schemas
class IrasutoyaImage(BaseModel):
    title: str
    imageUrl: str
    description: str
    categories: List[str]
