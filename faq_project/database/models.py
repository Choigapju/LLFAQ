from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class FAQModel(Base):
    __tablename__ = "faq"
    
    id = Column(Integer, primary_key=True, index=True)
    keywords = Column(String)
    question = Column(Text)
    answer = Column(Text)

class NoticeModel(Base):
    __tablename__ = "notices"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)