from fastapi import FastAPI, APIRouter, HTTPException, Query
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
import re

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
    '수업': ['출결', 'LMS', 'VOD'],
    'VOD': ['LMS', 'VOD'],
    '영상': ['LMS', 'VOD'],
    '강의': ['LMS', 'VOD', '출결'],
    '민방위': ['민방위', '공결'],
    '예비군': ['예비군', '공결'],
    '병원': ['병결', '공결', '출결'],
}

def normalize_keyword(keyword: str) -> str:
    """검색 키워드를 정규화합니다."""
    # 소문자 변환
    normalized = keyword.lower()
    
    # 특수문자 및 공백 처리
    normalized = re.sub(r'[^\w\s가-힣]', '', normalized)
    
    # 불필요한 접미사 제거
    suffixes = ['관련', '건', '합니다', '했습니다', '니다', '요', '할까요', '해요',
                '하고싶어요', '해주세요', '가능한가요', '문의']
    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]
            
    # 불필요한 조사 제거
    particles = ['은', '는', '이', '가', '을', '를', '로', '으로', '에서', '에']
    for particle in particles:
        normalized = normalized.replace(particle, '')
        
    return normalized.strip()

class SimpleKeywordExtractor:
    def __init__(self):
        """키워드 매핑을 초기화합니다."""
        self.keyword_mappings = KEYWORD_MAPPINGS
        
        # 복합 키워드는 기존 매핑에서 자동으로 생성
        self.compound_keywords = {}
        for key, values in KEYWORD_MAPPINGS.items():
            # 복합 키워드 생성 (예: '공결신청', '출석체크' 등)
            self.compound_keywords[f'{key}신청'] = values
            self.compound_keywords[f'{key}처리'] = values
            self.compound_keywords[f'{key}확인'] = values
    
    def extract_keywords(self, text: str, available_keywords: List[str]) -> Set[str]:
        try:
            print(f"Extracting keywords from: {text}")
            extracted_keywords = set()
            
            # 텍스트 정규화
            normalized_text = normalize_keyword(text)
            print(f"Normalized text: {normalized_text}")
            words = normalized_text.split()
            
            # 1. 먼저 전체 문장에서 키워드 매칭 시도
            for key in self.keyword_mappings:
                if key in normalized_text:
                    extracted_keywords.update(self.keyword_mappings[key])
            
            # 2. 개별 단어 매칭 (첫 번째 방법으로 키워드를 찾지 못한 경우)
            if not extracted_keywords:
                for word in words:
                    if word in self.keyword_mappings:
                        extracted_keywords.update(self.keyword_mappings[word])
            
            # 3. 복합 키워드 검색 (아직도 키워드를 찾지 못한 경우)
            if not extracted_keywords:
                for i in range(len(words)):
                    for j in range(i + 1, min(i + 4, len(words) + 1)):
                        compound = ''.join(words[i:j])
                        if compound in self.compound_keywords:
                            extracted_keywords.update(self.compound_keywords[compound])
                        # 복합 키워드의 부분 매칭도 시도
                        for key in self.keyword_mappings:
                            if key in compound:
                                extracted_keywords.update(self.keyword_mappings[key])
            
            print(f"Extracted keywords before filtering: {extracted_keywords}")
            
            # available_keywords와 매칭되는 것만 반환
            if extracted_keywords:
                result = set(kw for kw in extracted_keywords if kw in available_keywords)
            else:
                # 아무 키워드도 찾지 못한 경우, 문장 전체를 기준으로 available_keywords에서 찾아봄
                result = set(kw for kw in available_keywords 
                            if any(k in normalized_text for k in self.keyword_mappings.keys()))
                
            print(f"Final extracted keywords: {result}")
            return result
                
        except Exception as e:
            print(f"Error in extract_keywords: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return set()
    
# (.)온점 기준 줄바꿈
def format_text_with_linebreaks(text: str) -> str:
    """온점(.) 뒤에 줄바꿈을 추가하는 함수"""
    # 온점과 공백으로 끝나는 패턴을 찾아 줄바꿈으로 대체
    # 단, 숫자 사이의 온점은 제외 (예: 15.5)
    sentences = text.split('. ')
    formatted_text = '.\n'.join(sentences)
    return formatted_text

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
        print(f"Received query: {query}")
        
        # 사용 가능한 키워드 목록 가져오기
        db.cursor.execute("""
            SELECT DISTINCT keywords 
            FROM faq 
            WHERE keywords IS NOT NULL AND keywords != ''
            ORDER BY keywords
        """)
        available_keywords = [row[0] for row in db.cursor.fetchall()]
        print(f"Available keywords: {available_keywords}")
        
        # 키워드 추출
        extractor = SimpleKeywordExtractor()
        extracted_keywords = extractor.extract_keywords(query, available_keywords)
        print(f"Extracted keywords: {extracted_keywords}")
        
        # 검색 실행
        if extracted_keywords:
            # IN 절의 플레이스홀더 생성
            in_placeholders = ','.join(['?' for _ in extracted_keywords])
            
            # LIKE 절의 플레이스홀더 생성
            like_placeholders = ' OR '.join(['keywords LIKE ?' for _ in extracted_keywords])
            
            sql_query = f"""
                SELECT *,
                    CASE
                        WHEN keywords IN ({in_placeholders}) THEN 1
                        WHEN {like_placeholders} THEN 2
                        ELSE 3
                    END as relevance
                FROM faq
                WHERE {like_placeholders}
                ORDER BY relevance, id DESC
            """
            
            # 파라미터 준비
            # IN 절용 파라미터
            exact_params = list(extracted_keywords)
            # LIKE 절용 파라미터 (CASE문과 WHERE절에서 각각 사용)
            like_params = [f'%{k}%' for k in extracted_keywords]
            # 최종 파라미터 = IN절 + LIKE절(CASE) + LIKE절(WHERE)
            all_params = exact_params + like_params + like_params
            
            print(f"SQL Query: {sql_query}")
            print(f"Parameters: {all_params}")
            
            db.cursor.execute(sql_query, all_params)
        else:
            # 키워드가 추출되지 않은 경우 전체 텍스트로 검색
            normalized_query = normalize_keyword(query)
            exact_pattern = f'%{query}%'
            norm_pattern = f'%{normalized_query}%'
            
            db.cursor.execute("""
                SELECT *, 
                    CASE 
                        WHEN question LIKE ? OR answer LIKE ? THEN 1
                        WHEN LOWER(question) LIKE ? OR LOWER(answer) LIKE ? THEN 2
                        ELSE 3
                    END as relevance
                FROM faq 
                WHERE question LIKE ? OR answer LIKE ? OR
                      LOWER(question) LIKE ? OR LOWER(answer) LIKE ?
                ORDER BY relevance, id DESC
            """, [
                exact_pattern, exact_pattern,
                norm_pattern, norm_pattern,
                exact_pattern, exact_pattern,
                norm_pattern, norm_pattern
            ])
        
        results = db.cursor.fetchall()
        print(f"Number of results: {len(results)}")
        
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
        print(f"Error in smart_search: {str(e)}")
        import traceback
        print(traceback.format_exc())
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