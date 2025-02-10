# api/routes.py

from fastapi import FastAPI, APIRouter, HTTPException, Query, Depends
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
    NoticeCreate,
    Comment,
    CommentCreate,
)
from collections import Counter
from datetime import datetime, timedelta
import psycopg2
from psycopg2.errors import Error as PostgresError
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

def get_db():
    db = DatabaseManager()
    try:
        yield db
    finally:
        db.close()

def escape_like_pattern(value: str) -> str:
    """ILIKE 패턴에서 사용할 문자열을 이스케이프 처리합니다."""
    return value.replace('%', '\\%').replace('_', '\\_')

def normalize_keyword(keyword: str) -> str:
    """검색 키워드를 정규화합니다."""
    normalized = keyword.lower()
    normalized = re.sub(r'[^\w\s가-힣]', '', normalized)
    
    suffixes = ['관련', '건', '합니다', '했습니다', '니다', '요', '할까요', '해요',
                '하고싶어요', '해주세요', '가능한가요', '문의']
    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]
            
    particles = ['은', '는', '이', '가', '을', '를', '로', '으로', '에서', '에']
    for particle in particles:
        normalized = normalized.replace(particle, '')
        
    return normalized.strip()

class SimpleKeywordExtractor:
    def __init__(self):
        self.keyword_mappings = KEYWORD_MAPPINGS
        self.compound_keywords = {}
        for key, values in KEYWORD_MAPPINGS.items():
            self.compound_keywords[f'{key}신청'] = values
            self.compound_keywords[f'{key}처리'] = values
            self.compound_keywords[f'{key}확인'] = values
    
    def extract_keywords(self, text: str, available_keywords: List[str]) -> Set[str]:
        try:
            print(f"Extracting keywords from: {text}")
            extracted_keywords = set()
            
            normalized_text = normalize_keyword(text)
            print(f"Normalized text: {normalized_text}")
            words = normalized_text.split()
            
            for key in self.keyword_mappings:
                if key in normalized_text:
                    extracted_keywords.update(self.keyword_mappings[key])
            
            if not extracted_keywords:
                for word in words:
                    if word in self.keyword_mappings:
                        extracted_keywords.update(self.keyword_mappings[word])
            
            if not extracted_keywords:
                for i in range(len(words)):
                    for j in range(i + 1, min(i + 4, len(words) + 1)):
                        compound = ''.join(words[i:j])
                        if compound in self.compound_keywords:
                            extracted_keywords.update(self.compound_keywords[compound])
                        for key in self.keyword_mappings:
                            if key in compound:
                                extracted_keywords.update(self.keyword_mappings[key])
            
            if extracted_keywords:
                result = set(kw for kw in extracted_keywords if kw in available_keywords)
            else:
                result = set(kw for kw in available_keywords 
                            if any(k in normalized_text for k in self.keyword_mappings.keys()))
                
            return result
                
        except Exception as e:
            print(f"Error in extract_keywords: {str(e)}")
            return set()

def format_text_with_linebreaks(text: str) -> str:
    """온점(.) 뒤에 줄바꿈을 추가하는 함수"""
    sentences = text.split('. ')
    formatted_text = '.\n'.join(sentences)
    return formatted_text

class ValidationError(BaseModel):
    loc: List[str]
    msg: str
    type: str

class HTTPValidationError(BaseModel):
    detail: List[ValidationError]

router = APIRouter()

@router.get("/faqs/top-keywords/", response_model=TopKeywordsResponse)
async def get_top_keywords(db: DatabaseManager = Depends(get_db)):
    """가장 많이 사용된 키워드 3개를 반환합니다."""
    try:
        db.cursor.execute("""
            SELECT keywords
            FROM faq
            WHERE keywords IS NOT NULL AND keywords != ''
            GROUP BY keywords
            ORDER BY COUNT(*) DESC
            LIMIT 3
        """)
        top_keywords = [row[0] for row in db.cursor.fetchall()]
        
        return TopKeywordsResponse(
            top_keywords=top_keywords
        )
    except PostgresError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/notices/", response_model=List[Notice])
