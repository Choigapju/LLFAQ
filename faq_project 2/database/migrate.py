# database/migrate.py
import sqlite3
import psycopg2
from psycopg2.extras import DictCursor
import os
from dotenv import load_dotenv

load_dotenv()

def migrate_data():
    # SQLite 연결
    sqlite_conn = sqlite3.connect('database/faq.db')
    sqlite_cur = sqlite_conn.cursor()
    
    try:
        # SQLite 테이블 구조 확인
        print("\nChecking SQLite schema:")
        sqlite_cur.execute("PRAGMA table_info(faq)")
        columns = sqlite_cur.fetchall()
        print("FAQ table columns:", columns)
        
        # 샘플 데이터 확인
        print("\nChecking sample data:")
        sqlite_cur.execute("SELECT * FROM faq LIMIT 1")
        sample = sqlite_cur.fetchone()
        print("Sample FAQ row:", sample)
        
        # PostgreSQL 연결
        pg_params = {
            'dbname': os.getenv('POSTGRES_DB'),
            'user': os.getenv('POSTGRES_USER'),
            'password': os.getenv('POSTGRES_PASSWORD'),
            'host': os.getenv('POSTGRES_HOST'),
            'port': os.getenv('POSTGRES_PORT', '5432')
        }
        pg_conn = psycopg2.connect(**pg_params)
        pg_cur = pg_conn.cursor()
        
        # FAQ 데이터 마이그레이션
        print("\nMigrating FAQ data...")
        sqlite_cur.execute("SELECT * FROM faq")
        faqs = sqlite_cur.fetchall()
        
        # PostgreSQL 데이터 초기화
        pg_cur.execute("TRUNCATE faq RESTART IDENTITY CASCADE")
        
        # 데이터 이전
        for faq in faqs:
            print(f"Migrating FAQ: {faq}")
            # keywords 컬럼이 비어있는 경우 question에서 추출
            if not faq[1]:  # keywords가 비어있는 경우
                # 쉼표로 구분된 경우 첫 번째 부분을 키워드로 사용
                keywords = faq[2].split(',')[0].strip() if ',' in faq[2] else faq[2].split()[0]
            else:
                keywords = faq[1]
                
            pg_cur.execute("""
                INSERT INTO faq (keywords, question, answer, category)
                VALUES (%s, %s, %s, %s)
            """, (keywords, faq[2], faq[3], "기타"))
        
        pg_conn.commit()
        print("\nMigration completed successfully!")
        
    except Exception as e:
        print(f"\nError during migration: {e}")
        if 'pg_conn' in locals():
            pg_conn.rollback()
        raise
    finally:
        sqlite_cur.close()
        sqlite_conn.close()
        if 'pg_conn' in locals():
            pg_cur.close()
            pg_conn.close()

if __name__ == "__main__":
    migrate_data()