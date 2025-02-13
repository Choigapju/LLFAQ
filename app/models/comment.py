from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.sql import func
from app.database.session import Base

class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)
    
    # FAQ 관계
    faq_id = Column(Integer, ForeignKey("faqs.id"))
    
    # User 관련 필드와 relationship 제거
    # user_id = Column(Integer, ForeignKey("users.id"))
    # user = relationship("User", back_populates="comments")