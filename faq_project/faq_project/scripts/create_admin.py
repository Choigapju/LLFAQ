# scripts/create_admin.py
import sys
sys.path.append(".")

from app.database.session import SessionLocal, Base, engine
from app.core.security import get_password_hash
from app.models.user import User

def create_admin(email: str, username: str, password: str):
    db = SessionLocal()
    try:
        # 기존 사용자 확인
        db_user = db.query(User).filter(
            (User.email == email) | (User.username == username)
        ).first()
        
        if db_user:
            print(f"User with email {email} or username {username} already exists")
            return

        # 관리자 계정 생성
        db_user = User(
            email=email,
            username=username,
            hashed_password=get_password_hash(password),
            is_active=True,
            is_admin=True
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        print(f"Admin user {username} created successfully")
    
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python create_admin.py EMAIL USERNAME PASSWORD")
        sys.exit(1)
    
    email, username, password = sys.argv[1:]
    Base.metadata.create_all(bind=engine)
    create_admin(email, username, password)