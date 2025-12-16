# -*- coding: utf-8 -*-
"""Document 검색 API 통합 테스트 (FastAPI TestClient 사용)"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime

from src.main import app
from src.domains.documents.models import Document
from src.domains.tags.models import Tag, DocumentTag
from src.core.security import get_current_session_data, get_current_user_id


# 테스트용 인증 override 함수
async def override_get_current_session_data():
    """테스트용 세션 데이터 반환"""
    return {"user_id": 123}


async def override_get_current_user_id():
    """테스트용 user_id 반환"""
    return 123


class TestDocumentSearchFilenameAPI:
    """파일명 검색 API 엔드포인트 테스트"""

    def test_search_by_filename_success(self):
        """파일명 검색 API 성공 테스트"""
        # Dependency override 설정
        app.dependency_overrides[get_current_session_data] = override_get_current_session_data
        app.dependency_overrides[get_current_user_id] = override_get_current_user_id

        client = TestClient(app)

        # Mock 데이터
        mock_document = MagicMock(spec=Document)
        mock_document.document_id = 1
        mock_document.original_filename = "annual_report_2024.pdf"
        mock_document.file_type = "application/pdf"
        mock_document.file_size_kb = 2048
        mock_document.summary = "2024년도 연간 보고서입니다."
        mock_document.uploaded_at = datetime(2024, 1, 15, 10, 30, 0)
        mock_document.updated_at = datetime(2024, 1, 15, 10, 30, 0)

        # Mock Tag
        mock_tag = MagicMock(spec=Tag)
        mock_tag.tag_id = 5
        mock_tag.name = "보고서"

        mock_doc_tag = MagicMock(spec=DocumentTag)
        mock_doc_tag.tag = mock_tag

        mock_document.document_tags = [mock_doc_tag]

        # Mock Service
        with patch('src.domains.documents.service.DocumentService.search_documents_by_filename',
                   new_callable=AsyncMock) as mock_search:

            mock_search.return_value = [mock_document]

            # API 호출
            response = client.get(
                "/api/v1/documents/search/filename",
                params={"query": "report"}
            )

        # Dependency override 정리
        app.dependency_overrides.clear()

        # 검증
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "report"
        assert data["total"] == 1
        assert len(data["documents"]) == 1
        assert data["documents"][0]["document_id"] == 1
        assert data["documents"][0]["original_filename"] == "annual_report_2024.pdf"
        assert len(data["documents"][0]["tags"]) == 1
        assert data["documents"][0]["tags"][0]["name"] == "보고서"

    def test_search_by_filename_no_results(self):
        """파일명 검색 API 결과 없음 테스트"""
        # Dependency override 설정
        app.dependency_overrides[get_current_session_data] = override_get_current_session_data
        app.dependency_overrides[get_current_user_id] = override_get_current_user_id

        client = TestClient(app)

        # Mock Service (빈 결과)
        with patch('src.domains.documents.service.DocumentService.search_documents_by_filename',
                   new_callable=AsyncMock) as mock_search:

            mock_search.return_value = []

            # API 호출
            response = client.get(
                "/api/v1/documents/search/filename",
                params={"query": "nonexistent"}
            )

        # Dependency override 정리
        app.dependency_overrides.clear()

        # 검증
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "nonexistent"
        assert data["total"] == 0
        assert len(data["documents"]) == 0

    def test_search_by_filename_unauthorized(self):
        """파일명 검색 API 인증 실패 테스트"""
        # Dependency override 설정하지 않음 (인증 실패 테스트)
        client = TestClient(app)

        # API 호출
        response = client.get(
            "/api/v1/documents/search/filename",
            params={"query": "report"}
        )

        # 검증 (인증 실패)
        assert response.status_code == 401

    def test_search_by_filename_multiple_results(self):
        """파일명 검색 API 다중 결과 테스트"""
        # Dependency override 설정
        app.dependency_overrides[get_current_session_data] = override_get_current_session_data
        app.dependency_overrides[get_current_user_id] = override_get_current_user_id

        client = TestClient(app)

        # Mock 데이터 (여러 문서)
        mock_doc1 = MagicMock(spec=Document)
        mock_doc1.document_id = 1
        mock_doc1.original_filename = "report_2024.pdf"
        mock_doc1.file_type = "application/pdf"
        mock_doc1.file_size_kb = 2048
        mock_doc1.summary = "2024년 보고서"
        mock_doc1.uploaded_at = datetime(2024, 1, 15, 10, 30, 0)
        mock_doc1.updated_at = datetime(2024, 1, 15, 10, 30, 0)
        mock_doc1.document_tags = []

        mock_doc2 = MagicMock(spec=Document)
        mock_doc2.document_id = 2
        mock_doc2.original_filename = "monthly_report.xlsx"
        mock_doc2.file_type = "application/vnd.ms-excel"
        mock_doc2.file_size_kb = 512
        mock_doc2.summary = "월간 보고서"
        mock_doc2.uploaded_at = datetime(2024, 2, 1, 9, 0, 0)
        mock_doc2.updated_at = datetime(2024, 2, 1, 9, 0, 0)
        mock_doc2.document_tags = []

        # Mock Service
        with patch('src.domains.documents.service.DocumentService.search_documents_by_filename',
                   new_callable=AsyncMock) as mock_search:

            mock_search.return_value = [mock_doc1, mock_doc2]

            # API 호출
            response = client.get(
                "/api/v1/documents/search/filename",
                params={"query": "report"}
            )

        # Dependency override 정리
        app.dependency_overrides.clear()

        # 검증
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["documents"]) == 2


class TestDocumentSearchTagsAPI:
    """태그 검색 API 엔드포인트 테스트"""

    def test_search_by_tags_single_tag(self):
        """단일 태그 검색 API 테스트"""
        # Dependency override 설정
        app.dependency_overrides[get_current_session_data] = override_get_current_session_data
        app.dependency_overrides[get_current_user_id] = override_get_current_user_id

        client = TestClient(app)

        # Mock 데이터
        mock_document = MagicMock(spec=Document)
        mock_document.document_id = 10
        mock_document.original_filename = "fastapi_tutorial.pdf"
        mock_document.file_type = "application/pdf"
        mock_document.file_size_kb = 1024
        mock_document.summary = "FastAPI 튜토리얼"
        mock_document.uploaded_at = datetime(2024, 3, 10, 14, 20, 0)
        mock_document.updated_at = datetime(2024, 3, 10, 14, 20, 0)

        # Mock Tag
        mock_tag = MagicMock(spec=Tag)
        mock_tag.tag_id = 15
        mock_tag.name = "python"

        mock_doc_tag = MagicMock(spec=DocumentTag)
        mock_doc_tag.tag = mock_tag

        mock_document.document_tags = [mock_doc_tag]

        # Mock Service
        with patch('src.domains.documents.service.DocumentService.search_documents_by_tags',
                   new_callable=AsyncMock) as mock_search:

            mock_search.return_value = [mock_document]

            # API 호출
            response = client.get(
                "/api/v1/documents/search/tags",
                params={"tags": "python"}
            )

        # Dependency override 정리
        app.dependency_overrides.clear()

        # 검증
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "python"
        assert data["total"] == 1
        assert len(data["documents"]) == 1
        assert data["documents"][0]["document_id"] == 10
        assert len(data["documents"][0]["tags"]) == 1
        assert data["documents"][0]["tags"][0]["name"] == "python"

    def test_search_by_tags_multiple_tags(self):
        """다중 태그 검색 API 테스트"""
        # Dependency override 설정
        app.dependency_overrides[get_current_session_data] = override_get_current_session_data
        app.dependency_overrides[get_current_user_id] = override_get_current_user_id

        client = TestClient(app)

        # Mock 데이터
        mock_document = MagicMock(spec=Document)
        mock_document.document_id = 10
        mock_document.original_filename = "fastapi_tutorial.pdf"
        mock_document.file_type = "application/pdf"
        mock_document.file_size_kb = 1024
        mock_document.summary = "FastAPI 튜토리얼"
        mock_document.uploaded_at = datetime(2024, 3, 10, 14, 20, 0)
        mock_document.updated_at = datetime(2024, 3, 10, 14, 20, 0)

        # Mock Tags
        mock_tag1 = MagicMock(spec=Tag)
        mock_tag1.tag_id = 15
        mock_tag1.name = "python"

        mock_tag2 = MagicMock(spec=Tag)
        mock_tag2.tag_id = 23
        mock_tag2.name = "fastapi"

        mock_doc_tag1 = MagicMock(spec=DocumentTag)
        mock_doc_tag1.tag = mock_tag1

        mock_doc_tag2 = MagicMock(spec=DocumentTag)
        mock_doc_tag2.tag = mock_tag2

        mock_document.document_tags = [mock_doc_tag1, mock_doc_tag2]

        # Mock Service
        with patch('src.domains.documents.service.DocumentService.search_documents_by_tags',
                   new_callable=AsyncMock) as mock_search:

            mock_search.return_value = [mock_document]

            # API 호출 (쉼표로 구분된 여러 태그)
            response = client.get(
                "/api/v1/documents/search/tags",
                params={"tags": "python,fastapi"}
            )

        # Dependency override 정리
        app.dependency_overrides.clear()

        # 검증
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "python,fastapi"
        assert data["total"] == 1
        assert len(data["documents"]) == 1
        assert len(data["documents"][0]["tags"]) == 2

    def test_search_by_tags_no_results(self):
        """태그 검색 API 결과 없음 테스트"""
        # Dependency override 설정
        app.dependency_overrides[get_current_session_data] = override_get_current_session_data
        app.dependency_overrides[get_current_user_id] = override_get_current_user_id

        client = TestClient(app)

        # Mock Service (빈 결과)
        with patch('src.domains.documents.service.DocumentService.search_documents_by_tags',
                   new_callable=AsyncMock) as mock_search:

            mock_search.return_value = []

            # API 호출
            response = client.get(
                "/api/v1/documents/search/tags",
                params={"tags": "nonexistent_tag"}
            )

        # Dependency override 정리
        app.dependency_overrides.clear()

        # 검증
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "nonexistent_tag"
        assert data["total"] == 0
        assert len(data["documents"]) == 0

    def test_search_by_tags_with_spaces(self):
        """태그 검색 API 공백 포함 태그 테스트"""
        # Dependency override 설정
        app.dependency_overrides[get_current_session_data] = override_get_current_session_data
        app.dependency_overrides[get_current_user_id] = override_get_current_user_id

        client = TestClient(app)

        # Mock Service
        with patch('src.domains.documents.service.DocumentService.search_documents_by_tags',
                   new_callable=AsyncMock) as mock_search:

            mock_search.return_value = []

            # API 호출 (공백 포함)
            response = client.get(
                "/api/v1/documents/search/tags",
                params={"tags": "python, fastapi, 웹개발"}
            )

        # Dependency override 정리
        app.dependency_overrides.clear()

        # 검증
        assert response.status_code == 200
        # Service가 공백이 제거된 태그 리스트로 호출되었는지 확인
        mock_search.assert_called_once()
        call_args = mock_search.call_args
        assert call_args.kwargs["tag_names"] == ["python", "fastapi", "웹개발"]


class TestDocumentSearchIntegration:
    """검색 API 통합 시나리오 테스트"""

    def test_search_workflow_filename_then_tags(self):
        """파일명 검색 후 태그 검색 워크플로우 테스트"""
        # Dependency override 설정
        app.dependency_overrides[get_current_session_data] = override_get_current_session_data
        app.dependency_overrides[get_current_user_id] = override_get_current_user_id

        client = TestClient(app)

        # 1. 파일명으로 검색
        with patch('src.domains.documents.service.DocumentService.search_documents_by_filename',
                   new_callable=AsyncMock) as mock_filename_search:

            mock_filename_search.return_value = []

            response1 = client.get(
                "/api/v1/documents/search/filename",
                params={"query": "report"}
            )

        assert response1.status_code == 200

        # 2. 태그로 검색
        with patch('src.domains.documents.service.DocumentService.search_documents_by_tags',
                   new_callable=AsyncMock) as mock_tags_search:

            mock_tags_search.return_value = []

            response2 = client.get(
                "/api/v1/documents/search/tags",
                params={"tags": "python"}
            )

        # Dependency override 정리
        app.dependency_overrides.clear()

        assert response2.status_code == 200
