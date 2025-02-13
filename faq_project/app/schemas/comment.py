from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class CommentBase(BaseModel):
    content: str
    faq_id: int

class CommentCreate(CommentBase):
    pass

class CommentUpdate(BaseModel):
    content: str

class Comment(CommentBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    is_deleted: bool = False
    # user_id 필드와 User 관련 참조 제거

    class Config:
        from_attributes = True