from pydantic import BaseModel
from typing import Optional

class FAQBase(BaseModel):
    category: float
    keywords: str
    question: str
    answer: str

class FAQCreate(FAQBase):
    pass

class FAQResponse(FAQBase):
    id: int
    
    class Config:
        from_attributes = True