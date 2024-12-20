from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path

# FastAPI 인스턴스 생성
app = FastAPI(
    title="라이언 헬퍼",
    description="라이언 헬퍼",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포 시에는 특정 도메인만 허용하도록 수정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # 개발 환경에서 코드 변경 시 자동 재시작
    )