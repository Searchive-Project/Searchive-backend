import pytest
import asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import redis

from src.core.config import settings
from src.db.session import Base


# ============================================
# Pytest Configuration
# ============================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================
# Database Fixtures
# ============================================

@pytest.fixture(scope="session")
def db_engine():
    """Create a test database engine."""
    engine = create_engine(
        settings.DATABASE_URL,
        poolclass=StaticPool,
    )
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create a new database session for a test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = SessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def db_session_with_data(db_session) -> Generator[Session, None, None]:
    """Create a database session with test data."""
    # Add any common test data here
    yield db_session


# ============================================
# Redis Fixtures
# ============================================

@pytest.fixture(scope="session")
def redis_client():
    """Create a Redis client for testing."""
    client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
        db=1,  # Use database 1 for testing (not production db 0)
        decode_responses=True
    )
    yield client
    # Clean up test data
    client.flushdb()
    client.close()


@pytest.fixture(scope="function")
def clean_redis(redis_client):
    """Clean Redis before each test."""
    redis_client.flushdb()
    yield redis_client
    redis_client.flushdb()


# ============================================
# FastAPI App Fixtures
# ============================================

@pytest.fixture(scope="session")
def app():
    """Create a FastAPI app instance for testing."""
    from src.main import app
    return app


@pytest.fixture(scope="function")
async def async_client(app):
    """Create an async HTTP client for testing."""
    from httpx import AsyncClient
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# ============================================
# Mock Fixtures (Unit Test용 - 실제 인프라 사용 안함)
# ============================================

@pytest.fixture
def mock_minio_client():
    """MinIO 클라이언트 Mock 픽스처 (실제 파일 업로드 방지)"""
    from unittest.mock import MagicMock

    mock_client = MagicMock()

    # upload_file 메서드 Mock - 실제 업로드 없이 경로만 반환
    mock_client.upload_file.return_value = "1/test-uuid-1234.pdf"

    # delete_file 메서드 Mock
    mock_client.delete_file.return_value = None

    # get_file_url 메서드 Mock
    mock_client.get_file_url.return_value = "http://minio-test/bucket/test-file.pdf?expires=3600"

    return mock_client


@pytest.fixture
def mock_elasticsearch_client():
    """Elasticsearch 클라이언트 Mock 픽스처 (실제 색인 방지)"""
    from unittest.mock import AsyncMock

    mock_client = AsyncMock()

    # index_document 메서드 Mock
    mock_client.index_document.return_value = True

    # get_document_count 메서드 Mock (Cold Start 테스트용)
    mock_client.get_document_count.return_value = 5

    # extract_significant_terms 메서드 Mock
    mock_client.extract_significant_terms.return_value = ["keyword1", "keyword2", "keyword3"]

    # delete_document 메서드 Mock
    mock_client.delete_document.return_value = True

    return mock_client


@pytest.fixture
def mock_text_extractor():
    """TextExtractor Mock 픽스처"""
    from unittest.mock import MagicMock

    mock_extractor = MagicMock()

    # extract_text_from_bytes 메서드 Mock - 항상 테스트용 텍스트 반환
    mock_extractor.extract_text_from_bytes.return_value = (
        "This is a test document content. "
        "Machine learning and deep learning are important topics in artificial intelligence."
    )

    return mock_extractor


@pytest.fixture
def mock_keyword_extraction_service():
    """KeywordExtractionService Mock 픽스처"""
    from unittest.mock import AsyncMock

    mock_service = AsyncMock()

    # extract_keywords 메서드 Mock - (키워드 리스트, 추출 방법) 튜플 반환
    mock_service.extract_keywords.return_value = (
        ["machine learning", "deep learning", "artificial intelligence"],
        "keybert"
    )

    return mock_service


@pytest.fixture
def mock_ollama_summarizer():
    """OllamaSummarizer Mock 픽스처"""
    from unittest.mock import AsyncMock

    mock_summarizer = AsyncMock()

    # summarize 메서드 Mock - 요약 텍스트 반환
    mock_summarizer.summarize.return_value = "This is a test summary of the document content."

    return mock_summarizer


@pytest.fixture
def mock_upload_file():
    """FastAPI UploadFile Mock 픽스처"""
    from unittest.mock import AsyncMock, MagicMock
    from io import BytesIO

    mock_file = MagicMock()
    mock_file.filename = "test_document.pdf"
    mock_file.content_type = "application/pdf"

    # 파일 데이터 (PDF 매직 넘버 포함)
    test_content = b"%PDF-1.4\nTest PDF content"
    mock_file.read = AsyncMock(return_value=test_content)
    mock_file.file = BytesIO(test_content)

    return mock_file


