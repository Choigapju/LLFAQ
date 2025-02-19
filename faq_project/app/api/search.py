from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database.session import get_db
from app.models.search import SearchKeyword

router = APIRouter()

@router.get("/top-keywords")
def get_top_keywords(db: Session = Depends(get_db)):
    top_keywords = (
        db.query(SearchKeyword)
        .order_by(desc(SearchKeyword.count))
        .limit(3)
        .all()
    )
    
    return {
        "keywords": [
            {
                "keyword": keyword.keyword,
                "count": keyword.count
            }
            for keyword in top_keywords
        ]
    }

# 검색어가 입력될 때 호출되는 API
@router.post("/record-keyword")
def record_search_keyword(keyword: str, db: Session = Depends(get_db)):
    # 기존 키워드가 있는지 확인
    existing_keyword = db.query(SearchKeyword).filter(SearchKeyword.keyword == keyword).first()
    
    if existing_keyword:
        # 기존 키워드가 있다면 카운트 증가
        existing_keyword.count += 1
    else:
        # 새로운 키워드라면 새로 생성
        new_keyword = SearchKeyword(keyword=keyword)
        db.add(new_keyword)
    
    db.commit()
    return {"message": "Search keyword recorded successfully"}