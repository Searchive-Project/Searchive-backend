# -*- coding: utf-8 -*-
"""Tag 도메인 Repository"""
from typing import Optional, List
import numpy as np
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.domains.tags.models import Tag, DocumentTag
from src.core.elasticsearch_client import elasticsearch_client


class TagRepository:
    """Tag 엔티티 데이터 접근 계층"""

    def __init__(self, db: AsyncSession):
        """
        TagRepository 초기화

        Args:
            db: SQLAlchemy AsyncSession
        """
        self.db = db

    async def find_by_name(self, name: str) -> Optional[Tag]:
        """
        태그 이름으로 태그 조회

        Args:
            name: 태그 이름

        Returns:
            Tag 객체 또는 None
        """
        result = await self.db.execute(
            select(Tag).where(Tag.name == name)
        )
        return result.scalar_one_or_none()

    async def find_by_id(self, tag_id: int) -> Optional[Tag]:
        """
        태그 ID로 태그 조회

        Args:
            tag_id: 태그 고유 ID

        Returns:
            Tag 객체 또는 None
        """
        result = await self.db.execute(
            select(Tag).where(Tag.tag_id == tag_id)
        )
        return result.scalar_one_or_none()

    async def find_all_by_names(self, names: List[str]) -> List[Tag]:
        """
        여러 태그 이름으로 태그들을 한 번에 조회 (N+1 문제 방지)

        Args:
            names: 태그 이름 리스트

        Returns:
            Tag 객체 리스트
        """
        if not names:
            return []

        result = await self.db.execute(
            select(Tag).where(Tag.name.in_(names))
        )
        return list(result.scalars().all())

    async def create(self, name: str, embedding: Optional[np.ndarray] = None, commit: bool = True) -> Tag:
        """
        신규 태그 생성

        Args:
            name: 태그 이름
            embedding: 태그 임베딩 벡터 (선택)
            commit: 즉시 commit 여부 (기본값: True, False일 경우 Service에서 관리)

        Returns:
            생성된 Tag 객체
        """
        import logging
        logger = logging.getLogger(__name__)

        tag = Tag(name=name)
        if embedding is not None:
            tag.embedding = embedding.tolist()  # numpy array를 list로 변환
        self.db.add(tag)
        if commit:
            await self.db.commit()
            await self.db.refresh(tag)
        else:
            await self.db.flush()
            await self.db.refresh(tag)

        # Elasticsearch에 색인 (비동기)
        if embedding is not None:
            try:
                await elasticsearch_client.index_tag(
                    tag_id=tag.tag_id,
                    name=tag.name,
                    embedding=tag.embedding,
                    created_at=tag.created_at.isoformat() if tag.created_at else None
                )
                logger.info(f"[create] 태그 Elasticsearch 색인 완료: tag_id={tag.tag_id}, name={tag.name}")
            except Exception as e:
                logger.error(f"[create] 태그 Elasticsearch 색인 실패: {e}", exc_info=True)
                # Elasticsearch 색인 실패해도 PostgreSQL에는 저장되어 있으므로 계속 진행

        return tag

    async def bulk_create(self, names: List[str]) -> List[Tag]:
        """
        여러 태그를 한 번에 생성

        Args:
            names: 태그 이름 리스트

        Returns:
            생성된 Tag 객체 리스트
        """
        tags = [Tag(name=name) for name in names]
        self.db.add_all(tags)
        await self.db.commit()

        # 생성된 태그들을 refresh
        for tag in tags:
            await self.db.refresh(tag)

        return tags

    async def find_similar_tag(
        self,
        embedding: np.ndarray,
        threshold: float = 0.8,
        exclude_name: Optional[str] = None
    ) -> Optional[Tag]:
        """
        임베딩 벡터와 유사한 태그 찾기 (Elasticsearch 벡터 유사도 검색)

        Args:
            embedding: 쿼리 임베딩 벡터
            threshold: 최소 유사도 임계값 (0.0 ~ 1.0, 기본값: 0.8)
            exclude_name: 제외할 태그 이름 (선택)

        Returns:
            가장 유사한 Tag 객체 또는 None
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"[find_similar_tag] Elasticsearch 유사도 검색 시작 (threshold: {threshold})")

        try:
            # Elasticsearch에서 유사 태그 검색
            similar_tags = await elasticsearch_client.search_similar_tags(
                embedding=embedding.tolist(),
                threshold=threshold,
                size=1
            )

            if not similar_tags:
                logger.info(f"[find_similar_tag] 유사한 태그 없음 (threshold: {threshold})")
                return None

            # 가장 유사한 태그 (첫 번째)
            most_similar = similar_tags[0]
            tag_id = most_similar["tag_id"]
            name = most_similar["name"]
            score = most_similar["score"]

            logger.info(f"[find_similar_tag] 유사한 태그 발견: '{name}' (ID: {tag_id}, score: {score:.4f})")

            # exclude_name 체크
            if exclude_name and name == exclude_name:
                logger.info(f"[find_similar_tag] exclude_name으로 제외됨: '{name}'")
                return None

            # PostgreSQL에서 Tag 객체 조회
            tag = await self.find_by_id(tag_id)
            return tag

        except Exception as e:
            logger.error(f"[find_similar_tag] Elasticsearch 검색 실패: {e}", exc_info=True)
            return None

    async def get_or_create(
        self,
        name: str,
        embedding: Optional[np.ndarray] = None,
        similarity_threshold: float = 0.8,
        commit: bool = True
    ) -> Tag:
        """
        태그 조회 또는 생성 (Get-or-Create 패턴)
        임베딩이 제공된 경우 유사한 태그 검색 후 재사용

        Args:
            name: 태그 이름
            embedding: 태그 임베딩 벡터 (선택)
            similarity_threshold: 유사도 임계값 (기본값: 0.8)
            commit: 즉시 commit 여부 (기본값: True, False일 경우 Service에서 관리)

        Returns:
            조회되거나 생성된 Tag 객체
        """
        import logging
        logger = logging.getLogger(__name__)

        # 1. 정확히 일치하는 태그 찾기
        logger.info(f"[get_or_create] 1단계: 정확히 일치하는 태그 찾기 - '{name}'")
        tag = await self.find_by_name(name)
        if tag:
            logger.info(f"[get_or_create] ✓ 정확히 일치하는 태그 발견: '{tag.name}' (ID: {tag.tag_id})")
            return tag
        logger.info(f"[get_or_create] 정확히 일치하는 태그 없음")

        # 2. 임베딩이 제공된 경우, 유사한 태그 찾기
        if embedding is not None:
            logger.info(f"[get_or_create] 2단계: 유사한 태그 찾기 (threshold: {similarity_threshold})")

            # flush하여 현재 세션의 모든 변경사항을 DB로 전송 (commit하지 않고)
            # 이렇게 해야 raw SQL 쿼리가 아직 commit되지 않은 태그들도 볼 수 있음
            await self.db.flush()
            logger.info(f"[get_or_create] DB flush 완료 (commit 전 변경사항 동기화)")

            similar_tag = await self.find_similar_tag(
                embedding=embedding,
                threshold=similarity_threshold
            )
            if similar_tag:
                logger.info(f"[get_or_create] ✓ 유사한 태그 발견: '{similar_tag.name}' (ID: {similar_tag.tag_id})")
                return similar_tag
            logger.info(f"[get_or_create] 유사한 태그 없음")
        else:
            logger.info(f"[get_or_create] 2단계 건너뜀: 임베딩이 제공되지 않음")

        # 3. 유사한 태그가 없으면 새로 생성
        logger.info(f"[get_or_create] 3단계: 새 태그 생성 - '{name}' (commit: {commit})")
        new_tag = await self.create(name, embedding, commit=commit)
        logger.info(f"[get_or_create] ✓ 새 태그 생성 완료: '{new_tag.name}' (ID: {new_tag.tag_id})")
        return new_tag

    async def bulk_get_or_create(self, names: List[str]) -> List[Tag]:
        """
        여러 태그를 한 번에 조회 또는 생성 (N+1 문제 방지)

        Args:
            names: 태그 이름 리스트

        Returns:
            조회되거나 생성된 Tag 객체 리스트
        """
        if not names:
            return []

        # 1. 기존 태그 조회
        existing_tags = await self.find_all_by_names(names)
        existing_tag_names = {tag.name for tag in existing_tags}

        # 2. 신규 태그 이름 추출
        new_tag_names = [name for name in names if name not in existing_tag_names]

        # 3. 신규 태그 생성
        new_tags = []
        if new_tag_names:
            new_tags = await self.bulk_create(new_tag_names)

        # 4. 기존 태그 + 신규 태그 반환
        return existing_tags + new_tags


class DocumentTagRepository:
    """DocumentTag 연결 테이블 데이터 접근 계층"""

    def __init__(self, db: AsyncSession):
        """
        DocumentTagRepository 초기화

        Args:
            db: SQLAlchemy AsyncSession
        """
        self.db = db

    async def create(self, document_id: int, tag_id: int) -> DocumentTag:
        """
        문서-태그 연결 생성

        Args:
            document_id: 문서 ID
            tag_id: 태그 ID

        Returns:
            생성된 DocumentTag 객체
        """
        document_tag = DocumentTag(
            document_id=document_id,
            tag_id=tag_id
        )
        self.db.add(document_tag)
        await self.db.commit()
        await self.db.refresh(document_tag)
        return document_tag

    async def bulk_create(self, document_id: int, tag_ids: List[int], commit: bool = True) -> List[DocumentTag]:
        """
        하나의 문서에 여러 태그를 한 번에 연결 (N+1 문제 방지)

        Args:
            document_id: 문서 ID
            tag_ids: 태그 ID 리스트
            commit: 즉시 commit 여부 (기본값: True, False일 경우 Service에서 관리)

        Returns:
            생성된 DocumentTag 객체 리스트
        """
        if not tag_ids:
            return []

        document_tags = [
            DocumentTag(document_id=document_id, tag_id=tag_id)
            for tag_id in tag_ids
        ]
        self.db.add_all(document_tags)

        if commit:
            await self.db.commit()
            # refresh
            for doc_tag in document_tags:
                await self.db.refresh(doc_tag)
        else:
            await self.db.flush()
            # refresh
            for doc_tag in document_tags:
                await self.db.refresh(doc_tag)

        return document_tags

    async def find_tags_by_document_id(self, document_id: int) -> List[Tag]:
        """
        문서 ID로 연결된 모든 태그 조회 (N+1 문제 방지)

        Args:
            document_id: 문서 ID

        Returns:
            Tag 객체 리스트
        """
        result = await self.db.execute(
            select(Tag)
            .join(DocumentTag, Tag.tag_id == DocumentTag.tag_id)
            .where(DocumentTag.document_id == document_id)
        )
        return list(result.scalars().all())

    async def delete_by_document_id(self, document_id: int) -> bool:
        """
        문서 ID로 모든 문서-태그 연결 삭제

        Args:
            document_id: 문서 ID

        Returns:
            삭제 성공 여부
        """
        try:
            result = await self.db.execute(
                select(DocumentTag).where(DocumentTag.document_id == document_id)
            )
            document_tags = result.scalars().all()

            for doc_tag in document_tags:
                await self.db.delete(doc_tag)

            await self.db.commit()
            return True
        except Exception:
            await self.db.rollback()
            return False
