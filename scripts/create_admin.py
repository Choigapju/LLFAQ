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
        # chgju@likelion.net, PW: itlab
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

def reset_admin_password(email: str, new_password: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.hashed_password = get_password_hash(new_password)
            db.commit()
            print(f"Password reset successfully for {email}")
        else:
            print(f"User with email {email} not found")
    finally:
        db.close()

if __name__ == "__main__":
    # 임시로 직접 비밀번호 리셋 코드 추가
    reset_admin_password("chgju@likelion.net", "itlab")
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("Create admin: python create_admin.py create EMAIL USERNAME PASSWORD")
        print("Reset password: python create_admin.py reset EMAIL NEW_PASSWORD")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create":
        if len(sys.argv) != 5:
            print("Usage: python create_admin.py create EMAIL USERNAME PASSWORD")
            sys.exit(1)
        email, username, password = sys.argv[2:]
        Base.metadata.create_all(bind=engine)
        create_admin(email, username, password)
    
    elif command == "reset":
        if len(sys.argv) != 4:
            print("Usage: python create_admin.py reset EMAIL NEW_PASSWORD")
            sys.exit(1)
        email, new_password = sys.argv[2:]
        reset_admin_password(email, new_password)
    else:
        print("Unknown command. Use 'create' or 'reset'")