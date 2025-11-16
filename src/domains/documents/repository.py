# -*- coding: utf-8 -*-
"""Document 도메인 Repository"""
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.domains.documents.models import Document
from src.domains.tags.models import DocumentTag


class DocumentRepository:
    """Document 엔티티 데이터 접근 계층"""

    def __init__(self, db: AsyncSession):
        """
        DocumentRepository 초기화

        Args:
            db: SQLAlchemy AsyncSession
        """
        self.db = db

    async def create(
        self,
        user_id: int,
        original_filename: str,
        storage_path: str,
        file_type: str,
        file_size_kb: int,
        commit: bool = True
    ) -> Document:
        """
        신규 문서 생성

        Args:
            user_id: 문서 소유자 ID
            original_filename: 원본 파일 이름
            storage_path: MinIO 저장 경로
            file_type: 파일 MIME 타입
            file_size_kb: 파일 크기 (KB)
            commit: 즉시 commit 여부 (기본값: True, False일 경우 Service에서 관리)

        Returns:
            생성된 Document 객체
        """
        document = Document(
            user_id=user_id,
            original_filename=original_filename,
            storage_path=storage_path,
            file_type=file_type,
            file_size_kb=file_size_kb
        )
        self.db.add(document)
        if commit:
            await self.db.commit()
            await self.db.refresh(document)
        else:
            await self.db.flush()  # ID 생성을 위해 flush (commit은 나중에)
            await self.db.refresh(document)
        return document

    async def find_by_id(self, document_id: int) -> Optional[Document]:
        """
        문서 ID로 문서 조회

        Args:
            document_id: 문서 고유 ID

        Returns:
            Document 객체 또는 None
        """
        result = await self.db.execute(
            select(Document).where(Document.document_id == document_id)
        )
        return result.scalar_one_or_none()

    async def find_by_id_and_user_id(
        self,
        document_id: int,
        user_id: int
    ) -> Optional[Document]:
        """
        문서 ID와 사용자 ID로 문서 조회 (권한 검증용, 태그 포함, N+1 문제 방지)

        Args:
            document_id: 문서 고유 ID
            user_id: 사용자 ID

        Returns:
            Document 객체 또는 None
        """
        result = await self.db.execute(
            select(Document)
            .options(selectinload(Document.document_tags).selectinload(DocumentTag.tag))
            .where(
                Document.document_id == document_id,
                Document.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def find_all_by_user_id(self, user_id: int) -> List[Document]:
        """
        사용자 ID로 모든 문서 조회 (태그 포함, N+1 문제 방지)

        Args:
            user_id: 사용자 ID

        Returns:
            Document 객체 리스트
        """
        result = await self.db.execute(
            select(Document)
            .options(selectinload(Document.document_tags).selectinload(DocumentTag.tag))
            .where(Document.user_id == user_id)
            .order_by(Document.uploaded_at.desc())
        )
        return list(result.scalars().all())

    async def find_all_by_user_id_paginated(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 10
    ) -> List[Document]:
        """
        사용자 ID로 문서 조회 (페이징 적용, 태그 포함, N+1 문제 방지)

        Args:
            user_id: 사용자 ID
            skip: 건너뛸 항목 수
            limit: 가져올 항목 수

        Returns:
            Document 객체 리스트
        """
        result = await self.db.execute(
            select(Document)
            .options(selectinload(Document.document_tags).selectinload(DocumentTag.tag))
            .where(Document.user_id == user_id)
            .order_by(Document.uploaded_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_user_id(self, user_id: int) -> int:
        """
        사용자 ID로 전체 문서 수 조회

        Args:
            user_id: 사용자 ID

        Returns:
            전체 문서 수
        """
        result = await self.db.execute(
            select(func.count(Document.document_id))
            .where(Document.user_id == user_id)
        )
        return result.scalar_one()

    async def delete(self, document: Document) -> bool:
        """
        문서 삭제

        Args:
            document: 삭제할 Document 객체

        Returns:
            삭제 성공 여부
        """
        try:
            await self.db.delete(document)
            await self.db.commit()
            return True
        except Exception:
            await self.db.rollback()
            return False
