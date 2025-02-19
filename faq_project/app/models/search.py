from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database.session import Base

class SearchKeyword(Base):
    __tablename__ = "search_keywords"
    
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, nullable=False)
    count = Column(Integer, default=1)
    last_searched_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())