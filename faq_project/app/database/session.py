from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 테이블 재생성을 위한 함수 수정
def reset_database():
    # 기존 테이블들과의 의존성을 고려하여 삭제
    with engine.connect() as conn:
        print("Dropping all tables with CASCADE...")
        conn.execute(text("DROP TABLE IF EXISTS faqs CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS comments CASCADE"))
        conn.commit()
    
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Database reset complete!")