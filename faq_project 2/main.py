from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import os
from sqladmin import Admin
from api.admin import UserAdmin, AdminAuth  # FAQAdmin, NoticeAdmin 제거
from database.db_manager import DatabaseManager
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI(
    title="라이언 헬퍼",
    description="라이언 헬퍼 API",
    version="1.0.0"
)

# 환경변수 설정
SECRET_KEY = os.getenv("SECRET_KEY", "llfaq")  # 실제 배포시 변경 필요

# 세션 미들웨어
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Admin 설정
db_manager = DatabaseManager()
admin = Admin(
    app, 
    engine=db_manager.engine,
    authentication_backend=AdminAuth(secret_key=SECRET_KEY)
)
admin.add_view(UserAdmin)  # UserAdmin만 추가

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 실제 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# favicon.ico
@app.get('/favicon.ico')
async def get_favicon():
    favicon_path = Path("static/favicon.ico")
    if favicon_path.exists():
        return FileResponse(favicon_path)
    return JSONResponse(status_code=204, content={})

# 루트 경로
@app.get("/")
async def root():
    return JSONResponse({
        "message": "멋쟁이사자처럼 FAQ API",
        "version": "1.0.0",
        "available_endpoints": {
            "API 문서": "/docs 또는 /redoc",
            "관리자 페이지": "/admin",
            "FAQ 검색": "/api/faqs/search/",
            "스마트 검색": "/api/faqs/smart-search/"
        }
    })

# API 라우터 포함
app.include_router(router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )