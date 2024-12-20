# api/models.py
from pydantic import BaseModel
from typing import List, Optional

class FAQBase(BaseModel):
    keywords: str
    question: str
    answer: str

class FAQCreate(FAQBase):
    # FAQ 생성에 사용되는 모델
    pass

class FAQ(FAQBase):
    id: int
    
    class Config:
        from_attributes = True

# 응답 스키마 정의
class KeywordCount(BaseModel):
    keyword: str
    count: int

class PopularKeywordsResponse(BaseModel):
    popular_keywords: List[KeywordCount]

class SearchResponse(BaseModel):
    total: int
    available_keywords: List[str]
    results: List[FAQ]