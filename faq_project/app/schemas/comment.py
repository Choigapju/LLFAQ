from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.schemas.user import User

class CommentBase(BaseModel):
    content: str

class CommentCreate(CommentBase):
    faq_id: int

class CommentUpdate(BaseModel):
    content: str

class Comment(CommentBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    is_deleted: bool
    user_id: int
    faq_id: int
    user: User  # User 스키마 참조

    class Config:
        from_attributes = True