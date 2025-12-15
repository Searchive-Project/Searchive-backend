# -*- coding: utf-8 -*-
"""Document 검색 API 단위 테스트"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from src.domains.documents.service import DocumentService
from src.domains.documents.repository import DocumentRepository


class TestDocumentSearchByFilename:
    """파일명으로 문서 검색 테스트"""

    @pytest.mark.asyncio
    async def test_search_by_filename_success(self):
        """파일명 검색 성공 테스트"""
        # Mock Repository
        mock_repository = AsyncMock()

        # Mock Document 객체
        mock_document = MagicMock()
        mock_document.document_id = 1
        mock_document.user_id = 123
        mock_document.original_filename = "annual_report_2024.pdf"
        mock_document.storage_path = "123/test-uuid.pdf"
        mock_document.file_type = "application/pdf"
        mock_document.file_size_kb = 2048
        mock_document.summary = "2024년도 연간 보고서입니다."
        mock_document.uploaded_at = datetime.now()
        mock_document.updated_at = datetime.now()
        mock_document.document_tags = []

        mock_repository.find_by_id_and_user_id.return_value = mock_document

        # Mock Elasticsearch 검색 결과
        mock_es_results = [
            {
                "document_id": 1,
                "filename": "annual_report_2024.pdf",
                "file_type": "application/pdf",
                "uploaded_at": "2024-01-15T10:30:00",
                "score": 1.5
            }
        ]

        # Service 생성
        service = DocumentService(mock_repository, db=MagicMock())

        # Elasticsearch 클라이언트 Mock
        with patch('src.domains.documents.service.elasticsearch_client') as mock_es:
            mock_es.search_documents_by_filename = AsyncMock(return_value=mock_es_results)

            # 파일명 검색 실행
            documents = await service.search_documents_by_filename(
                user_id=123,
                query="report"
            )

        # 검증
        assert len(documents) == 1
        assert documents[0].document_id == 1
        assert documents[0].original_filename == "annual_report_2024.pdf"
        mock_es.search_documents_by_filename.assert_called_once_with(
            user_id=123,
            query="report"
        )

    @pytest.mark.asyncio
    async def test_search_by_filename_no_results(self):
        """파일명 검색 결과 없음 테스트"""
        # Mock Repository
        mock_repository = AsyncMock()

        # Service 생성
        service = DocumentService(mock_repository, db=MagicMock())

        # Elasticsearch 클라이언트 Mock (빈 결과)
        with patch('src.domains.documents.service.elasticsearch_client') as mock_es:
            mock_es.search_documents_by_filename = AsyncMock(return_value=[])

            # 파일명 검색 실행
            documents = await service.search_documents_by_filename(
                user_id=123,
                query="nonexistent"
            )

        # 검증
        assert len(documents) == 0
        mock_es.search_documents_by_filename.assert_called_once_with(
            user_id=123,
            query="nonexistent"
        )

    @pytest.mark.asyncio
    async def test_search_by_filename_multiple_results(self):
        """파일명 검색 다중 결과 테스트"""
        # Mock Repository
        mock_repository = AsyncMock()

        # Mock Document 객체들
        mock_doc1 = MagicMock()
        mock_doc1.document_id = 1
        mock_doc1.original_filename = "report_2024.pdf"
        mock_doc1.document_tags = []

        mock_doc2 = MagicMock()
        mock_doc2.document_id = 2
        mock_doc2.original_filename = "monthly_report.xlsx"
        mock_doc2.document_tags = []

        # Repository Mock 설정 (document_id에 따라 다른 문서 반환)
        def mock_find_by_id(document_id, user_id):
            if document_id == 1:
                return mock_doc1
            elif document_id == 2:
                return mock_doc2
            return None

        mock_repository.find_by_id_and_user_id.side_effect = mock_find_by_id

        # Mock Elasticsearch 검색 결과
        mock_es_results = [
            {"document_id": 1, "filename": "report_2024.pdf", "file_type": "application/pdf", "uploaded_at": "2024-01-15T10:30:00", "score": 1.5},
            {"document_id": 2, "filename": "monthly_report.xlsx", "file_type": "application/vnd.ms-excel", "uploaded_at": "2024-02-01T09:00:00", "score": 1.2}
        ]

        # Service 생성
        service = DocumentService(mock_repository, db=MagicMock())

        # Elasticsearch 클라이언트 Mock
        with patch('src.domains.documents.service.elasticsearch_client') as mock_es:
            mock_es.search_documents_by_filename = AsyncMock(return_value=mock_es_results)

            # 파일명 검색 실행
            documents = await service.search_documents_by_filename(
                user_id=123,
                query="report"
            )

        # 검증
        assert len(documents) == 2
        assert documents[0].document_id == 1
        assert documents[1].document_id == 2


class TestDocumentSearchByTags:
    """태그로 문서 검색 테스트"""

    @pytest.mark.asyncio
    async def test_search_by_tags_single_tag(self):
        """단일 태그 검색 테스트"""
        # Mock Repository
        mock_repository = AsyncMock()

        # Mock Document 객체
        mock_document = MagicMock()
        mock_document.document_id = 10
        mock_document.user_id = 123
        mock_document.original_filename = "fastapi_tutorial.pdf"
        mock_document.storage_path = "123/test-uuid.pdf"
        mock_document.file_type = "application/pdf"
        mock_document.file_size_kb = 1024
        mock_document.summary = "FastAPI 프레임워크 튜토리얼 문서입니다."
        mock_document.uploaded_at = datetime.now()
        mock_document.updated_at = datetime.now()

        # Mock Tag
        mock_tag = MagicMock()
        mock_tag.tag_id = 15
        mock_tag.name = "python"

        mock_document.document_tags = [MagicMock(tag=mock_tag)]

        # Repository Mock 설정
        mock_repository.find_by_tag_names.return_value = [mock_document]

        # Service 생성
        service = DocumentService(mock_repository, db=MagicMock())

        # 태그 검색 실행
        documents = await service.search_documents_by_tags(
            user_id=123,
            tag_names=["python"]
        )

        # 검증
        assert len(documents) == 1
        assert documents[0].document_id == 10
        assert documents[0].original_filename == "fastapi_tutorial.pdf"
        mock_repository.find_by_tag_names.assert_called_once_with(
            user_id=123,
            tag_names=["python"]
        )

    @pytest.mark.asyncio
    async def test_search_by_tags_multiple_tags(self):
        """다중 태그 검색 테스트 (OR 조건)"""
        # Mock Repository
        mock_repository = AsyncMock()

        # Mock Document 객체들
        mock_doc1 = MagicMock()
        mock_doc1.document_id = 10
        mock_doc1.original_filename = "fastapi_tutorial.pdf"
        mock_doc1.document_tags = []

        mock_doc2 = MagicMock()
        mock_doc2.document_id = 15
        mock_doc2.original_filename = "python_best_practices.docx"
        mock_doc2.document_tags = []

        # Repository Mock 설정
        mock_repository.find_by_tag_names.return_value = [mock_doc1, mock_doc2]

        # Service 생성
        service = DocumentService(mock_repository, db=MagicMock())

        # 태그 검색 실행 (여러 태그)
        documents = await service.search_documents_by_tags(
            user_id=123,
            tag_names=["python", "fastapi"]
        )

        # 검증
        assert len(documents) == 2
        assert documents[0].document_id == 10
        assert documents[1].document_id == 15
        mock_repository.find_by_tag_names.assert_called_once_with(
            user_id=123,
            tag_names=["python", "fastapi"]
        )

    @pytest.mark.asyncio
    async def test_search_by_tags_no_results(self):
        """태그 검색 결과 없음 테스트"""
        # Mock Repository
        mock_repository = AsyncMock()

        # Repository Mock 설정 (빈 결과)
        mock_repository.find_by_tag_names.return_value = []

        # Service 생성
        service = DocumentService(mock_repository, db=MagicMock())

        # 태그 검색 실행
        documents = await service.search_documents_by_tags(
            user_id=123,
            tag_names=["nonexistent_tag"]
        )

        # 검증
        assert len(documents) == 0
        mock_repository.find_by_tag_names.assert_called_once_with(
            user_id=123,
            tag_names=["nonexistent_tag"]
        )


class TestElasticsearchFilenameSearch:
    """Elasticsearch 파일명 검색 클라이언트 테스트"""

    @pytest.mark.asyncio
    async def test_elasticsearch_search_documents_by_filename(self):
        """Elasticsearch 파일명 검색 기능 테스트"""
        from src.core.elasticsearch_client import ElasticsearchClient

        # Mock Elasticsearch 클라이언트
        mock_es_client = AsyncMock()

        # Mock 검색 결과
        mock_search_result = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "document_id": 1,
                            "filename": "report_2024.pdf",
                            "file_type": "application/pdf",
                            "uploaded_at": "2024-01-15T10:30:00"
                        },
                        "_score": 1.5
                    }
                ]
            }
        }

        mock_es_client.search.return_value = mock_search_result

        # ElasticsearchClient 인스턴스 생성
        es_client = ElasticsearchClient()
        es_client.client = mock_es_client

        # 파일명 검색 실행
        results = await es_client.search_documents_by_filename(
            user_id=123,
            query="report",
            size=10
        )

        # 검증
        assert len(results) == 1
        assert results[0]["document_id"] == 1
        assert results[0]["filename"] == "report_2024.pdf"
        assert results[0]["score"] == 1.5

        # search 메서드가 올바른 인자로 호출되었는지 확인
        mock_es_client.search.assert_called_once()
        call_args = mock_es_client.search.call_args
        assert call_args.kwargs["size"] == 10


class TestRepositoryTagSearch:
    """Repository 태그 검색 테스트"""

    @pytest.mark.asyncio
    async def test_repository_find_by_tag_names(self):
        """Repository 태그 이름으로 문서 검색 테스트"""
        # Mock Repository 직접 테스트 대신 Service 레벨에서 테스트
        mock_repository = AsyncMock()

        # Mock Document 객체
        mock_document = MagicMock()
        mock_document.document_id = 1
        mock_document.original_filename = "test.pdf"
        mock_document.document_tags = []

        # Repository Mock 설정
        mock_repository.find_by_tag_names.return_value = [mock_document]

        # Service 생성
        service = DocumentService(mock_repository, db=MagicMock())

        # 태그로 검색
        documents = await service.search_documents_by_tags(
            user_id=123,
            tag_names=["python", "fastapi"]
        )

        # 검증
        assert len(documents) == 1
        assert documents[0].document_id == 1
        mock_repository.find_by_tag_names.assert_called_once_with(
            user_id=123,
            tag_names=["python", "fastapi"]
        )
