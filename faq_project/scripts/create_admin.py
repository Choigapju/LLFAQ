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
    print("Starting password reset...")
    print(f"Database URL: {engine.url}")
    db = SessionLocal()
    try:
        # 먼저 사용자가 존재하는지 확인
        user = db.query(User).filter(User.email == "chgju@likelion.net").first()
        if user:
            print(f"Found user: {user.email}")
            print(f"Current password hash: {user.hashed_password}")
            user.hashed_password = get_password_hash("itlab")
            print(f"New password hash: {user.hashed_password}")
            db.commit()
            print("Password reset completed successfully")
        else:
            print("User not found, creating new admin user...")
            new_user = User(
                email="chgju@likelion.net",
                username="chgju",
                hashed_password=get_password_hash("itlab"),
                is_active=True,
                is_admin=True
            )
            db.add(new_user)
            db.commit()
            print("New admin user created successfully")
    except Exception as e:
        print(f"Error during operation: {str(e)}")
        print(f"Error type: {type(e)}")
    finally:
        db.close()
    
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