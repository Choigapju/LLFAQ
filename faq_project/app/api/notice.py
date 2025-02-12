from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database.session import get_db
from app.models.notice import Notice
from app.schemas.notice import NoticeCreate, Notice as NoticeSchema, NoticeUpdate
from app.api.auth import get_current_admin_user
from app.models.user import User

router = APIRouter()

@router.post("/", response_model=NoticeSchema)
def create_notice(
    notice: NoticeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)  # 관리자만 접근 가능
):
    """공지사항 생성 (관리자 전용)"""
    db_notice = Notice(**notice.model_dump())
    db.add(db_notice)
    db.commit()
    db.refresh(db_notice)
    return db_notice

@router.get("/", response_model=List[NoticeSchema])
def get_notices(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """공지사항 목록 조회"""
    notices = db.query(Notice)\
        .order_by(Notice.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    return notices

@router.get("/{notice_id}", response_model=NoticeSchema)
def get_notice(
    notice_id: int,
    db: Session = Depends(get_db)
):
    """공지사항 상세 조회"""
    notice = db.query(Notice).filter(Notice.id == notice_id).first()
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    return notice

@router.put("/{notice_id}", response_model=NoticeSchema)
def update_notice(
    notice_id: int,
    notice_update: NoticeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)  # 관리자만 접근 가능
):
    """공지사항 수정 (관리자 전용)"""
    db_notice = db.query(Notice).filter(Notice.id == notice_id).first()
    if not db_notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    
    for key, value in notice_update.model_dump().items():
        setattr(db_notice, key, value)
    
    db.commit()
    db.refresh(db_notice)
    return db_notice

@router.delete("/{notice_id}")
def delete_notice(
    notice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)  # 관리자만 접근 가능
):
    """공지사항 삭제 (관리자 전용)"""
    db_notice = db.query(Notice).filter(Notice.id == notice_id).first()
    if not db_notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    
    db.delete(db_notice)
    db.commit()
    return {"message": "Notice deleted successfully"}