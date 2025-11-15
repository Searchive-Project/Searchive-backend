# -*- coding: utf-8 -*-
"""Tag 도메인 Service"""
from typing import List, Optional
import re
from sqlalchemy.ext.asyncio import AsyncSession
from src.domains.tags.repository import TagRepository, DocumentTagRepository
from src.domains.tags.models import Tag
from src.core.embedding_service import embedding_service
from src.core.keyword_extraction import is_stopword
import logging

logger = logging.getLogger(__name__)


class TagService:
    """Tag 비즈니스 로직 처리 계층"""

    def __init__(self, db: AsyncSession):
        """
        TagService 초기화

        Args:
            db: SQLAlchemy AsyncSession
        """
        self.tag_repository = TagRepository(db)
        self.document_tag_repository = DocumentTagRepository(db)

    @staticmethod
    def normalize_tag_name(name: str) -> str:
        """
        태그 이름 정규화
        - 영어: Title Case (각 단어의 첫 글자만 대문자)
        - 한글/기타: 소문자

        Args:
            name: 원본 태그 이름

        Returns:
            정규화된 태그 이름
        """
        name = name.strip()

        # 영어 알파벳과 공백, 하이픈만 포함되어 있는지 확인
        is_english = bool(re.match(r'^[a-zA-Z\s\-]+$', name))

        if is_english:
            # 영어: Title Case 적용
            return name.title()
        else:
            # 한글/기타: 소문자
            return name.lower()

    async def get_or_create_tag(
        self,
        name: str,
        similarity_threshold: float = 0.8,
        commit: bool = True
    ) -> Tag:
        """
        태그 조회 또는 생성 (임베딩 기반 유사도 검색 포함)

        Args:
            name: 태그 이름
            similarity_threshold: 유사도 임계값 (기본값: 0.8)
            commit: 즉시 commit 여부 (기본값: True, False일 경우 Service에서 관리)

        Returns:
            Tag 객체
        """
        # 임베딩 생성
        embedding = embedding_service.encode(name)

        # 임베딩 기반 Get-or-Create
        return await self.tag_repository.get_or_create(
            name=name,
            embedding=embedding,
            similarity_threshold=similarity_threshold,
            commit=commit
        )

    async def get_or_create_tags(
        self,
        names: List[str],
        similarity_threshold: float = 0.8,
        commit: bool = True
    ) -> List[Tag]:
        """
        여러 태그를 한 번에 조회 또는 생성 (임베딩 기반 유사도 검색 포함)

        Args:
            names: 태그 이름 리스트
            similarity_threshold: 유사도 임계값 (기본값: 0.8)
            commit: 즉시 commit 여부 (기본값: True, False일 경우 Service에서 관리)

        Returns:
            Tag 객체 리스트
        """
        if not names:
            return []

        # 불용어 필터링 (방어적 프로그래밍)
        valid_names = []
        for name in names:
            name_stripped = name.strip()
            if not name_stripped:
                continue
            # 불용어 체크
            if is_stopword(name_stripped):
                logger.info(f"불용어로 필터링됨: '{name_stripped}'")
                continue
            valid_names.append(name_stripped)

        if not valid_names:
            logger.warning("불용어 필터링 후 유효한 태그 이름이 없습니다.")
            return []

        # 중복 제거 및 정규화 (영어: Title Case, 한글: 소문자)
        normalized_names = [self.normalize_tag_name(name) for name in valid_names]
        unique_names = list(set(normalized_names))

        logger.info(f"태그 조회/생성 시작 (임베딩 기반): {unique_names}")

        # 각 태그에 대해 임베딩 기반 Get-or-Create 수행
        tags = []
        for name in unique_names:
            tag = await self.get_or_create_tag(
                name=name,
                similarity_threshold=similarity_threshold,
                commit=commit
            )
            tags.append(tag)

        logger.info(f"태그 조회/생성 완료: {len(tags)}개")

        return tags

    async def attach_tags_to_document(
        self,
        document_id: int,
        tag_names: List[str],
        similarity_threshold: float = 0.8,
        commit: bool = True
    ) -> List[Tag]:
        """
        문서에 태그 연결 (임베딩 기반 유사도 검색 포함)

        Args:
            document_id: 문서 ID
            tag_names: 태그 이름 리스트
            similarity_threshold: 유사도 임계값 (기본값: 0.8)
            commit: 즉시 commit 여부 (기본값: True, False일 경우 Service에서 관리)

        Returns:
            연결된 Tag 객체 리스트
        """
        if not tag_names:
            logger.info(f"문서 {document_id}에 연결할 태그 없음")
            return []

        # 1. 임베딩 기반 태그 조회 또는 생성
        tags = await self.get_or_create_tags(
            names=tag_names,
            similarity_threshold=similarity_threshold,
            commit=commit
        )

        # 2. 문서-태그 연결 생성 (N+1 문제 방지)
        tag_ids = [tag.tag_id for tag in tags]
        await self.document_tag_repository.bulk_create(document_id, tag_ids, commit=commit)

        logger.info(f"문서 {document_id}에 태그 {len(tags)}개 연결 완료: {tag_names}")

        return tags

    async def get_tags_by_document_id(self, document_id: int) -> List[Tag]:
        """
        문서 ID로 연결된 모든 태그 조회

        Args:
            document_id: 문서 ID

        Returns:
            Tag 객체 리스트
        """
        return await self.document_tag_repository.find_tags_by_document_id(document_id)

    async def find_tag_by_name(self, name: str) -> Optional[Tag]:
        """
        태그 이름으로 태그 조회

        Args:
            name: 태그 이름

        Returns:
            Tag 객체 또는 None
        """
        return await self.tag_repository.find_by_name(name)
