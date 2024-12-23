from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any, Set
from pydantic import BaseModel
from database.db_manager import DatabaseManager
from .models import (
    FAQ, 
    FAQCreate, 
    SearchResponse, 
    PopularKeywordsResponse, 
    KeywordCount,
    TopKeywordsResponse,
    Notice,
    NoticeCreate
)
from konlpy.tag import Okt
from collections import Counter
from datetime import datetime, timedelta

class SmartKeywordExtractor:
    def __init__(self):
        self.okt = Okt()
        # FAQ 키워드 사전
        self.keyword_mappings = {
            '병원': ['병결', '공결'],
            '공결': ['공결', '출결'],
            '병결': ['병결', '출결'],
            '결석': ['출결', '공결', '병결'],
            '지각': ['출결', '지각'],
            'QR': ['QR', '출결'],
            '훈련': ['훈련장려금'],
            '장려금': ['훈련장려금'],
            '면접': ['증빙서류, 면접'],
            '단위': ['훈련장려금'],
            '기간': ['훈련장려금', '출결'],
            '신청': ['공결', '훈련장려금'],
            '수당': ['훈련장려금'],
            '지원금': ['훈련장려금'],
            '출석': ['출결', 'QR'],
            '체크': ['출결', 'QR'],
            '인정': ['출결', '공결'],
            '휴가': ['공결', '출결'],
            '외출': ['출결'],
            '조퇴': ['출결'],
            '증명': ['증빙서류'],
            '서류': ['증빙서류'],
            '디스코드': ['디스코드'],
            '줌': ['줌', 'zoom', 'ZOOM'],
            '화상': ['줌', '디스코드'],
            '온라인': ['줌', '디스코드', 'LMS'],
            '수업': ['출결', 'LMS'],
            'VOD': ['LMS, VOD'],
            '영상': ['LMS, VOD'],
            '강의': ['LMS, VOD', '출결'],
        }
    
    def extract_keywords(self, text: str, available_keywords: List[str]) -> Set[str]:
        morphs = self.okt.nouns(text)
        extracted_keywords = set()
        for morph in morphs:
            if morph in self.keyword_mappings:
                extracted_keywords.update(self.keyword_mappings[morph])
        return set(kw for kw in extracted_keywords if any(ak in kw for ak in available_keywords))
    

# 422 에러 응답 스키마 정의
class ValidationError(BaseModel):
    loc: List[str]
    msg: str
    type: str

class HTTPValidationError(BaseModel):
    detail: List[ValidationError]

router = APIRouter()
db = DatabaseManager()

