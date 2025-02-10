from database import DatabaseManager
from pathlib import Path
from database.seeder import DatabaseSeeder
from sqlite3 import Error as SQLiteError

print("Verification script started...")

class DatabaseVerifier:
    def __init__(self):
        print("Initializing DatabaseVerifier...")
        self.db = DatabaseManager()
        self.db_path = Path("database/faq.db")
        print(f"Database path: {self.db_path}")
    
    def verify_table_existence(self, table_name: str) -> bool:
        """테이블 존재 여부를 확인합니다."""
        self.db.cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table_name,))
        return bool(self.db.cursor.fetchone())
    
    def print_table_structure(self, table_name: str):
        """테이블 구조를 출력합니다."""
        self.db.cursor.execute(f"PRAGMA table_info({table_name})")
        columns = self.db.cursor.fetchall()
        print(f"\n{table_name} 테이블 구조")
        for col in columns:
            print(f" - {col[1]} ({col[2]})")
    
    def verify_faq_table(self):
        """FAQ 테이블을 검증합니다."""
        if not self.verify_table_existence('faq'):
            print("❌ FAQ 테이블이 없습니다.")
            return False
        
        print("✅ FAQ 테이블 존재 확인")
        self.print_table_structure('faq')
        
        # FAQ 데이터 검증
        self.db.cursor.execute("SELECT COUNT(*) FROM faq")
        count = self.db.cursor.fetchone()[0]
        print(f"\n총 FAQ 수: {count}")
        
        # FAQ가 없는 경우 시드 데이터 추가
        if count == 0:
            print("\nFAQ 시드 데이터 추가 중...")
            seeder = DatabaseSeeder()
            seeder.seed_faqs(clear_existing=False)
            print("✅ FAQ 시드 데이터 추가 완료")
            
            # 추가된 FAQ 수 다시 확인
            self.db.cursor.execute("SELECT COUNT(*) FROM faq")
            count = self.db.cursor.fetchone()[0]
            print(f"총 FAQ 수: {count}")
        
        if count > 0:
            self.show_recent_faqs()
            self.show_keyword_distribution()
        return True
    
    def verify_notices_table(self):
        """공지사항 테이블을 검증합니다."""
        if not self.verify_table_existence('notices'):
            print("❌ 공지사항 테이블이 없습니다.")
            return False
            
        print("\n✅ 공지사항 테이블 존재 확인")
        self.print_table_structure('notices')
        
        # 공지사항 데이터 확인
        self.db.cursor.execute("SELECT COUNT(*) FROM notices")
        notice_count = self.db.cursor.fetchone()[0]
        print(f"\n총 공지사항 수: {notice_count}")
        
        # 공지사항이 없는 경우 시드 데이터 추가
        if notice_count == 0:
            print("\n공지사항 시드 데이터 추가 중...")
            seeder = DatabaseSeeder()
            seeder.seed_notices(clear_existing=False)
            print("✅ 공지사항 시드 데이터 추가 완료")
        return True
    
    def show_recent_faqs(self):
        """최근 FAQ 5개를 출력합니다."""
        print("\n최근 등록된 FAQ 5개")
        self.db.cursor.execute("""
            SELECT id, keywords,
            substr(question, 1, 30) as question_preview,
            substr(answer, 1, 30) as answer_preview
            FROM faq
            ORDER BY id DESC
            LIMIT 5
        """)
        rows = self.db.cursor.fetchall()
        for row in rows:
            print(f"\nID: {row[0]}")
            print(f"키워드: {row[1]}")
            print(f"질문 미리보기: {row[2]}...")
            print(f"답변 미리보기: {row[3]}...")
    
    def show_keyword_distribution(self):
        """키워드 분포를 출력합니다."""
        print("\n키워드 분포")
        self.db.cursor.execute("""
            SELECT keywords, COUNT(*) as count
            FROM faq
            GROUP BY keywords
            ORDER BY count DESC
            LIMIT 5
        """)
        keyword_dist = self.db.cursor.fetchall()
        for kw, count in keyword_dist:
            print(f" - {kw}: {count}개")

    def verify_comments_table(self):
        """Comments 테이블을 검증합니다."""
        if not self.verify_table_existence('comments'):
            print("\n❌ Comments 테이블이 없습니다.")
            return False
            
        print("\n✅ Comments 테이블 존재 확인")
        self.print_table_structure('comments')
        
        self.db.cursor.execute("""
            SELECT COUNT(*) as total,
                COUNT(CASE WHEN faq_id IS NOT NULL THEN 1 END) as faq_comments,
                COUNT(CASE WHEN notice_id IS NOT NULL THEN 1 END) as notice_comments
            FROM comments
        """)
        counts = self.db.cursor.fetchone()
        print(f"\n총 댓글 수: {counts[0]}")
        print(f" - FAQ 댓글: {counts[1]}")
        print(f" - 공지사항 댓글: {counts[2]}")
        
        if counts[0] > 0:
            self.show_recent_comments()
        return True

    def show_recent_comments(self):
        """최근 댓글 5개를 출력합니다."""
        print("\n최근 등록된 댓글 5개")
        self.db.cursor.execute("""
            SELECT id, substr(content, 1, 50) as content_preview,
                author, created_at, faq_id, notice_id
            FROM comments
            ORDER BY created_at DESC
            LIMIT 5
        """)
        rows = self.db.cursor.fetchall()
        for row in rows:
            print(f"\nID: {row[0]}")
            print(f"내용 미리보기: {row[1]}...")
            print(f"작성자: {row[2]}")
            print(f"작성일시: {row[3]}")
            if row[4]:
                print(f"FAQ ID: {row[4]}")
            if row[5]:
                print(f"공지사항 ID: {row[5]}")

def verify_database():
    print("\n=== 데이터베이스 검증 시작 ===")
    
    try:
        verifier = DatabaseVerifier()
        
        if not verifier.db_path.exists():
            print(f"❌ 데이터베이스 파일이 없습니다: {verifier.db_path}")
            return
        
        print(f"✅ 데이터베이스 파일 확인: {verifier.db_path}")
        
        verifier.verify_faq_table()
        verifier.verify_notices_table()
        verifier.verify_comments_table()
        
    except SQLiteError as e:
        print(f"\n❌ 데이터베이스 오류 발생: {e}")
        raise
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류 발생: {e}")
        raise
    finally:
        if 'verifier' in locals() and hasattr(verifier, 'db'):
            verifier.db.close()
        print("\n=== 데이터베이스 검증 완료 ===")

if __name__ == "__main__":
    try:
        print("Starting database verification...")
        verify_database()
    except Exception as e:
        print(f"Fatal error: {e}")