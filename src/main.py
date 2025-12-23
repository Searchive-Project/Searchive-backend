from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from src.core.config import settings
from src.core.exception import (
    CustomException,
    custom_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from alembic.config import Config
from alembic import command
import os

# FastAPI 앱 초기화
app = FastAPI(
    title="Searchive Backend API",
    description="AI 기반 지능형 검색 및 문서 관리 시스템",
    version="1.0.0",
    debug=settings.DEBUG,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 예외 핸들러 등록
app.add_exception_handler(CustomException, custom_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)


# @app.on_event("startup")
# async def startup_event():
#     """애플리케이션 시작 시 데이터베이스 마이그레이션 실행"""
#     alembic_cfg = Config("alembic.ini")
#     command.upgrade(alembic_cfg, "head")


@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 Redis 연결 종료"""
    await close_redis()


@app.get("/")
async def root():
    """루트 엔드포인트 (헬스 체크)"""
    return {
        "message": "Searchive Backend API에 오신 것을 환영합니다",
        "status": "running",
        "environment": settings.APP_ENV,
    }


@app.get("/health")
async def health_check():
    """모니터링용 헬스 체크 엔드포인트"""
    return {"status": "healthy"}


# 도메인 라우터 포함
from src.domains.auth.controller import router as auth_router
from src.domains.documents.controller import router as documents_router
from src.domains.aichat.controller import router as aichat_router
from src.domains.users.controller import router as users_router
from src.core.redis import close_redis

app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(documents_router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(aichat_router, prefix="/api/v1/aichat", tags=["AI Chat"])
app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )
