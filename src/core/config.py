from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """환경 변수에서 로드되는 애플리케이션 설정"""

    # 데이터베이스 설정
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    # Redis 설정
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str = ""

    # Elasticsearch 설정
    ELASTICSEARCH_HOST: str
    ELASTICSEARCH_PORT: int
    ELASTICSEARCH_USER: str = "elastic"
    ELASTICSEARCH_PASSWORD: str

    # 애플리케이션 설정
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True

    # 보안 설정
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # AI/LLM 설정
    OPENAI_API_KEY: str = ""
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_PROJECT: str = "searchive"

    # CORS 설정
    ALLOWED_ORIGINS: str = "http://localhost:5173"

    # 카카오 OAuth 설정
    KAKAO_CLIENT_ID: str
    KAKAO_CLIENT_SECRET: str = ""
    KAKAO_REDIRECT_URI: str

    # 프론트엔드 URL
    FRONTEND_URL: str = "http://localhost:5173"

    # MinIO 설정
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_SECURE: bool = False
    MINIO_BUCKET_NAME: str = "user-documents"

    # AI 자동 태깅 설정
    KEYWORD_EXTRACTION_THRESHOLD: int = 5  # Cold Start와 Normal 경로를 구분하는 문서 수 임계값
    KEYWORD_EXTRACTION_COUNT: int = 3  # 추출할 키워드 개수

    # Ollama 설정
    OLLAMA_HOST: str
    OLLAMA_PORT: int
    OLLAMA_MODEL: str

    @property
    def DATABASE_URL(self) -> str:
        """PostgreSQL 데이터베이스 URL 생성"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """비동기 PostgreSQL 데이터베이스 URL 생성"""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def REDIS_URL(self) -> str:
        """Redis URL 생성"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"

    @property
    def ELASTICSEARCH_URL(self) -> str:
        """Elasticsearch URL 생성"""
        return f"http://{self.ELASTICSEARCH_HOST}:{self.ELASTICSEARCH_PORT}"

    @property
    def OLLAMA_URL(self) -> str:
        """Ollama API URL 생성"""
        return f"http://{self.OLLAMA_HOST}:{self.OLLAMA_PORT}"

    @property
    def CORS_ORIGINS(self) -> List[str]:
        """쉼표로 구분된 문자열에서 CORS origin 목록 파싱"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


# 전역 설정 인스턴스
settings = Settings()
