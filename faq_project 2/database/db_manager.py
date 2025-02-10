import os
from pathlib import Path
from typing import List, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

class DatabaseManager:
    def __init__(self):
        # PostgreSQL 연결 설정
        self.connection_params = {
            'dbname': os.getenv('POSTGRES_DB'),
            'user': os.getenv('POSTGRES_USER'),
            'password': os.getenv('POSTGRES_PASSWORD'),
            'host': os.getenv('POSTGRES_HOST'),
            'port': os.getenv('POSTGRES_PORT', '5432')
        }
        
        # SQLAlchemy 엔진 설정
        self.engine = create_engine(
            f"postgresql://{self.connection_params['user']}:{self.connection_params['password']}@"
            f"{self.connection_params['host']}:{self.connection_params['port']}/{self.connection_params['dbname']}"
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        self.connect()
        self.initialize_database()

    def connect(self):
        """PostgreSQL 연결 설정"""
        self.connection = psycopg2.connect(**self.connection_params)
        self.connection.set_session(autocommit=False)
        self.cursor = self.connection.cursor(cursor_factory=RealDictCursor)

    def initialize_database(self):
        try:
            # SQLAlchemy 모델 테이블 생성
            Base.metadata.create_all(bind=self.engine)
            print("Database initialized successfully")
        except Exception as e:
            print(f"Database initialization error: {e}")

    def add_faq(self, keywords, question, answer):
        try:
            self.cursor.execute("""
                INSERT INTO faq (keywords, question, answer)
                VALUES (%s, %s, %s)
                RETURNING *
            """, (keywords, question, answer))
            self.commit()
            print(f"FAQ added successfully: {question[:30]}...")
            return True
        except Exception as e:
            print(f"Error adding FAQ: {e}")
            self.rollback()
            return False

    def search_by_keyword(self, keyword):
        try:
            self.cursor.execute(
                "SELECT * FROM faq WHERE keywords ILIKE %s",
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
        if hasattr(self, 'cursor'):
            self.cursor.close()
        if hasattr(self, 'connection'):
            self.connection.close()
            print("Database connection closed")

    def __del__(self):
        self.close()

    def commit(self):
        """변경사항 커밋"""
        try:
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Error during commit: {e}")
            self.rollback()
            return False

    def rollback(self):
        """변경사항 롤백"""
        try:
            self.connection.rollback()
        except Exception as e:
            print(f"Error during rollback: {e}")

    def execute_query(self, query, params=None):
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            return True
        except Exception as e:
            print(f"Error executing query: {e}")
            self.rollback()
            return False

    def smart_search_faqs(self, keywords: List[str]):
        try:
            placeholders = ','.join(['%s' for _ in keywords])
            like_conditions = ' OR '.join(['keywords ILIKE %s' for _ in keywords])
            
            query = f"""
                WITH ranked_results AS (
                    SELECT *,
                        CASE
                            WHEN keywords = ANY(%s) THEN 1
                            WHEN {like_conditions} THEN 2
                            ELSE 3
                        END as relevance
                    FROM faq
                    WHERE {like_conditions}
                )
                SELECT * FROM ranked_results
                ORDER BY relevance, id DESC
            """
            
            params = [keywords]  # ANY 연산자를 위한 리스트
            params.extend([f'%{k}%' for k in keywords])  # ILIKE 패턴
            params.extend([f'%{k}%' for k in keywords])  # WHERE 절을 위한 중복

            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error in smart search: {e}")
            return []