# ============================================
# File Fixtures (실제 샘플 파일 로딩)
# ============================================

@pytest.fixture
def sample_pdf_path():
    """샘플 PDF 파일 경로 반환"""
    from pathlib import Path
    return Path(__file__).parent / "fixtures" / "sample_documents" / "sample.pdf"


@pytest.fixture
def sample_docx_path():
    """샘플 DOCX 파일 경로 반환"""
    from pathlib import Path
    return Path(__file__).parent / "fixtures" / "sample_documents" / "sample.docx"


@pytest.fixture
def sample_txt_path():
    """샘플 TXT 파일 경로 반환"""
    from pathlib import Path
    return Path(__file__).parent / "fixtures" / "sample_documents" / "sample.txt"


@pytest.fixture
def sample_hwp_path():
    """샘플 HWP 파일 경로 반환"""
    from pathlib import Path
    return Path(__file__).parent / "fixtures" / "sample_documents" / "sample.hwp"


@pytest.fixture
def sample_pdf_file():
    """실제 샘플 PDF 파일 내용을 읽어서 UploadFile Mock 생성"""
    from unittest.mock import AsyncMock, MagicMock
    from io import BytesIO
    from pathlib import Path

    # 실제 샘플 파일 읽기
    sample_path = Path(__file__).parent / "fixtures" / "sample_documents" / "sample.pdf"
    with open(sample_path, "rb") as f:
        file_content = f.read()

    # UploadFile Mock 생성
    mock_file = MagicMock()
    mock_file.filename = "sample.pdf"
    mock_file.content_type = "application/pdf"
    mock_file.read = AsyncMock(return_value=file_content)
    mock_file.file = BytesIO(file_content)

    return mock_file


@pytest.fixture
def sample_docx_file():
    """실제 샘플 DOCX 파일 내용을 읽어서 UploadFile Mock 생성"""
    from unittest.mock import AsyncMock, MagicMock
    from io import BytesIO
    from pathlib import Path

    # 실제 샘플 파일 읽기
    sample_path = Path(__file__).parent / "fixtures" / "sample_documents" / "sample.docx"
    with open(sample_path, "rb") as f:
        file_content = f.read()

    # UploadFile Mock 생성
    mock_file = MagicMock()
    mock_file.filename = "sample.docx"
    mock_file.content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    mock_file.read = AsyncMock(return_value=file_content)
    mock_file.file = BytesIO(file_content)

    return mock_file


@pytest.fixture
def sample_txt_file():
    """실제 샘플 TXT 파일 내용을 읽어서 UploadFile Mock 생성"""
    from unittest.mock import AsyncMock, MagicMock
    from io import BytesIO
    from pathlib import Path

    # 실제 샘플 파일 읽기
    sample_path = Path(__file__).parent / "fixtures" / "sample_documents" / "sample.txt"
    with open(sample_path, "rb") as f:
        file_content = f.read()

    # UploadFile Mock 생성
    mock_file = MagicMock()
    mock_file.filename = "sample.txt"
    mock_file.content_type = "text/plain"
    mock_file.read = AsyncMock(return_value=file_content)
    mock_file.file = BytesIO(file_content)

    return mock_file


@pytest.fixture
def sample_hwp_file():
    """실제 샘플 HWP 파일 내용을 읽어서 UploadFile Mock 생성"""
    from unittest.mock import AsyncMock, MagicMock
    from io import BytesIO
    from pathlib import Path

    # 실제 샘플 파일 읽기
    sample_path = Path(__file__).parent / "fixtures" / "sample_documents" / "sample.hwp"

    # HWP 파일이 없으면 None 반환
    if not sample_path.exists():
        return None

    with open(sample_path, "rb") as f:
        file_content = f.read()

    # UploadFile Mock 생성
    mock_file = MagicMock()
    mock_file.filename = "sample.hwp"
    mock_file.content_type = "application/x-hwp"
    mock_file.read = AsyncMock(return_value=file_content)
    mock_file.file = BytesIO(file_content)

    return mock_file


@pytest.fixture
def sample_text_content():
    """샘플 TXT 파일의 텍스트 내용 반환"""
    from pathlib import Path

    sample_path = Path(__file__).parent / "fixtures" / "sample_documents" / "sample.txt"
    with open(sample_path, "r", encoding="utf-8") as f:
        return f.read()
