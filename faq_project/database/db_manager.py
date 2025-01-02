import sqlite3
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base

class DatabaseManager:
    def __init__(self, db_name="faq.db"):
        # SQLite 연결 설정
        self.base_dir = Path(__file__).parent
        self.db_path = self.base_dir / db_name
        self.conn = None
        self.cursor = None
        
        # SQLAlchemy 엔진 설정
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        self.initialize_database()

    def initialize_database(self):
        try:
            # SQLite 직접 연결 초기화
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            
            # 스키마 적용
            schema_path = self.base_dir / "schema.sql"
            if not schema_path.exists():
                print(f"Schema file not found at: {schema_path}")
                self.cursor.execute('''
                    CREATE TABLE IF NOT EXISTS faq(
                        id INTEGER PRIMARY KEY,
                        keywords TEXT NOT NULL,
                        question TEXT NOT NULL,
                        answer TEXT NOT NULL
                    );
                ''')
            else:
                with open(schema_path, 'r', encoding='utf-8') as f:
                    self.cursor.executescript(f.read())
            
            # SQLAlchemy 모델 테이블 생성
            Base.metadata.create_all(bind=self.engine)
            
            self.conn.commit()
            print("Database initialized successfully")
        except Exception as e:
            print(f"Database initialization error: {e}")

    def add_faq(self, keywords, question, answer):
        try:
            self.cursor.execute(
                "INSERT INTO faq (keywords, question, answer) VALUES (?, ?, ?)",
                (keywords, question, answer)
            )
            self.conn.commit()
            print(f"FAQ added successfully: {question[:30]}...")
            return True
        except Exception as e:
            print(f"Error adding FAQ: {e}")
            return False

    def search_by_keyword(self, keyword):
        try:
            self.cursor.execute(
                "SELECT * FROM faq WHERE keywords LIKE ?",
                (f"%{keyword}%",)
            )
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error searching FAQ: {e}")
            return []

    def get_all_faqs(self):
        try:
            self.cursor.execute("SELECT * FROM faq")
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error getting all FAQs: {e}")
            return []

    def get_session(self):
        """SQLAlchemy 세션을 반환합니다."""
        return self.SessionLocal()

    def close(self):
        if self.conn:
            self.conn.close()
            print("Database connection closed")

    def __del__(self):
        self.close()