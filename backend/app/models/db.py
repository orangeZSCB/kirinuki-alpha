from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    source_video_path = Column(String, nullable=False)
    language = Column(String, default="ja")
    status = Column(String, nullable=False, default="created")  # created/processing/completed/failed
    duration_seconds = Column(Float)
    fps = Column(Float)
    width = Column(Integer)
    height = Column(Integer)
    audio_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    runs = relationship("ProjectRun", back_populates="project", cascade="all, delete-orphan")
    transcript_segments = relationship("TranscriptSegment", back_populates="project", cascade="all, delete-orphan")
    analysis_chunks = relationship("AnalysisChunk", back_populates="project", cascade="all, delete-orphan")
    candidates = relationship("ClipCandidate", back_populates="project", cascade="all, delete-orphan")
    exports = relationship("Export", back_populates="project", cascade="all, delete-orphan")

class ProjectRun(Base):
    __tablename__ = "project_runs"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    status = Column(String, nullable=False, default="pending")  # pending/running/completed/failed
    config_snapshot = Column(JSON, nullable=False)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    error_message = Column(Text)

    project = relationship("Project", back_populates="runs")
    steps = relationship("PipelineStep", back_populates="run", cascade="all, delete-orphan")

class PipelineStep(Base):
    __tablename__ = "pipeline_steps"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("project_runs.id"), nullable=False)
    step_name = Column(String, nullable=False)  # ingest/transcribe/extract_features/chunk/cheap_screen/multimodal_review/export
    status = Column(String, nullable=False, default="pending")
    progress = Column(Float, default=0.0)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    error_message = Column(Text)
    output_data = Column(JSON)

    run = relationship("ProjectRun", back_populates="steps")

class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    start_seconds = Column(Float, nullable=False)
    end_seconds = Column(Float, nullable=False)
    text = Column(Text, nullable=False)

    project = relationship("Project", back_populates="transcript_segments")

class AnalysisChunk(Base):
    __tablename__ = "analysis_chunks"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    start_seconds = Column(Float, nullable=False)
    end_seconds = Column(Float, nullable=False)
    transcript_summary = Column(Text)
    heuristic_score = Column(Float)
    cheap_model_score = Column(Float)
    selected_for_mm = Column(Boolean, default=False)
    feature_data = Column(JSON)

    project = relationship("Project", back_populates="analysis_chunks")

class ClipCandidate(Base):
    __tablename__ = "clip_candidates"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    start_seconds = Column(Float, nullable=False)
    end_seconds = Column(Float, nullable=False)
    duration_seconds = Column(Float, nullable=False)
    heuristic_score = Column(Float)
    cheap_model_score = Column(Float)
    multimodal_score = Column(Float)
    final_score = Column(Float)
    title = Column(String)
    summary = Column(Text)
    tags = Column(JSON)
    status = Column(String, nullable=False, default="proposed")  # proposed/kept/rejected
    manual_keep = Column(Boolean)
    manual_reject = Column(Boolean)
    keyframes = Column(JSON)  # 存储关键帧路径列表
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="candidates")

class Export(Base):
    __tablename__ = "exports"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    format = Column(String, nullable=False)  # fcpxml/edl/otio
    version = Column(String)
    status = Column(String, nullable=False, default="pending")
    file_path = Column(String)
    export_metadata = Column(JSON)  # 改名避免与 SQLAlchemy 的 metadata 冲突
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="exports")

class ProviderConfig(Base):
    __tablename__ = "provider_configs"

    id = Column(String, primary_key=True, default=generate_uuid)
    provider_kind = Column(String, nullable=False)  # whisper/multimodal
    name = Column(String, nullable=False)
    config = Column(JSON, nullable=False)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
