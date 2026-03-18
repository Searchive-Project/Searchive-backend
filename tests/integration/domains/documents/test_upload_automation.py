
import pytest
import os
import numpy as np
from io import BytesIO
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import UploadFile
from sqlalchemy import select
from src.domains.documents.service import DocumentService
from src.domains.documents.repository import DocumentRepository
from src.domains.users.models import User
from src.domains.documents.models import Document
from src.domains.aichat.models import Conversation
from src.core.config import settings

@pytest.mark.asyncio
class TestDocumentUploadAutomation:
    """문서 업로드 시 요약 및 태그 생성 자동화 기능 테스트"""

    async def test_upload_with_automation(self, async_db_session):
        """100자 이상 문서 업로드 시 요약과 태그가 생성되는지 테스트"""
        
        # 1. 테스트 사용자 준비 (기존 사용자 또는 생성)
        result = await async_db_session.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if not user:
            user = User(nickname="test_auto_user", kakao_id="auto_123")
            async_db_session.add(user)
            await async_db_session.commit()
            await async_db_session.refresh(user)

        # 2. 서비스 인스턴스 준비
        doc_repo = DocumentRepository(async_db_session)
        doc_service = DocumentService(doc_repo, async_db_session)

        # 3. 100자 이상 샘플 파일 로드
        sample_path = os.path.join("tests", "fixtures", "sample_documents", "test_automation.txt")
        with open(sample_path, "rb") as f:
            content = f.read()
        
        # FastAPI UploadFile을 Mock으로 생성
        upload_file = MagicMock(spec=UploadFile)
        upload_file.filename = "test_automation.txt"
        upload_file.content_type = "text/plain"
        upload_file.read = AsyncMock(return_value=content)
        upload_file.file = BytesIO(content)

        # 4. AI 서비스 및 임베딩 서비스 Mocking
        mock_summary = "이 문서는 인공지능과 머신러닝의 핵심 개념과 발전 과정을 다룬다"
        mock_keywords = (["인공지능", "머신러닝", "딥러닝"], "keybert")
        # 가짜 임베딩 벡터 (384차원 가정)
        mock_embedding = np.random.rand(384).astype(np.float32)

        with patch("src.domains.documents.service.ollama_summarizer.summarize", new_callable=AsyncMock) as mocked_summarize, \
             patch("src.domains.documents.service.keyword_extraction_service.extract_keywords", new_callable=AsyncMock) as mocked_extract, \
             patch("src.domains.tags.service.embedding_service.encode", new_callable=AsyncMock) as mocked_encode:
            
            mocked_summarize.return_value = mock_summary
            mocked_extract.return_value = mock_keywords
            mocked_encode.return_value = mock_embedding

            # 4. 문서 업로드 실행
            doc, tags, method = await doc_service.upload_document(user.user_id, upload_file)

        # 5. 검증 (Validation)
        print(f"\n[Test Result] Document ID: {doc.document_id}")
        print(f"[Test Result] Summary: {doc.summary}")
        print(f"[Test Result] Tags: {[t.name for t in tags]} (Method: {method})")

        # 5-1. 요약 검증
        assert doc.summary == mock_summary

        # 5-2. 태그 검증
        assert len(tags) == 3
        assert any(t.name == "인공지능" for t in tags)
        
        # 5-3. 데이터베이스 저장 상태 확인
        # tags 관계를 함께 로드하기 위해 select 쿼리 사용
        from sqlalchemy.orm import joinedload
        stmt = select(Document).options(joinedload(Document.tags)).where(
            Document.document_id == doc.document_id,
            Document.user_id == user.user_id
        )
        result = await async_db_session.execute(stmt)
        uploaded_doc = result.unique().scalar_one_or_none()
        
        assert uploaded_doc is not None
        assert uploaded_doc.summary == mock_summary
        assert len(uploaded_doc.tags) == 3
        assert any(t.name == "인공지능" for t in uploaded_doc.tags)
