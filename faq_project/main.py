from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import os
from sqladmin import Admin
from api.admin import FAQAdmin, NoticeAdmin, AdminAuth
from database.db_manager import DatabaseManager
from starlette.middleware.sessions import SessionMiddleware  # 이 줄 추가

# FastAPI 인스턴스 생성
app = FastAPI(
    title="라이언 헬퍼",
    description="라이언 헬퍼",
    version="1.0.0"
)

# 환경변수에서 시크릿 키 가져오기
SECRET_KEY = os.environ.get("SECRET_KEY", "llfaq")

# 세션 미들웨어 추가 (관리자 인증에 필요)
app.add_middleware(SessionMiddleware, secret_key="llfaq")  # 안전한 비밀키로 변경하세요

# Admin 설정
db_manager = DatabaseManager()
admin = Admin(
    app, 
    engine=db_manager.engine,
    authentication_backend=AdminAuth(secret_key="llfaq")  # 안전한 비밀키로 변경하세요
)
admin.add_view(FAQAdmin)
admin.add_view(NoticeAdmin)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포 시에는 특정 도메인만 허용하도록 수정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# favicon.ico 처리
@app.get('/favicon.ico')
async def get_favicon():
    # favicon.ico 파일 경로
    favicon_path = Path("static/favicon.ico")
    if favicon_path.exists():
        return FileResponse(favicon_path)
    else:
        return JSONResponse(status_code=204, content={})

# 루트 경로 추가
@app.get("/")
async def root():
    return JSONResponse({
        "message": "멋쟁이사자처럼 FAQ API",
        "version": "1.0.0",
        "available_endpoints": {
            "API 문서": "/docs 또는 /redoc",
            "모든 FAQ 조회": "/api/faqs/",
            "FAQ 검색": "/api/faqs/search/?keyword=검색어",
            "FAQ 추가": "/api/faqs/ (POST)"
        }
    })

# 라우터 포함
app.include_router(router, prefix="/api")

# Render.com은 자체적으로 uvicorn을 실행하므로, 
# 로컬 개발 환경에서만 실행되도록 수정
if __name__ == "__main__":
    import uvicorn
    
    # Render.com의 PORT 환경 변수를 사용
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # 개발 환경에서 코드 변경 시 자동 재시작
    )