@router.get(
    "/faqs/top-keywords/",
    response_model=TopKeywordsResponse,
    tags=["faqs"]
)
async def get_top_keywords():
    """가장 많이 사용된 키워드 3개를 반환합니다."""
    try:
        db.cursor.execute("""
            SELECT keywords
            FROM faq
            WHERE keywords IS NOT NULL AND keywords != ''
            GROUP BY keywords
            ORDER BY COUNT (*) DESC
            LIMIT 3
        """)
        top_keywords = [row[0] for row in db.cursor.fetchall()]
        
        return TopKeywordsResponse(
            top_keywords=top_keywords
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/notices/", response_model=List[Notice])
async def get_notices(
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None
):
    """공지사항 목록을 조회합니다."""
    try:
        query = "SELECT * FROM notices"
        params = []
        
        if search:
            query += " WHERE title LIKE ? OR content LIKE ?"
            params.extend([f'%{search}%', f'%{search}%'])
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])
        
        db.cursor.execute(query, params)
        results = db.cursor.fetchall()
        
        # 2주 이내 게시물 NEW 표시
        two_weeks_ago = datetime.now() - timedelta(weeks=2)
        
        notices = []
        for row in results:
            created_at = datetime.strptime(row[4], '%Y-%m-%d %H:%M:%S')
            updated_at = datetime.strptime(row[5], '%Y-%m-%d %H:%M:%S')
            
            notice = Notice(
                id=row[0],
                title=row[1],
                content=row[2],
                is_new=(created_at > two_weeks_ago),
                created_at=created_at,
                updated_at=updated_at
            )
            notices.append(notice)
            
        return notices
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notices/", response_model=Notice)
async def create_notice(notice: NoticeCreate):
    try:
        db.cursor.execute("""
            INSERT INTO notices (title, content)
            VALUES (?, ?)
            RETURNING *
        """, (notice.title, notice.content))
        db.commit()
        result = db.cursor.fetchone()
        
        return Notice(
            id=result[0],
            title=result[1],
            content=result[2],
            is_new=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/faqs/smart-search/",
    response_model=SearchResponse,
    tags=["faqs"]
)
async def smart_search(
    query: str = Query(..., description="검색할 자연어 문장", example="병원 방문으로 공결 신청합니다")
):
    try:
        # 사용 가능한 키워드 목록 가져오기
        db.cursor.execute("""
            SELECT DISTINCT keywords 
            FROM faq 
            WHERE keywords IS NOT NULL AND keywords != ''
            ORDER BY keywords
        """)
        available_keywords = [row[0] for row in db.cursor.fetchall()]
        
        # 키워드 추출
        extractor = SmartKeywordExtractor()
        extracted_keywords = extractor.extract_keywords(query, available_keywords)
        
        # 검색 쿼리 구성
        if extracted_keywords:
            placeholders = ' OR '.join(['keywords LIKE ?' for _ in extracted_keywords])
            search_terms = [f'%{keyword}%' for keyword in extracted_keywords]
            
            sql_query = f"""
                SELECT * FROM faq 
                WHERE {placeholders}
                ORDER BY id DESC
            """
            db.cursor.execute(sql_query, search_terms)
        else:
            # 키워드가 추출되지 않은 경우 전체 텍스트로 검색
            db.cursor.execute("""
                SELECT * FROM faq 
                WHERE question LIKE ? OR answer LIKE ?
                ORDER BY id DESC
            """, (f'%{query}%', f'%{query}%'))
        
        results = db.cursor.fetchall()
        faqs = [
            FAQ(
                id=row[0],
                keywords=row[1],
                question=row[2],
                answer=row[3]
            ) for row in results
        ]
        
        return SearchResponse(
            total=len(faqs),
            available_keywords=available_keywords,
            results=faqs
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get(
    "/faqs/search/",
    response_model=SearchResponse,
    responses={
        200: {
            "description": "성공적으로 FAQ를 검색한 경우",
            "model": SearchResponse,
            "content": {
                "application/json": {
                    "example": {
                        "total": 2,
                        "available_keywords": ["출결", "훈련장려금"],
                        "results": [
                            {
                                "id": 1,
                                "keywords": "출결",
                                "question": "출결 관련 질문",
                                "answer": "출결 관련 답변"
                            }
                        ]
                    }
                }
            }
        },
        422: {
            "description": "유효하지 않은 매개변수가 전달된 경우",
            "model": HTTPValidationError,
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["query"],
                                "msg": "유효하지 않은 검색어 형식",
                                "type": "value_error"
                            }
                        ]
                    }
                }
            }
        }
    },
    tags=["faqs"]
)
async def search_faqs(
    query: Optional[str] = Query(None, description="검색할 키워드", example="출결"),
    keyword: Optional[str] = Query(None, description="필터링할 카테고리", example="출결")
):
    """
    FAQ를 검색합니다.
    - query: 질문/답변 내용에서 검색할 키워드
    - keyword: 특정 카테고리로 필터링할 키워드
    """
    try:
        # 기존 코드 유지
        # 키워드 목록 조회
        db.cursor.execute("""
            SELECT DISTINCT keywords 
            FROM faq 
            WHERE keywords IS NOT NULL AND keywords != ''
            ORDER BY keywords
        """)
        available_keywords = [row[0] for row in db.cursor.fetchall()]

        # 검색 쿼리 구성
        if query and keyword:
            db.cursor.execute("""
                SELECT * FROM faq 
                WHERE (question LIKE ? OR answer LIKE ?) 
                AND keywords = ?
                ORDER BY id DESC
            """, (f'%{query}%', f'%{query}%', keyword))
        elif query:
            db.cursor.execute("""
                SELECT * FROM faq 
                WHERE question LIKE ? OR answer LIKE ?
                ORDER BY id DESC
            """, (f'%{query}%', f'%{query}%'))
        elif keyword:
            db.cursor.execute("""
                SELECT * FROM faq 
                WHERE keywords = ?
                ORDER BY id DESC
            """, (keyword,))
        else:
            db.cursor.execute("SELECT * FROM faq ORDER BY id DESC")

        results = db.cursor.fetchall()
        
        faqs = [
            FAQ(
                id=row[0],
                keywords=row[1],
                question=row[2],
                answer=row[3]
            ) for row in results
        ]

        return SearchResponse(
            total=len(faqs),
            available_keywords=available_keywords,
            results=faqs
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/faqs/popular-keywords/",
    response_model=PopularKeywordsResponse,
    responses={
        200: {
            "description": "인기 키워드 목록 조회 성공",
            "model": PopularKeywordsResponse,
            "content": {
                "application/json": {
                    "example": {
                        "popular_keywords": [
                            {"keyword": "출결", "count": 15},
                            {"keyword": "훈련장려금", "count": 10}
                        ]
                    }
                }
            }
        }
    },
    tags=["faqs"]
)
async def get_popular_keywords():
    """자주 사용되는 키워드 목록을 조회합니다."""
    try:
        db.cursor.execute("""
            SELECT keywords, COUNT(*) as count
            FROM faq
            WHERE keywords IS NOT NULL AND keywords != ''
            GROUP BY keywords
            ORDER BY count DESC
            LIMIT 5
        """)
        results = db.cursor.fetchall()
        
        return PopularKeywordsResponse(
            popular_keywords=[
                KeywordCount(keyword=row[0], count=row[1])
                for row in results
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/faqs/",
    response_model=FAQ,
    responses={
        200: {
            "description": "FAQ 생성 성공",
            "model": FAQ
        },
        422: {
            "description": "유효하지 않은 입력 데이터",
            "model": HTTPValidationError
        }
    },
    tags=["faqs"]
)
async def create_faq(faq: FAQCreate):
    """새로운 FAQ를 생성합니다."""
    try:
        db.add_faq(faq.keywords, faq.question, faq.answer)
        results = db.get_all_faqs()
        last_faq = results[-1]
        return FAQ(
            id=last_faq[0],
            keywords=last_faq[1],
            question=last_faq[2],
            answer=last_faq[3]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))