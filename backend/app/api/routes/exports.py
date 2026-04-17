from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.db import Project, Export
from app.schemas.api import ExportCreate, ExportResponse
from app.services.export.fcpxml.builder import FCPXMLBuilder
from typing import List

router = APIRouter()

@router.post("/{project_id}", response_model=ExportResponse)
async def create_export(
    project_id: str,
    export_req: ExportCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """创建导出"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    export = Export(
        project_id=project_id,
        format=export_req.format,
        version=export_req.version,
        status="pending"
    )
    db.add(export)
    db.commit()
    db.refresh(export)

    # 后台生成导出文件
    if export_req.format == "fcpxml":
        builder = FCPXMLBuilder(db)
        background_tasks.add_task(builder.build_and_save, project_id, export.id)

    return export

@router.get("/{project_id}", response_model=List[ExportResponse])
async def list_exports(project_id: str, db: Session = Depends(get_db)):
    """获取项目的导出列表"""
    exports = db.query(Export).filter(Export.project_id == project_id).order_by(Export.created_at.desc()).all()
    return exports

@router.get("/{export_id}/download")
async def download_export(export_id: str, db: Session = Depends(get_db)):
    """下载导出文件"""
    export = db.query(Export).filter(Export.id == export_id).first()
    if not export:
        raise HTTPException(status_code=404, detail="导出不存在")

    if export.status != "completed" or not export.file_path:
        raise HTTPException(status_code=400, detail="导出文件未就绪")

    return FileResponse(
        export.file_path,
        media_type="application/xml" if export.format == "fcpxml" else "text/plain",
        filename=f"{export.project.name}_{export.format}.{export.format}"
    )