async def get_notices(
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None,
    db: DatabaseManager = Depends(get_db)
):
    """공지사항 목록을 조회합니다."""
    try:
        query = "SELECT * FROM notices"
        params = []
        
        if search:
            escaped_search = escape_like_pattern(search)
            query += " WHERE title ILIKE %s OR content ILIKE %s"
            params.extend([f'%{escaped_search}%', f'%{escaped_search}%'])
        
        query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, skip])
        
        db.cursor.execute(query, params)
        results = db.cursor.fetchall()
        
        two_weeks_ago = datetime.now() - timedelta(weeks=2)
        
        notices = [
            Notice(
                id=row[0],
                title=row[1],
                content=row[2],
                is_new=(row[4] > two_weeks_ago),
                created_at=row[4],
                updated_at=row[5]
            )
            for row in results
        ]
        
        return notices
        
    except PostgresError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notices/", response_model=Notice)
async def create_notice(
    notice: NoticeCreate,
    db: DatabaseManager = Depends(get_db)
):
    try:
        db.cursor.execute("""
            INSERT INTO notices (title, content)
            VALUES (%s, %s)
            RETURNING id, title, content, is_new, created_at, updated_at
        """, (notice.title, notice.content))
        db.commit()
        result = db.cursor.fetchone()
        
        return Notice(
            id=result[0],
            title=result[1],
            content=result[2],
            is_new=True,
            created_at=result[4],
            updated_at=result[5],
        )
    except PostgresError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/faqs/smart-search/", response_model=SearchResponse)
async def smart_search(
    query: str = Query(..., description="검색할 자연어 문장", example="병원 방문으로 공결 신청합니다"),
    db: DatabaseManager = Depends(get_db)
):
    try:
        print(f"Received query: {query}")
        
        # PostgreSQL에서 키워드 가져오기
        db.cursor.execute("""
            SELECT DISTINCT keywords 
            FROM faq 
            WHERE keywords IS NOT NULL AND keywords != ''
            ORDER BY keywords
        """)
        results = db.cursor.fetchall()
        # RealDictCursor는 딕셔너리를 반환하므로 'keywords' 키를 사용
        available_keywords = [row['keywords'] for row in results]
        print(f"Available keywords: {available_keywords}")
        
        extractor = SimpleKeywordExtractor()
        extracted_keywords = extractor.extract_keywords(query, available_keywords)
        print(f"Extracted keywords: {extracted_keywords}")
        
        if extracted_keywords:
            like_conditions = ' OR '.join(['keywords ILIKE %s' for _ in extracted_keywords])
            
            sql_query = f"""
                WITH ranked_results AS (
                    SELECT *,
                        CASE
                            WHEN keywords = ANY(%s) THEN 1
                            WHEN {like_conditions} THEN 2
                            ELSE 3
                        END as relevance
                    FROM faq
                    WHERE {like_conditions}
                )
                SELECT * FROM ranked_results
                ORDER BY relevance, id DESC
            """
            
            exact_params = [list(extracted_keywords)]
            like_params = [f'%{k}%' for k in extracted_keywords]
            all_params = exact_params + like_params + like_params
            
            print(f"Query parameters: {all_params}")
            db.cursor.execute(sql_query, all_params)
        else:
            normalized_query = normalize_keyword(query)
            escaped_query = escape_like_pattern(query)
            escaped_norm_query = escape_like_pattern(normalized_query)
            
            db.cursor.execute("""
                WITH ranked_results AS (
                    SELECT *, 
                        CASE 
                            WHEN question ILIKE %s OR answer ILIKE %s THEN 1
                            WHEN LOWER(question) ILIKE %s OR LOWER(answer) ILIKE %s THEN 2
                            ELSE 3
                        END as relevance
                    FROM faq 
                    WHERE question ILIKE %s OR answer ILIKE %s OR
                          LOWER(question) ILIKE %s OR LOWER(answer) ILIKE %s
                )
                SELECT * FROM ranked_results
                ORDER BY relevance, id DESC
            """, [
                f'%{escaped_query}%', f'%{escaped_query}%',
                f'%{escaped_norm_query}%', f'%{escaped_norm_query}%',
                f'%{escaped_query}%', f'%{escaped_query}%',
                f'%{escaped_norm_query}%', f'%{escaped_norm_query}%'
            ])
        
        results = db.cursor.fetchall()
        print(f"Number of results: {len(results)}")
        
        faqs = [
            FAQ(
                id=row['id'],
                keywords=row['keywords'],
                question=format_text_with_linebreaks(row['question']),
                answer=format_text_with_linebreaks(row['answer'])
            ) for row in results
        ]
        
        return SearchResponse(
            total=len(faqs),
            available_keywords=available_keywords,
            results=faqs
        )
        
    except PostgresError as e:
        print(f"Error in smart_search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/faqs/search/", response_model=SearchResponse)
