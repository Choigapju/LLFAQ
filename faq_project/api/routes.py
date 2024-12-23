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
from collections import Counter
from datetime import datetime, timedelta
import sqlite3

# 키워드 매핑 정의
KEYWORD_MAPPINGS = {
    '출결': ['출결'],
    '공결': ['공결'],
    '병결': ['병결', '출결'],
    '결석': ['출결', '공결', '병결'],
    '지각': ['출결', '지각'],
    'QR': ['QR', '출결'],
    '훈련장려금': ['훈련장려금'],
    '장려금': ['훈련장려금'],
    '면접': ['증빙서류', '면접'],
    '단위기간': ['훈련장려금'],
    '수당': ['훈련장려금'],
    '지원금': ['훈련장려금'],
    '출석': ['출결', 'QR'],
    '퇴실': ['출결', 'QR'],
    '출석체크': ['출결', 'QR'],
    '인정': ['출결', '공결', '병결'],
    '휴가': ['공결', '출결'],
    '외출': ['출결', '외출'],
    '조퇴': ['출결', '조퇴'],
    '증명': ['증빙서류'],
    '서류': ['증빙서류'],
    '디스코드': ['디스코드'],
    '줌': ['줌', 'zoom', 'ZOOM'],
    '화상': ['줌', '디스코드'],
    '온라인': ['줌', 'zoom', 'ZOOM', '디스코드', 'LMS'],
    '수업': ['출결', 'LMS'],
    'VOD': ['LMS', 'VOD'],
    '영상': ['LMS', 'VOD'],
    '강의': ['LMS', 'VOD', '출결']
}

def normalize_keyword(keyword: str) -> str:
    """검색 키워드를 정규화합니다."""
    # 공백 제거 및 관련/건 등의 접미사 제거
    normalized = keyword.replace(' ', '')
    normalized = normalized.replace('관련', '')
    normalized = normalized.replace('신청건', '')
    return normalized

class SimpleKeywordExtractor:
    def __init__(self):
        """키워드 매핑을 초기화합니다."""
        self.keyword_mappings = KEYWORD_MAPPINGS
    
    def extract_keywords(self, text: str, available_keywords: List[str]) -> Set[str]:
        """
        주어진 텍스트에서 키워드를 추출합니다.
        텍스트를 정규화하여 처리합니다.
        """
        extracted_keywords = set()
        words = text.split()
        for word in words:
            # 각 단어를 정규화하여 검색
            normalized_word = normalize_keyword(word)
            if normalized_word in self.keyword_mappings:
                extracted_keywords.update(self.keyword_mappings[normalized_word])
        
        return set(kw for kw in extracted_keywords if any(ak in kw for ak in available_keywords))
    
# (.)온점 기준 줄바꿈
def format_text_with_linebreaks(text: str) -> str:
    """온점(.) 뒤에 줄바꿈을 추가하는 함수"""
    # HTML <br/> 태그 사용
    text = text.replace('. ', '.__BREAK__')
    text = text.replace('? ', '?__BREAK__')
    text = text.replace('! ', '!__BREAK__')

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
                title=format_text_with_linebreaks(row[1]),  # title에도 적용
                content=format_text_with_linebreaks(row[2]),  # content에도 적용
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
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        db.cursor.execute("""
            INSERT INTO notices (title, content, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (notice.title, notice.content, current_time, current_time))
        db.commit()
        
        # 마지막으로 삽입된 row의 id 가져오기
        last_id = db.cursor.lastrowid
        
        # 삽입된 데이터 조회
        db.cursor.execute("SELECT * FROM notices WHERE id = ?", (last_id,))
        result = db.cursor.fetchone()
        
        if result:
            return Notice(
                id=result[0],
                title=format_text_with_linebreaks(result[1]),
                content=format_text_with_linebreaks(result[2]),
                is_new=True,
                created_at=datetime.strptime(result[4], '%Y-%m-%d %H:%M:%S'),
                updated_at=datetime.strptime(result[5], '%Y-%m-%d %H:%M:%S')
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to create notice")
            
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
        extractor = SimpleKeywordExtractor()
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
                question=format_text_with_linebreaks(row[2]),
                answer=format_text_with_linebreaks(row[3])
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
            "model": SearchResponse
        },
        422: {
            "description": "유효하지 않은 매개변수가 전달된 경우",
            "model": HTTPValidationError
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
        # 키워드 매핑 정의
        keyword_mapping = {
            "공결신청건": "공결",
            "출결 관련": "출결"
        }
        
        # 검색 키워드 매핑
        if keyword:
            keyword = keyword_mapping.get(keyword, keyword)
        
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
                question=format_text_with_linebreaks(row[2]),
                answer=format_text_with_linebreaks(row[3])
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
    try:
        db.add_faq(faq.keywords, faq.question, faq.answer)
        results = db.get_all_faqs()
        last_faq = results[-1]
        return FAQ(
            id=last_faq[0],
            keywords=last_faq[1],
            question=format_text_with_linebreaks(last_faq[2]),
            answer=format_text_with_linebreaks(last_faq[3])
        )
    except sqlite3.Error as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))