from sqlalchemy import Column, Integer, String, Float
from app.database.session import Base

class FAQ(Base):
    __tablename__ = "faqs"
    
    id = Column(Integer, primary_key=True, index=True)
    category = Column(Float)
    keywords = Column(String)
    question = Column(String)
    answer = Column(String)