async def search_faqs(
    query: Optional[str] = Query(None, description="검색할 키워드", example="출결"),
    keyword: Optional[str] = Query(None, description="필터링할 카테고리", example="출결"),
    db: DatabaseManager = Depends(get_db)
):
    try:
        keyword_mapping = {
            "공결신청건": "공결",
            "출결 관련": "출결"
        }
        
        if keyword:
            keyword = keyword_mapping.get(keyword, keyword)
        
        db.cursor.execute("""
            SELECT DISTINCT keywords 
            FROM faq 
            WHERE keywords IS NOT NULL AND keywords != ''
            ORDER BY keywords
        """)
        available_keywords = [row[0] for row in db.cursor.fetchall()]

        if query and keyword:
            escaped_query = escape_like_pattern(query)
            db.cursor.execute("""
                SELECT * FROM faq 
                WHERE (question ILIKE %s OR answer ILIKE %s) 
                AND keywords = %s
                ORDER BY id DESC
            """, (f'%{escaped_query}%', f'%{escaped_query}%', keyword))
        elif query:
            escaped_query = escape_like_pattern(query)
            db.cursor.execute("""
                SELECT * FROM faq 
                WHERE question ILIKE %s OR answer ILIKE %s
                ORDER BY id DESC
            """, (f'%{escaped_query}%', f'%{escaped_query}%'))
        elif keyword:
            db.cursor.execute("""
                SELECT * FROM faq 
                WHERE keywords = %s
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

    except PostgresError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/faqs/popular-keywords/", response_model=PopularKeywordsResponse)
async def get_popular_keywords(db: DatabaseManager = Depends(get_db)):
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
    except PostgresError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/faqs/", response_model=FAQ)
async def create_faq(faq: FAQCreate, db: DatabaseManager = Depends(get_db)):
    try:
        db.cursor.execute("""
            INSERT INTO faq (keywords, question, answer)
            VALUES (%s, %s, %s)
            RETURNING id, keywords, question, answer
        """, (faq.keywords, faq.question, faq.answer))
        db.commit()
        result = db.cursor.fetchone()
        
        return FAQ(
            id=result[0],
            keywords=result[1],
            question=format_text_with_linebreaks(result[2]),
            answer=format_text_with_linebreaks(result[3])
        )
    except PostgresError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/faqs/{faq_id}/comments/", response_model=Comment)
async def create_comment(
    faq_id: int,
    comment: CommentCreate,
    db: DatabaseManager = Depends(get_db)
):
    """FAQ에 익명 댓글을 추가합니다."""
    try:
        db.cursor.execute("SELECT id FROM faq WHERE id = %s", (faq_id,))
        if not db.cursor.fetchone():
            raise HTTPException(status_code=404, detail="FAQ not found")
            
        db.cursor.execute("""
            INSERT INTO comments (faq_id, content, created_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            RETURNING id, faq_id, content, created_at
        """, (faq_id, comment.content))
        db.commit()
        
        result = db.cursor.fetchone()
        return Comment(
            id=result[0],
            faq_id=result[1],
            content=result[2],
            created_at=result[3]
        )
    except PostgresError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/faqs/{faq_id}/comments/", response_model=List[Comment])
async def get_comments(
    faq_id: int,
    db: DatabaseManager = Depends(get_db)
):
    """특정 FAQ의 모든 댓글을 조회합니다."""
    try:
        db.cursor.execute("""
            SELECT id, faq_id, content, created_at 
            FROM comments 
            WHERE faq_id = %s
            ORDER BY created_at DESC
        """, (faq_id,))
        
        comments = [
            Comment(
                id=row[0],
                faq_id=row[1],
                content=row[2],
                created_at=row[3]
            )
            for row in db.cursor.fetchall()
        ]
        return comments
    except PostgresError as e:
        raise HTTPException(status_code=500, detail=str(e))