from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from app.database.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, User as UserSchema, UserUpdate, Token
from app.core.security import (
    get_password_hash, 
    get_current_user, 
    get_current_admin_user,
    verify_password,
    create_access_token
)
from datetime import timedelta
import re

router = APIRouter()

# Access token 만료 시간 설정
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def validate_company_email(email: str) -> bool:
    company_domain = "@likelion.net"
    return email.endswith(company_domain)

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """사용자 로그인 및 토큰 발급"""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/", response_model=UserSchema)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """사내 이메일로 회원가입"""
    if not validate_company_email(user.email):
        raise HTTPException(
            status_code=400,
            detail="Invalid company email domain"
        )
    
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=get_password_hash(user.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/me", response_model=UserSchema)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """현재 로그인한 사용자 정보 조회"""
    return current_user

@router.put("/me", response_model=UserSchema)
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 정보 업데이트"""
    if user_update.password:
        current_user.hashed_password = get_password_hash(user_update.password)
    if user_update.username:
        current_user.username = user_update.username
    
    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/logout")
async def logout():
    """
    로그아웃 (클라이언트 측에서 토큰 제거)
    FastAPI JWT 구현에서는 서버 측 로그아웃이 필요 없지만,
    클라이언트 편의를 위해 200 응답을 반환합니다.
    """
    return {"message": "Successfully logged out"}