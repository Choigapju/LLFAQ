import sqlite3
import os
from pathlib import Path

class DatabaseManager:
    def __init__(self, db_name="faq.db"):
        self.base_dir = Path(__file__).parent
        self.db_path = self.base_dir / db_name
        self.conn = None
        self.cursor = None
        self.initialize_databse()
        
    def initialize_databse(self):
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            
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
                    
                    
            self.conn.commit()
            print("Database initialized successfully")
            
        except Exception as e:
            print(f"Database initializeation error: {e}")
            
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
        
    def close(self):
        if self.conn:
            self.conn.close()
            print("Database connection closed")