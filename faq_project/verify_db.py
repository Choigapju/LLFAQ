from database import DatabaseManager
from pathlib import Path

def verify_database():
    db = DatabaseManager()
    
    print("\n=== 데이터베이스 검증 시작 ===")
    
    db_path = Path("database/faq.db")
    if db_path.exists():
        print(f"✅ 데이터베이스 파일 확인: {db_path}")
    else:
        print(f"❌ 데이터베이스 파일이 없습니다: {db_path}")
        return
    
    try:
        db.cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='faq'
        """)
        if db.cursor.fetchone():
            print("✅ FAQ  테이블 존재 확인")
            
            db.cursor.execute("PRAGMA table_info(faq)")
            columns = db.cursor.fetchall()
            print("\n테이블 구조")
            for col in columns:
                print(f" - {col[1]} ({col[2]})")
                
        else:
            print("❌ FAQ 테이블이 없습니다.")
            return
        
        db.cursor.execute("SELECT COUNT(*) FROM faq")
        count = db.cursor.fetchone()[0]
        print(f"\n총 FAQ 수: {count}")
        
        if count > 0:
            print("\n최근 등록된 FAQ 5개")
            db.cursor.execute("""
            SELECT id, keywords,
                substr(question, 1, 30) as question_preview,
                substr(answer, 1, 30) as answer_preview
            FROM faq
            ORDER BY id DESC
            LIMIT 5
            """)
            
            rows = db.cursor.fetchall()
            for row in rows:
                print(f"\nID: {row[0]}")
                print(f"키워드: {row[1]}")
                print(f"질문 미리보기: {row[2]}...")
                print(f"답변 미리보기: {row[3]}...")
                
        print("\n키워드 분포")
        db.cursor.execute("""
            SELECT keywords, COUNT(*) as count
            FROM faq
            GROUP BY keywords
            ORDER BY count DESC
            LIMIT 5
        """)
        keyword_dist = db.cursor.fetchall()
        for kw, count in keyword_dist:
            print(f" - {kw}: {count}개")
            
    except Exception as e:
        print(f"\n❌ 검증 중 오류 발생: {e}")
        
    finally:
        db.close()
        print("\n=== 데이터베이스 검증 완료 ===")
        
if __name__ == "__main__":
    verify_database()