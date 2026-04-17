from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.db import ClipCandidate
from app.schemas.api import CandidateResponse, CandidateUpdate

router = APIRouter()

@router.get("/{project_id}", response_model=List[CandidateResponse])
async def get_candidates(project_id: str, db: Session = Depends(get_db)):
    """获取项目的候选片段"""
    candidates = db.query(ClipCandidate).filter(
        ClipCandidate.project_id == project_id
    ).order_by(ClipCandidate.final_score.desc()).all()
    return candidates

@router.patch("/{candidate_id}", response_model=CandidateResponse)
async def update_candidate(
    candidate_id: str,
    update: CandidateUpdate,
    db: Session = Depends(get_db)
):
    """更新候选片段"""
    candidate = db.query(ClipCandidate).filter(ClipCandidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="候选片段不存在")

    if update.start_seconds is not None:
        candidate.start_seconds = update.start_seconds
        candidate.duration_seconds = candidate.end_seconds - update.start_seconds
    if update.end_seconds is not None:
        candidate.end_seconds = update.end_seconds
        candidate.duration_seconds = update.end_seconds - candidate.start_seconds
    if update.title is not None:
        candidate.title = update.title
    if update.manual_keep is not None:
        candidate.manual_keep = update.manual_keep
        if update.manual_keep:
            candidate.status = "kept"
    if update.manual_reject is not None:
        candidate.manual_reject = update.manual_reject
        if update.manual_reject:
            candidate.status = "rejected"

    db.commit()
    db.refresh(candidate)
    return candidate
