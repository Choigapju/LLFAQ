# app/api/main.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.database.session import get_db
from app.models.notice import Notice
from app.models.faq import FAQ
from app.schemas.faq import FAQResponse
from app.schemas.notice import Notice as NoticeSchema

router = APIRouter()

class MainPageResponse(BaseModel):
    recent_notices: List[NoticeSchema]
    popular_faqs: List[FAQResponse]
    categories: List[float]

    class Config:
        from_attributes = True

@router.get("/", response_model=MainPageResponse)
async def get_main_page(db: Session = Depends(get_db)):
    """메인 페이지 데이터 조회"""
    # 최근 공지사항 3개
    recent_notices = db.query(Notice)\
        .order_by(Notice.created_at.desc())\
        .limit(3)\
        .all()
    
    # FAQ 목록 (향후 인기순으로 변경 가능)
    popular_faqs = db.query(FAQ)\
        .limit(5)\
        .all()
    
    # FAQ 카테고리 목록
    categories = [c[0] for c in db.query(FAQ.category).distinct().all()]
    
    return {
        "recent_notices": recent_notices,
        "popular_faqs": popular_faqs,
        "categories": categories
    }

@router.get("/search", response_model=List[FAQResponse])
async def global_search(
    query: str,
    db: Session = Depends(get_db)
):
    """전체 검색 기능"""
    faqs = db.query(FAQ).filter(
        FAQ.keywords.ilike(f"%{query}%") |
        FAQ.question.ilike(f"%{query}%") |
        FAQ.answer.ilike(f"%{query}%")
    ).all()
    
    return faqs