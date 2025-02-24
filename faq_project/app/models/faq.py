from sqlalchemy import Column, Integer, String, Text
from app.database.session import Base

class FAQ(Base):
    __tablename__ = "faqs"
    
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String)
    keywords = Column(String)
    question = Column(Text)
    answer = Column(Text)