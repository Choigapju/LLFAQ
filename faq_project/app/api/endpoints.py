from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
import csv
import re
from app.database.session import get_db
from app.models.faq import FAQ
from app.schemas.faq import FAQCreate, FAQResponse
# from app.api.auth import get_current_admin_user, get_current_user
# from app.models.user import User

router = APIRouter()

@router.post("/load-csv")
def load_csv_data(db: Session = Depends(get_db)):
    """CSV 파일에서 데이터를 로드하여 데이터베이스에 저장합니다."""
    try:
        with open('faq_data.csv', 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                try:
                    category = float(row['category']) if row['category'].strip() else 0.0
                    db_faq = FAQ(
                        category=category,
                        keywords=row['keywords'],
                        question=row['question'],
                        answer=row['answer']
                    )
                    db.add(db_faq)
                except ValueError as e:
                    print(f"Error processing row: {row}, Error: {str(e)}")
                    continue
            db.commit()
        return {"message": "CSV 데이터가 성공적으로 로드되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[FAQResponse])
def get_all_faqs(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """모든 FAQ를 조회합니다."""
    faqs = db.query(FAQ).offset(skip).limit(limit).all()
    return faqs

@router.get("/category/{category}", response_model=List[FAQResponse])
def get_faqs_by_category(
    category: float, 
    db: Session = Depends(get_db)
):
    """카테고리별 FAQ를 조회합니다."""
    faqs = db.query(FAQ).filter(FAQ.category == category).all()
    return faqs

KEYWORD_MAPPINGS = {
    # 출결 관련
    '출결': ['출석', '출석체크', '퇴실', 'QR', '출결', '출결신청', '출결 신청'],
    '지각': ['늦음', '지각', '지각신청', '지각 신청'],
    '조퇴': ['일찍가기', '조퇴', '조퇴신청', '조퇴 신청'],
    '외출': ['나갔다', '나감', '외출', '외출신청', '외출 신청'],
    '결석': ['빠짐', '못감', '결석', '결석신청', '결석 신청'],
    
    # 공결/병결 관련
    '공결': ['공가', '공식결석', '예비군', '민방위', '공결신청', '공결 신청', '공결'],
    '병결': ['병가', '병원', '진료', '치료', '병결', '병결신청', '병결 신청'],
    
    # 수업/학습 관련
    '수업': ['강의', '교육', '학습', '수업', '수업신청', '수업 신청'],
    'VOD': ['영상', '녹화', '온라인강의', 'VOD', 'VOD신청', 'VOD 신청'],
    'LMS': ['학습관리', '이러닝', 'LMS', 'LMS신청', 'LMS 신청'],
    
    # 화상 도구 관련
    '줌': ['zoom', 'ZOOM', '화상', '줌', '줌신청', '줌 신청'],
    '디스코드': ['단체채팅', '채팅방', '디스코드', '디스코드신청', '디스코드 신청'],
    
    # 지원금 관련
    '훈련장려금': ['장려금', '지원금', '수당', '단위기간', '훈련장려금', '훈련장려금신청', '훈련장려금 신청'],
    
    # 서류 관련
    '증빙서류': ['증명서', '확인서', '서류', '면접확인서', '증빙서류', '증빙서류신청', '증빙서류 신청'],
}

# 역방향 매핑 생성
REVERSE_KEYWORD_MAPPINGS = {}
for main_keyword, related_keywords in KEYWORD_MAPPINGS.items():
    for keyword in related_keywords:
        if keyword not in REVERSE_KEYWORD_MAPPINGS:
            REVERSE_KEYWORD_MAPPINGS[keyword] = set()
        REVERSE_KEYWORD_MAPPINGS[keyword].add(main_keyword)
        
stop_words = {
    "있다", "없다", "하다", "이다", "되다", "어떻다", 
    "무엇", "무슨", "어떤", "이런", "저런", "그런",
    "은", "는", "이", "가", "을", "를", "의", "로", "으로",
    "에서", "부터", "까지", "에게", "한테",
    "어떻게", "어디서", "언제", "누가", "왜",
    "합니다", "입니다", "습니다", "니다",
    "하나요", "인가요", "될까요", "할까요",
    "어케", "해야", "다녀왔는데",
    "요합니다", "방법을" 
}

def extract_keywords(query: str) -> List[str]:
    # 특수문자 제거 및 소문자 변환
    query = re.sub(r'[^\w\s]', ' ', query)
    
    # 단어 분리 전 불필요한 조사/어미 제거
    query = re.sub(r'(을|를|이|가|의|에|로|으로|합니다|습니다|니다)$', '', query)
    
    # 단어 분리
    words = [word.strip() for word in query.split() if word.strip()]
    
    # 결과 키워드 리스트
    keywords = set()
    
    for word in words:
        # 불용어 제거
        if word in stop_words:
            continue
            
        # 짧은 단어 제거 (1글자)
        if len(word) < 2:
            continue
            
        # 키워드 매핑 확인
        mapped = False
        for main_keyword, variations in KEYWORD_MAPPINGS.items():
            if word in variations or word == main_keyword:
                keywords.add(main_keyword)
                mapped = True
                break
                
        # 매핑되지 않은 단어도 추가
        if not mapped:
            keywords.add(word)
    
    return list(keywords)

@router.get("/search", response_model=List[FAQResponse])
def search_faqs(
    query: str, 
    db: Session = Depends(get_db),
    threshold: float = 0.3
):
    # 디버깅을 위한 데이터베이스 확인 로그 추가
    total_faqs = db.query(FAQ).count()
    print(f"Total FAQs in database: {total_faqs}")
    
    """문장으로 FAQ를 검색합니다."""
    print(f"Received query: {query}")  
    
    # 검색어에서 키워드 추출
    keywords = extract_keywords(query)
    print(f"Extracted keywords: {keywords}")  
    
    if not keywords:
        print("No keywords extracted")
        return []
    
    # 검색 조건 생성
    conditions = []
    for keyword in keywords:
        # 정확한 매칭
        conditions.extend([
            FAQ.keywords.ilike(f"%{keyword}%"),
            FAQ.question.ilike(f"%{keyword}%"),
            FAQ.answer.ilike(f"%{keyword}%")
        ])
        
        # 부분 매칭 (키워드가 2글자 이상인 경우)
        if len(keyword) >= 2:
            conditions.extend([
                FAQ.keywords.ilike(f"%{keyword[:-1]}%"),
                FAQ.question.ilike(f"%{keyword[:-1]}%"),
                FAQ.answer.ilike(f"%{keyword[:-1]}%")
            ])
    print(f"Search conditions: {conditions}")  
    
    # 검색 실행
    faqs = db.query(FAQ).filter(or_(*conditions)).all()
    print(f"Initial search results: {len(faqs)}")  
    
    # 관련성 점수 계산 및 정렬
    scored_faqs = []
    for faq in faqs:
        score = 0
        faq_text = f"{faq.keywords} {faq.question} {faq.answer}".lower()
        
        # 키워드 매칭 점수
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in faq_text:
                # 키워드가 keywords 필드에 있으면 가중치 부여
                if keyword_lower in faq.keywords.lower():
                    score += 2
                # question에 있으면 높은 가중치
                elif keyword_lower in faq.question.lower():
                    score += 1.5
                # answer에 있으면 기본 가중치
                else:
                    score += 1
        
        # 전체 키워드 수로 정규화
        score = score / len(keywords)
        print(f"FAQ {faq.id} score: {score}")  
        
        if score >= threshold:
            scored_faqs.append((score, faq))
    
    # 점수순으로 정렬
    scored_faqs.sort(key=lambda x: x[0], reverse=True)
    print(f"Final results count: {len(scored_faqs)}")  
    
    return [faq for score, faq in scored_faqs]

@router.post("/", response_model=FAQResponse)
def create_faq(
    faq: FAQCreate, 
    db: Session = Depends(get_db)
):
    """새로운 FAQ를 생성합니다."""
    db_faq = FAQ(**faq.model_dump())
    db.add(db_faq)
    db.commit()
    db.refresh(db_faq)
    return db_faq

@router.put("/{faq_id}", response_model=FAQResponse)
def update_faq(
    faq_id: int,
    faq_update: FAQCreate,
    db: Session = Depends(get_db)
):
    """FAQ를 수정합니다."""
    db_faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if not db_faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    
    for key, value in faq_update.model_dump().items():
        setattr(db_faq, key, value)
    
    db.commit()
    db.refresh(db_faq)
    return db_faq

@router.delete("/{faq_id}")
def delete_faq(
    faq_id: int, 
    db: Session = Depends(get_db)
):
    """FAQ를 삭제합니다."""
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    db.delete(faq)
    db.commit()
    return {"message": "FAQ가 성공적으로 삭제되었습니다."}