# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.core.config import get_settings
from app.api.endpoints import router as faq_router
from app.api.auth import router as auth_router
from app.api.comment import router as comment_router
from app.api.notice import router as notice_router
from app.api.main import router as main_router
from app.database.session import Base, engine
import os

# Create database tables
Base.metadata.create_all(bind=engine)

settings = get_settings()
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",
        "https://your-frontend-domain.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 추가: 강제 HTTPS 비활성화 (Render에서는 이미 HTTPS 처리)
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"]
)

# API 라우터들
app.include_router(main_router, prefix=settings.API_V1_STR + "/main", tags=["main"])  # 추가
app.include_router(faq_router, prefix=settings.API_V1_STR + "/faqs", tags=["faqs"])
app.include_router(auth_router, prefix=settings.API_V1_STR + "/auth", tags=["auth"])
app.include_router(comment_router, prefix=settings.API_V1_STR + "/comments", tags=["comments"])
app.include_router(notice_router, prefix=settings.API_V1_STR + "/notices", tags=["notices"])

# 루트 경로 리다이렉션 (선택사항)
@app.get("/")
async def root():
    return {"message": "Welcome to FAQ API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)