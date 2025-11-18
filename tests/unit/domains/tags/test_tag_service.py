# -*- coding: utf-8 -*-
"""Tag Service 단위 테스트"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.domains.tags.service import TagService
from src.domains.tags.models import Tag


class TestTagServiceGetOrCreate:
    """태그 조회 또는 생성 테스트"""

    @pytest.mark.asyncio
    async def test_get_or_create_tag_existing(self):
        """기존 태그 조회 테스트"""
        # Mock Repository
        mock_tag_repository = AsyncMock()

        # Mock Tag 객체
        existing_tag = MagicMock()
        existing_tag.tag_id = 1
        existing_tag.name = "python"
        mock_tag_repository.get_or_create.return_value = existing_tag

        mock_document_tag_repository = AsyncMock()

        # Mock DB session
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        # TagService 생성
        tag_service = TagService(db=mock_db)
        tag_service.tag_repository = mock_tag_repository
        tag_service.document_tag_repository = mock_document_tag_repository

        # 테스트 실행
        tag = await tag_service.get_or_create_tag("python")

        # 검증
        assert tag.tag_id == 1
        assert tag.name == "python"
        assert mock_tag_repository.get_or_create.called

    @pytest.mark.asyncio
    async def test_get_or_create_tags_bulk(self):
        """여러 태그 일괄 조회/생성 테스트 (N+1 방지)"""
        from unittest.mock import patch

        # Mock Repository
        mock_tag_repository = AsyncMock()

        # Mock Tag 객체들
        mock_tag1 = MagicMock()
        mock_tag1.tag_id = 1
        mock_tag1.name = "Python"
        mock_tag2 = MagicMock()
        mock_tag2.tag_id = 2
        mock_tag2.name = "Fastapi"
        mock_tag3 = MagicMock()
        mock_tag3.tag_id = 3
        mock_tag3.name = "Redis"

        # find_by_name이 순서대로 각 태그를 반환하도록 설정
        mock_tag_repository.find_by_name.side_effect = [mock_tag1, mock_tag2, mock_tag3]

        mock_document_tag_repository = AsyncMock()

        # Mock DB session
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        # TagService 생성
        tag_service = TagService(db=mock_db)
        tag_service.tag_repository = mock_tag_repository
        tag_service.document_tag_repository = mock_document_tag_repository

        # elasticsearch_client.search_similar_tags_batch mock
        with patch('src.core.elasticsearch_client.elasticsearch_client') as mock_es, \
             patch('src.core.embedding_service.embedding_service') as mock_embedding:
            # AsyncMock을 사용하여 await 가능하도록 설정
            mock_es.search_similar_tags_batch = AsyncMock(return_value=[[], [], []])  # 유사 태그 없음

            # embedding_service.encode()가 numpy array처럼 동작하도록 설정
            mock_embedding_result = MagicMock()
            mock_embedding_result.tolist.return_value = [0.1, 0.2, 0.3]
            mock_embedding.encode.return_value = mock_embedding_result

            # 테스트 실행
            tag_names = ["python", "fastapi", "redis"]
            tags = await tag_service.get_or_create_tags(tag_names)

        # 검증
        assert len(tags) == 3
        assert tags[0].name == "Python"
        assert tags[1].name == "Fastapi"
        assert tags[2].name == "Redis"
        assert mock_tag_repository.find_by_name.called

    @pytest.mark.asyncio
    async def test_get_or_create_tags_with_duplicates(self):
        """중복 태그 이름으로 조회 시 중복 제거 테스트"""
        # Mock Repository
        mock_tag_repository = AsyncMock()

        # Mock Tag 객체들
        mock_tag1 = MagicMock()
        mock_tag1.tag_id = 1
        mock_tag1.name = "python"
        mock_tag2 = MagicMock()
        mock_tag2.tag_id = 2
        mock_tag2.name = "fastapi"
        mock_tags = [mock_tag1, mock_tag2]
        mock_tag_repository.bulk_get_or_create.return_value = mock_tags

        mock_document_tag_repository = AsyncMock()

        # Mock DB session
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        # TagService 생성
        tag_service = TagService(db=mock_db)
        tag_service.tag_repository = mock_tag_repository
        tag_service.document_tag_repository = mock_document_tag_repository

        # 중복 포함된 태그 이름 리스트
        tag_names = ["python", "Python", "PYTHON", "fastapi", "FastAPI"]
        tags = await tag_service.get_or_create_tags(tag_names)

        # 검증: 중복 제거되어 2개만 조회됨
        assert len(tags) == 2

    @pytest.mark.asyncio
    async def test_get_or_create_tags_empty_list(self):
        """빈 태그 리스트 처리 테스트"""
        # Mock Repository
        mock_tag_repository = AsyncMock()
        mock_document_tag_repository = AsyncMock()

        # Mock DB session
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        # TagService 생성
        tag_service = TagService(db=mock_db)
        tag_service.tag_repository = mock_tag_repository
        tag_service.document_tag_repository = mock_document_tag_repository

        # 빈 리스트 전달
        tags = await tag_service.get_or_create_tags([])

        # 검증: 빈 리스트 반환
        assert len(tags) == 0


class TestTagServiceAttachment:
    """태그 문서 연결 테스트"""

    @pytest.mark.asyncio
    async def test_attach_tags_to_document(self):
        """문서에 태그 연결 테스트"""
        from unittest.mock import patch

        # Mock Repository
        mock_tag_repository = AsyncMock()

        # Mock Tag 객체들
        mock_tag1 = MagicMock()
        mock_tag1.tag_id = 1
        mock_tag1.name = "Machine Learning"
        mock_tag2 = MagicMock()
        mock_tag2.tag_id = 2
        mock_tag2.name = "Deep Learning"
        mock_tag3 = MagicMock()
        mock_tag3.tag_id = 3
        mock_tag3.name = "Neural Network"

        # find_by_name이 순서대로 각 태그를 반환하도록 설정
        mock_tag_repository.find_by_name.side_effect = [mock_tag1, mock_tag2, mock_tag3]

        mock_document_tag_repository = AsyncMock()
        mock_document_tag_repository.bulk_create.return_value = [
            MagicMock(document_id=1, tag_id=1),
            MagicMock(document_id=1, tag_id=2),
            MagicMock(document_id=1, tag_id=3)
        ]

        # Mock DB session
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        # TagService 생성
        tag_service = TagService(db=mock_db)
        tag_service.tag_repository = mock_tag_repository
        tag_service.document_tag_repository = mock_document_tag_repository

        # elasticsearch_client.search_similar_tags_batch mock
        with patch('src.core.elasticsearch_client.elasticsearch_client') as mock_es, \
             patch('src.core.embedding_service.embedding_service') as mock_embedding:
            # AsyncMock을 사용하여 await 가능하도록 설정
            mock_es.search_similar_tags_batch = AsyncMock(return_value=[[], [], []])  # 유사 태그 없음

            # embedding_service.encode()가 numpy array처럼 동작하도록 설정
            mock_embedding_result = MagicMock()
            mock_embedding_result.tolist.return_value = [0.1, 0.2, 0.3]
            mock_embedding.encode.return_value = mock_embedding_result

            # 테스트 실행
            tag_names = ["machine learning", "deep learning", "neural network"]
            tags = await tag_service.attach_tags_to_document(
                document_id=1,
                tag_names=tag_names
            )

        # 검증
        assert len(tags) == 3
        assert mock_tag_repository.find_by_name.called
        assert mock_document_tag_repository.bulk_create.called

    @pytest.mark.asyncio
    async def test_attach_tags_empty_list(self):
        """빈 태그 리스트로 연결 시도 테스트"""
        # Mock Repository
        mock_tag_repository = AsyncMock()
        mock_document_tag_repository = AsyncMock()

        # Mock DB session
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        # TagService 생성
        tag_service = TagService(db=mock_db)
        tag_service.tag_repository = mock_tag_repository
        tag_service.document_tag_repository = mock_document_tag_repository

        # 빈 리스트 전달
        tags = await tag_service.attach_tags_to_document(
            document_id=1,
            tag_names=[]
        )

        # 검증: 빈 리스트 반환, Repository 호출 안됨
        assert len(tags) == 0


class TestTagServiceRetrieval:
    """태그 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_tags_by_document_id(self):
        """문서 ID로 태그 조회 테스트"""
        # Mock Repository
        mock_tag_repository = AsyncMock()
        mock_document_tag_repository = AsyncMock()

        # Mock Tag 객체들
        mock_tag1 = MagicMock()
        mock_tag1.tag_id = 1
        mock_tag1.name = "python"
        mock_tag2 = MagicMock()
        mock_tag2.tag_id = 2
        mock_tag2.name = "fastapi"
        mock_tags = [mock_tag1, mock_tag2]
        mock_document_tag_repository.find_tags_by_document_id.return_value = mock_tags

        # Mock DB session
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        # TagService 생성
        tag_service = TagService(db=mock_db)
        tag_service.tag_repository = mock_tag_repository
        tag_service.document_tag_repository = mock_document_tag_repository

        # 테스트 실행
        tags = await tag_service.get_tags_by_document_id(document_id=1)

        # 검증
        assert len(tags) == 2
        assert tags[0].name == "python"
        assert tags[1].name == "fastapi"
        assert mock_document_tag_repository.find_tags_by_document_id.called

    @pytest.mark.asyncio
    async def test_find_tag_by_name(self):
        """태그 이름으로 태그 조회 테스트"""
        # Mock Repository
        mock_tag_repository = AsyncMock()

        # Mock Tag 객체
        existing_tag = MagicMock()
        existing_tag.tag_id = 1
        existing_tag.name = "python"
        mock_tag_repository.find_by_name.return_value = existing_tag

        mock_document_tag_repository = AsyncMock()

        # Mock DB session
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        # TagService 생성
        tag_service = TagService(db=mock_db)
        tag_service.tag_repository = mock_tag_repository
        tag_service.document_tag_repository = mock_document_tag_repository

        # 테스트 실행
        tag = await tag_service.find_tag_by_name("python")

        # 검증
        assert tag.tag_id == 1
        assert tag.name == "python"
        assert mock_tag_repository.find_by_name.called

    @pytest.mark.asyncio
    async def test_find_tag_by_name_not_found(self):
        """존재하지 않는 태그 조회 테스트"""
        # Mock Repository
        mock_tag_repository = AsyncMock()
        mock_tag_repository.find_by_name.return_value = None

        mock_document_tag_repository = AsyncMock()

        # Mock DB session
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        # TagService 생성
        tag_service = TagService(db=mock_db)
        tag_service.tag_repository = mock_tag_repository
        tag_service.document_tag_repository = mock_document_tag_repository

        # 테스트 실행
        tag = await tag_service.find_tag_by_name("nonexistent")

        # 검증: None 반환
        assert tag is None
