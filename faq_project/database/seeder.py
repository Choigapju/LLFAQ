from pathlib import Path
import json
from datetime import datetime, timedelta
import sqlite3
from typing import Dict, Any, List

class DatabaseSeeder:
    def __init__(self, db_path: str = "database/faq.db"):
        self.db_path = Path(db_path)
        self.seed_data_path = Path("database/seeds")
        self.seed_data_path.mkdir(exist_ok=True)
        
    def _connect_db(self) -> sqlite3.Connection:
        """데이터베이스 연결을 생성합니다."""
        return sqlite3.connect(self.db_path)
    
    def _load_seed_data(self, name: str) -> Dict[str, Any]:
        """시드 데이터 JSON 파일을 로드합니다."""
        seed_file = self.seed_data_path / f"{name}.json"
        if not seed_file.exists():
            raise FileNotFoundError(f"Seed file not found: {seed_file}")
        
        with open(seed_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _process_date_strings(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """날짜 문자열을 상대적인 날짜로 변환합니다."""
        date_markers = {
            "NOW": datetime.now(),
            "TODAY": datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
            "YESTERDAY": datetime.now() - timedelta(days=1),
            "LAST_WEEK": datetime.now() - timedelta(weeks=1),
            "LAST_MONTH": datetime.now() - timedelta(days=30),
        }
        
        def process_value(value: Any) -> Any:
            if isinstance(value, str) and value.startswith("@"):
                marker = value[1:]  # Remove @ symbol
                if marker in date_markers:
                    return date_markers[marker].strftime('%Y-%m-%d %H:%M:%S')
            return value
        
        def process_dict(d: Dict[str, Any]) -> Dict[str, Any]:
            return {k: process_value(v) for k, v in d.items()}
        
        if isinstance(data, list):
            return [process_dict(item) for item in data]
        return process_dict(data)
    
    def seed_notices(self, clear_existing: bool = False):
        """공지사항 테이블에 시드 데이터를 삽입합니다."""
        conn = self._connect_db()
        cursor = conn.cursor()
        
        try:
            seed_data = self._load_seed_data("notices")
            notices = self._process_date_strings(seed_data["notices"])
            
            if clear_existing:
                cursor.execute("DELETE FROM notices")
            
            for notice in notices:
                cursor.execute("""
                    INSERT INTO notices (title, content, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    notice["title"],
                    notice["content"],
                    notice["created_at"],
                    notice.get("updated_at", notice["created_at"])
                ))
            
            conn.commit()
            print(f"Successfully seeded {len(notices)} notices")
            
        except Exception as e:
            conn.rollback()
            print(f"Error seeding notices: {e}")
            raise
        finally:
            conn.close()
    
    def run_all(self, clear_existing: bool = False):
        """모든 시드 데이터를 적용합니다."""
        self.seed_notices(clear_existing)
        # 추후 다른 테이블의 시드 메서드 추가 가능

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Database seeder utility')
    parser.add_argument('--clear', action='store_true', 
                       help='Clear existing data before seeding')
    parser.add_argument('--table', type=str, default='all',
                       help='Specific table to seed (default: all)')
    
    args = parser.parse_args()
    seeder = DatabaseSeeder()
    
    if args.table == 'all':
        seeder.run_all(args.clear)
    elif args.table == 'notices':
        seeder.seed_notices(args.clear)
    else:
        print(f"Unknown table: {args.table}")