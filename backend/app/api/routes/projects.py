from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.db import Project
from app.schemas.api import ProjectCreate, ProjectResponse
import os

router = APIRouter()

@router.post("", response_model=ProjectResponse)
async def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """创建新项目"""
    # 验证视频文件存在
    if not os.path.exists(project.source_video_path):
        raise HTTPException(status_code=400, detail="视频文件不存在")

    db_project = Project(
        name=project.name,
        source_video_path=project.source_video_path,
        language=project.language,
        status="created"
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

@router.get("", response_model=List[ProjectResponse])
async def list_projects(db: Session = Depends(get_db)):
    """获取项目列表"""
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return projects

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: Session = Depends(get_db)):
    """获取项目详情"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project

@router.delete("/{project_id}")
async def delete_project(project_id: str, db: Session = Depends(get_db)):
    """删除项目"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    db.delete(project)
    db.commit()
    return {"message": "项目已删除"}
