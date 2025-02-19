from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.core.config import get_settings
from app.api.endpoints import router as faq_router
from app.api.comment import router as comment_router
from app.api.notice import router as notice_router
from app.api.main import router as main_router
from app.api.user import router as user_router  # 새로 추가
from app.api.search import router as search_router
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
        "http://localhost:3000",  # React 개발 서버
        "http://localhost:3001",  # 다른 로컬 포트
        "https://lion-helper-v2.vercel.app"  # Vercel 프로덕션 도메인
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"]
)

# API 라우터들
app.include_router(main_router, prefix=settings.API_V1_STR + "/main", tags=["main"])
app.include_router(faq_router, prefix=settings.API_V1_STR + "/faqs", tags=["faqs"])
app.include_router(comment_router, prefix=settings.API_V1_STR + "/comments", tags=["comments"])
app.include_router(notice_router, prefix=settings.API_V1_STR + "/notices", tags=["notices"])
app.include_router(user_router, prefix=settings.API_V1_STR + "/users", tags=["users"])
app.include_router(search_router, prefix=settings.API_V1_STR + "/search", tags=["search"])

@app.get("/")
async def root():
    return {"message": "Welcome to FAQ API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)