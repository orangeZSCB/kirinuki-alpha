from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.db import Project, ProjectRun
from app.schemas.api import ProjectRunResponse
from app.services.pipeline.orchestrator import PipelineOrchestrator
import logging
from collections import deque
from typing import Dict

router = APIRouter()

# 内存中存储最近的日志（每个 run 最多保留 500 条）
log_buffer: Dict[str, deque] = {}

class LogBufferHandler(logging.Handler):
    """将日志写入内存缓冲区"""
    def __init__(self, run_id: str):
        super().__init__()
        self.run_id = run_id
        if run_id not in log_buffer:
            log_buffer[run_id] = deque(maxlen=500)

    def emit(self, record):
        try:
            msg = self.format(record)
            log_buffer[self.run_id].append(msg)
        except Exception:
            pass

@router.post("/{project_id}/run", response_model=ProjectRunResponse)
async def run_pipeline(
    project_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """运行完整 pipeline"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 创建 run 记录
    run = ProjectRun(
        project_id=project_id,
        status="pending",
        config_snapshot={}  # TODO: 从配置中获取
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # 为这个 run 添加日志处理器
    handler = LogBufferHandler(run.id)
    handler.setFormatter(logging.Formatter('%(message)s'))

    # 添加到所有相关的 logger
    loggers = [
        logging.getLogger("app.services.pipeline.orchestrator"),
        logging.getLogger("app.services.transcription.remote"),
        logging.getLogger("app.services.transcription.local"),
    ]

    for logger in loggers:
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

    # 后台执行 pipeline
    orchestrator = PipelineOrchestrator(db)
    background_tasks.add_task(orchestrator.run_pipeline, project_id, run.id)

    return run

@router.get("/{project_id}/runs", response_model=list[ProjectRunResponse])
async def get_project_runs(project_id: str, db: Session = Depends(get_db)):
    """获取项目的所有运行记录"""
    runs = db.query(ProjectRun).filter(ProjectRun.project_id == project_id).order_by(ProjectRun.started_at.desc()).all()
    return runs

@router.get("/runs/{run_id}", response_model=ProjectRunResponse)
async def get_run_detail(run_id: str, db: Session = Depends(get_db)):
    """获取运行详情"""
    run = db.query(ProjectRun).filter(ProjectRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="运行记录不存在")
    return run

@router.get("/{project_id}/runs/{run_id}/logs")
async def get_run_logs(project_id: str, run_id: str, db: Session = Depends(get_db)):
    """获取运行日志"""
    run = db.query(ProjectRun).filter(ProjectRun.id == run_id, ProjectRun.project_id == project_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="运行记录不存在")

    logs = list(log_buffer.get(run_id, []))
    return {"logs": logs}
