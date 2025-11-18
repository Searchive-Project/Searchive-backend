# -*- coding: utf-8 -*-
"""Document Service 단위 테스트 (Mock 사용 - 실제 MinIO/Elasticsearch 사용 안함)"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException

from src.domains.documents.service import DocumentService
from src.domains.documents.models import Document


class TestDocumentServiceUpload:
    """문서 업로드 서비스 테스트 (Mock 사용)"""

    @pytest.mark.asyncio
    async def test_upload_document_success(
        self,
        mock_minio_client,
        mock_elasticsearch_client,
        mock_text_extractor,
        mock_keyword_extraction_service,
        mock_upload_file
    ):
        """문서 업로드 성공 테스트 (실제 MinIO 업로드 없음)"""
        # Mock DocumentRepository
        mock_repository = AsyncMock()

        # Mock Document 객체 (SQLAlchemy 모델 대신 MagicMock 사용)
        mock_document = MagicMock()
        mock_document.document_id = 1
        mock_document.user_id = 123
        mock_document.original_filename = "test_document.pdf"
        mock_document.storage_path = "123/test-uuid.pdf"
        mock_document.file_type = "application/pdf"
        mock_document.file_size_kb = 100
        mock_document.uploaded_at = MagicMock()
        mock_document.updated_at = MagicMock()

        mock_repository.create.return_value = mock_document

        # Mock TagService
        mock_tag_service = AsyncMock()
        mock_tag1 = MagicMock()
        mock_tag1.tag_id = 1
        mock_tag1.name = "machine learning"
        mock_tag2 = MagicMock()
        mock_tag2.tag_id = 2
        mock_tag2.name = "deep learning"
        mock_tag_service.attach_tags_to_document.return_value = [mock_tag1, mock_tag2]

        # Mock DB session (commit/rollback은 async 메서드)
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        # DocumentService 생성
        document_service = DocumentService(mock_repository, db=mock_db)
        document_service.tag_service = mock_tag_service

        # Mock 주입
        with patch('src.domains.documents.service.minio_client', mock_minio_client), \
             patch('src.domains.documents.service.text_extractor', mock_text_extractor), \
             patch('src.domains.documents.service.elasticsearch_client', mock_elasticsearch_client), \
             patch('src.domains.documents.service.keyword_extraction_service', mock_keyword_extraction_service):

            # 테스트 실행
            document, tags, extraction_method = await document_service.upload_document(
                user_id=123,
                file=mock_upload_file
            )

        # 검증: MinIO 업로드 호출됨 (실제로는 Mock이므로 업로드 안됨)
        assert mock_minio_client.upload_file.called

        # 검증: PostgreSQL 저장됨
        assert mock_repository.create.called
        assert document.document_id == 1
        assert document.user_id == 123

        # 검증: Elasticsearch 색인됨 (실제로는 Mock이므로 색인 안됨)
        assert mock_elasticsearch_client.index_document.called

        # 검증: 키워드 추출됨
        assert mock_keyword_extraction_service.extract_keywords.called
        assert extraction_method == "keybert"

        # 검증: 태그 생성됨
        assert mock_tag_service.attach_tags_to_document.called
        assert len(tags) == 2
        assert tags[0].name == "machine learning"

    @pytest.mark.asyncio
    async def test_upload_document_invalid_file_type(self, mock_upload_file):
        """허용되지 않은 파일 형식 업로드 테스트"""
        # 잘못된 파일 타입 설정
        mock_upload_file.content_type = "image/png"

        mock_repository = AsyncMock()

        # Mock DB session
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        document_service = DocumentService(mock_repository, db=mock_db)

        # HTTPException 발생 확인
        with pytest.raises(HTTPException) as exc_info:
            await document_service.upload_document(
                user_id=123,
                file=mock_upload_file
            )

        assert exc_info.value.status_code == 400
        assert "지원하지 않는 파일 형식" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_upload_hwp_document(
        self,
        mock_minio_client,
        mock_elasticsearch_client,
        mock_text_extractor,
        mock_keyword_extraction_service,
    ):
        """HWP 파일 업로드 테스트"""
        from unittest.mock import AsyncMock, MagicMock

        # HWP Mock 파일 생성
        mock_hwp_file = MagicMock()
        mock_hwp_file.filename = "test_document.hwp"
        mock_hwp_file.content_type = "application/x-hwp"
        mock_hwp_file.read = AsyncMock(return_value=b"HWP test content")

        # Mock DocumentRepository
        mock_repository = AsyncMock()

        # Mock Document 객체
        mock_document = MagicMock()
        mock_document.document_id = 1
        mock_document.user_id = 123
        mock_document.original_filename = "test_document.hwp"
        mock_document.storage_path = "123/test-uuid.hwp"
        mock_document.file_type = "application/x-hwp"
        mock_document.file_size_kb = 50
        mock_document.uploaded_at = MagicMock()
        mock_document.updated_at = MagicMock()

        mock_repository.create.return_value = mock_document

        # Mock TagService
        mock_tag_service = AsyncMock()
        mock_tag1 = MagicMock()
        mock_tag1.tag_id = 1
        mock_tag1.name = "문서"
        mock_tag2 = MagicMock()
        mock_tag2.tag_id = 2
        mock_tag2.name = "한글"
        mock_tag_service.attach_tags_to_document.return_value = [mock_tag1, mock_tag2]

        # Mock DB session
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        # DocumentService 생성
        document_service = DocumentService(mock_repository, db=mock_db)
        document_service.tag_service = mock_tag_service

        # Mock 주입
        with patch('src.domains.documents.service.minio_client', mock_minio_client), \
             patch('src.domains.documents.service.text_extractor', mock_text_extractor), \
             patch('src.domains.documents.service.elasticsearch_client', mock_elasticsearch_client), \
             patch('src.domains.documents.service.keyword_extraction_service', mock_keyword_extraction_service):

            # 테스트 실행
            document, tags, extraction_method = await document_service.upload_document(
                user_id=123,
                file=mock_hwp_file
            )

        # 검증
        assert mock_minio_client.upload_file.called
        assert mock_repository.create.called
        assert document.document_id == 1
        assert document.file_type == "application/x-hwp"
        assert mock_elasticsearch_client.index_document.called
        assert len(tags) == 2

    @pytest.mark.asyncio
    async def test_upload_document_empty_text(
        self,
        mock_minio_client,
        mock_text_extractor,
        mock_upload_file
    ):
        """텍스트 추출 실패 시 태그 생성 건너뛰기 테스트"""
        # 빈 텍스트 반환 설정
        mock_text_extractor.extract_text_from_bytes.return_value = ""

        mock_repository = AsyncMock()

        # Mock Document 객체
        mock_document = MagicMock()
        mock_document.document_id = 1
        mock_document.user_id = 123
        mock_document.original_filename = "empty.pdf"
        mock_document.storage_path = "123/empty-uuid.pdf"
        mock_document.file_type = "application/pdf"
        mock_document.file_size_kb = 10

        mock_repository.create.return_value = mock_document

        # Mock DB session
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        document_service = DocumentService(mock_repository, db=mock_db)

        with patch('src.domains.documents.service.minio_client', mock_minio_client), \
             patch('src.domains.documents.service.text_extractor', mock_text_extractor):

            document, tags, extraction_method = await document_service.upload_document(
                user_id=123,
                file=mock_upload_file
            )

        # 검증: 태그가 생성되지 않음
        assert len(tags) == 0
        assert extraction_method == "none"


class TestDocumentServiceRetrieval:
    """문서 조회 서비스 테스트"""

    @pytest.mark.asyncio
    async def test_get_user_documents(self):
        """사용자 문서 목록 조회 테스트"""
        mock_repository = AsyncMock()

        # Mock Document 객체들
        mock_doc1 = MagicMock()
        mock_doc1.document_id = 1
        mock_doc1.user_id = 123
        mock_doc1.original_filename = "doc1.pdf"
        mock_doc1.storage_path = "123/uuid1.pdf"
        mock_doc1.file_type = "application/pdf"
        mock_doc1.file_size_kb = 100

        mock_doc2 = MagicMock()
        mock_doc2.document_id = 2
        mock_doc2.user_id = 123
        mock_doc2.original_filename = "doc2.docx"
        mock_doc2.storage_path = "123/uuid2.docx"
        mock_doc2.file_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        mock_doc2.file_size_kb = 200

        mock_documents = [mock_doc1, mock_doc2]
        mock_repository.find_all_by_user_id.return_value = mock_documents

        document_service = DocumentService(mock_repository)

        documents = await document_service.get_user_documents(user_id=123)

        assert len(documents) == 2
        assert documents[0].document_id == 1
        assert documents[1].document_id == 2
        assert mock_repository.find_all_by_user_id.called

    @pytest.mark.asyncio
    async def test_get_document_by_id(self):
        """문서 상세 조회 테스트"""
        mock_repository = AsyncMock()

        # Mock Document 객체
        mock_document = MagicMock()
        mock_document.document_id = 1
        mock_document.user_id = 123
        mock_document.original_filename = "test.pdf"
        mock_document.storage_path = "123/uuid.pdf"
        mock_document.file_type = "application/pdf"
        mock_document.file_size_kb = 150

        mock_repository.find_by_id_and_user_id.return_value = mock_document

        document_service = DocumentService(mock_repository)

        document = await document_service.get_document_by_id(
            document_id=1,
            user_id=123
        )

        assert document.document_id == 1
        assert document.user_id == 123
        assert mock_repository.find_by_id_and_user_id.called


class TestDocumentServiceDeletion:
    """문서 삭제 서비스 테스트"""

    @pytest.mark.asyncio
    async def test_delete_document_success(self, mock_minio_client):
        """문서 삭제 성공 테스트 (실제 MinIO 삭제 없음)"""
        mock_repository = AsyncMock()

        # Mock Document 객체
        mock_document = MagicMock()
        mock_document.document_id = 1
        mock_document.user_id = 123
        mock_document.original_filename = "to_delete.pdf"
        mock_document.storage_path = "123/to-delete-uuid.pdf"
        mock_document.file_type = "application/pdf"
        mock_document.file_size_kb = 100

        mock_repository.find_by_id_and_user_id.return_value = mock_document
        mock_repository.delete.return_value = True

        document_service = DocumentService(mock_repository)

        with patch('src.domains.documents.service.minio_client', mock_minio_client):
            success = await document_service.delete_document(
                document_id=1,
                user_id=123
            )

        assert success is True
        assert mock_minio_client.delete_file.called
        assert mock_repository.delete.called

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self):
        """존재하지 않는 문서 삭제 시도 테스트"""
        mock_repository = AsyncMock()
        mock_repository.find_by_id_and_user_id.return_value = None

        document_service = DocumentService(mock_repository)

        with pytest.raises(HTTPException) as exc_info:
            await document_service.delete_document(
                document_id=999,
                user_id=123
            )

        assert exc_info.value.status_code == 404
        assert "문서를 찾을 수 없습니다" in exc_info.value.detail
