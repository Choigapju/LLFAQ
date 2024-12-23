from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

class FAQBase(BaseModel):
    keywords: str
    question: str
    answer: str

class FAQCreate(FAQBase):
    # FAQ 생성에 사용되는 모델
    pass

class FAQ(FAQBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

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

# 추천 검색어 3개
class TopKeywordsResponse(BaseModel):
    top_keywords: List[str]

# 공지사항
class NoticeBase(BaseModel):
    title: str
    content: str

class NoticeCreate(NoticeBase):
    pass

class Notice(NoticeBase):
    id: int
    is_new: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )