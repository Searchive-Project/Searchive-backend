# -*- coding: utf-8 -*-
"""Document 도메인 Service"""
from typing import List, Optional, Tuple, Dict
import uuid
import math
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.domains.documents.repository import DocumentRepository
from src.domains.documents.models import Document
from src.domains.tags.service import TagService
from src.domains.tags.models import Tag
from src.core.minio_client import minio_client
from src.core.text_extractor import text_extractor
from src.core.elasticsearch_client import elasticsearch_client
from src.core.keyword_extraction import keyword_extraction_service
from src.core.ollama_summarizer import ollama_summarizer
import logging

logger = logging.getLogger(__name__)

# 허용된 파일 형식 (MIME 타입)
ALLOWED_MIME_TYPES = {
    "application/pdf",  # .pdf
    "text/plain",  # .txt
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/vnd.ms-excel",  # .xls
    "application/msword",  # .doc
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.ms-powerpoint",  # .ppt
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
    "application/x-hwp",  # .hwp (한글)
    "application/haansofthwp",  # .hwp (한글, 일부 브라우저)
    "application/vnd.hancom.hwp"  # .hwp (한글, 표준 MIME 타입)
}


class DocumentService:
    """Document 비즈니스 로직 처리 계층"""

    def __init__(self, document_repository: DocumentRepository, db: AsyncSession = None):
        """
        DocumentService 초기화

        Args:
            document_repository: DocumentRepository 인스턴스
            db: AsyncSession (TagService를 위해 필요)
        """
        self.document_repository = document_repository
        self.db = db
        self.tag_service = TagService(db) if db else None

    async def upload_document(
        self,
        user_id: int,
        file: UploadFile
    ) -> Tuple[Document, List[Tag], str]:
        """
        문서 업로드 (파일 검증 → MinIO 저장 → DB 저장 → 텍스트 추출 → Elasticsearch 색인 → 키워드 추출 → 태그 생성)

        Args:
            user_id: 업로드하는 사용자 ID
            file: 업로드된 파일

        Returns:
            (생성된 Document 객체, 생성된 Tag 리스트, 추출 방법)

        Raises:
            HTTPException: 파일 형식이 허용되지 않거나 업로드 실패 시
        """
        # 1. 파일 형식 검증
        if file.content_type not in ALLOWED_MIME_TYPES:
            logger.warning(f"허용되지 않은 파일 형식: {file.content_type}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"지원하지 않는 파일 형식입니다: {file.content_type}. 텍스트 기반 문서만 업로드 가능합니다."
            )

        # 2. 고유 경로 생성 (user_id/uuid.확장자)
        file_extension = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}" # uuid.uudi4()는 무작위 기반 중복되지 않는 고유한 UUID를 생성해서 반환 
        storage_path = f"{user_id}/{unique_filename}"

        # 3. 파일 크기 계산 (KB)
        file_data = await file.read()
        file_size_bytes = len(file_data)
        file_size_kb = file_size_bytes // 1024

        # MinIO 업로드 여부 추적 (롤백용)
        minio_uploaded = False

        try:
            # 4. MinIO에 파일 업로드
            from io import BytesIO
            file_stream = BytesIO(file_data)

            minio_client.upload_file(
                file_path=storage_path,
                file_data=file_stream,
                file_size=file_size_bytes,
                content_type=file.content_type
            )
            minio_uploaded = True
            logger.info(f"MinIO 업로드 성공: {storage_path}")

            # 5. PostgreSQL에 메타데이터 저장 (commit하지 않음)
            document = await self.document_repository.create(
                user_id=user_id,
                original_filename=file.filename,
                storage_path=storage_path,
                file_type=file.content_type,
                file_size_kb=file_size_kb,
                commit=False  # Service 레벨에서 트랜잭션 관리
            )
            logger.info(f"문서 메타데이터 저장 성공 (pending commit): document_id={document.document_id}")

            # 6. 텍스트 추출
            extracted_text = text_extractor.extract_text_from_bytes(
                file_data=file_data,
                file_type=file.content_type,
                filename=file.filename
            )

            if not extracted_text or len(extracted_text.strip()) < 10:
                logger.warning(f"문서 {document.document_id}에서 텍스트 추출 실패 또는 너무 짧음. 태그 생성 건너뜀.")
                # 텍스트 추출 실패는 오류가 아니므로 commit 후 반환
                await self.db.commit()
                await self.db.refresh(document)
                return document, [], "none"

            # 7. 문서 요약 생성 (Ollama 사용)
            summary = await ollama_summarizer.summarize(extracted_text)
            if summary:
                document.summary = summary
                logger.info(f"문서 요약 생성 완료: document_id={document.document_id}, summary={summary[:50]}...")
            else:
                logger.warning(f"문서 {document.document_id}에서 요약 생성 실패")

            # 8. Elasticsearch에 문서 색인
            await elasticsearch_client.index_document(
                document_id=document.document_id,
                user_id=user_id,
                content=extracted_text,
                filename=file.filename,
                file_type=file.content_type,
                uploaded_at=document.uploaded_at.isoformat()
            )
            logger.info(f"Elasticsearch 색인 완료: document_id={document.document_id}")

            # 9. 하이브리드 키워드 추출 (KeyBERT or Elasticsearch)
            keywords, extraction_method = await keyword_extraction_service.extract_keywords(
                text=extracted_text,
                document_id=document.document_id
            )

            if not keywords:
                logger.warning(f"문서 {document.document_id}에서 키워드 추출 실패. 태그 생성 건너뜀.")
                # 키워드 추출 실패는 오류가 아니므로 commit 후 반환
                await self.db.commit()
                await self.db.refresh(document)
                return document, [], extraction_method

            # 10. 태그 생성 및 문서에 연결 (Get-or-Create 패턴으로 N+1 문제 방지, commit하지 않음)
            if self.tag_service:
                tags = await self.tag_service.attach_tags_to_document(
                    document_id=document.document_id,
                    tag_names=keywords,
                    commit=False  # Service 레벨에서 트랜잭션 관리
                )
                logger.info(f"문서 {document.document_id}에 태그 {len(tags)}개 연결 완료 (pending commit)")
            else:
                tags = []
                logger.warning("TagService가 초기화되지 않았습니다. 태그 생성 건너뜀.")

            # 11. 모든 DB 작업 성공 시 commit
            await self.db.commit()
            logger.info(f"문서 업로드 트랜잭션 commit 완료: document_id={document.document_id}")

            # 12. commit 후 document 객체를 refresh하여 최신 상태 로드
            await self.db.refresh(document)

            return document, tags, extraction_method

        except HTTPException:
            # HTTPException은 그대로 전파하되, DB 롤백 + MinIO 파일 삭제
            await self.db.rollback()
            logger.info("DB 트랜잭션 롤백 완료")

            if minio_uploaded:
                try:
                    minio_client.delete_file(storage_path)
                    logger.info(f"오류로 인한 MinIO 파일 롤백 완료: {storage_path}")
                except Exception as delete_error:
                    logger.error(f"MinIO 파일 삭제 실패 (수동 정리 필요): {storage_path}, 오류: {delete_error}")
            raise
        except Exception as e:
            logger.error(f"문서 업로드 실패: {e}", exc_info=True)

            # 보상 트랜잭션: DB 롤백 + MinIO 파일 삭제
            await self.db.rollback()
            logger.info("DB 트랜잭션 롤백 완료")

            if minio_uploaded:
                try:
                    minio_client.delete_file(storage_path)
                    logger.info(f"오류로 인한 MinIO 파일 롤백 완료: {storage_path}")
                except Exception as delete_error:
                    logger.error(f"MinIO 파일 삭제 실패 (수동 정리 필요): {storage_path}, 오류: {delete_error}")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="문서 업로드 중 오류가 발생했습니다."
            )

    async def get_user_documents(self, user_id: int) -> List[Document]:
        """
        사용자의 모든 문서 조회 (내림차순)

        Args:
            user_id: 사용자 ID

        Returns:
            Document 객체 리스트
        """
        return await self.document_repository.find_all_by_user_id(user_id)

    async def get_user_documents_ascending(self, user_id: int) -> List[Document]:
        """
        사용자의 모든 문서 조회 (올림차순)

        Args:
            user_id: 사용자 ID

        Returns:
            Document 객체 리스트
        """
        return await self.document_repository.find_all_by_user_id_ascending(user_id)

    async def get_user_documents_paginated(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 10
    ) -> Dict:
        """
        사용자의 문서 조회 (페이징 적용, 내림차순)

        Args:
            user_id: 사용자 ID
            page: 페이지 번호 (1부터 시작)
            page_size: 페이지당 항목 수

        Returns:
            {
                "documents": Document 객체 리스트,
                "total": 전체 문서 수,
                "page": 현재 페이지,
                "page_size": 페이지당 항목 수,
                "total_pages": 전체 페이지 수
            }
        """
        # 페이지 번호 검증 (1부터 시작)
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10

        # skip 계산 (0부터 시작)
        skip = (page - 1) * page_size

        # 문서 목록과 전체 개수 조회
        documents = await self.document_repository.find_all_by_user_id_paginated(
            user_id=user_id,
            skip=skip,
            limit=page_size
        )
        total = await self.document_repository.count_by_user_id(user_id)

        # 전체 페이지 수 계산
        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return {
            "documents": documents,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

    async def get_user_documents_paginated_ascending(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 10
    ) -> Dict:
        """
        사용자의 문서 조회 (페이징 적용, 올림차순)

        Args:
            user_id: 사용자 ID
            page: 페이지 번호 (1부터 시작)
            page_size: 페이지당 항목 수

        Returns:
            {
                "documents": Document 객체 리스트,
                "total": 전체 문서 수,
                "page": 현재 페이지,
                "page_size": 페이지당 항목 수,
                "total_pages": 전체 페이지 수
            }
        """
        # 페이지 번호 검증 (1부터 시작)
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10

        # skip 계산 (0부터 시작)
        skip = (page - 1) * page_size

        # 문서 목록과 전체 개수 조회
        documents = await self.document_repository.find_all_by_user_id_paginated_ascending(
            user_id=user_id,
            skip=skip,
            limit=page_size
        )
        total = await self.document_repository.count_by_user_id(user_id)

        # 전체 페이지 수 계산
        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return {
            "documents": documents,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

    async def get_document_by_id(
        self,
        document_id: int,
        user_id: int
    ) -> Optional[Document]:
        """
        특정 문서 조회 (권한 검증 포함)

        Args:
            document_id: 문서 ID
            user_id: 요청하는 사용자 ID

        Returns:
            Document 객체 또는 None
        """
        return await self.document_repository.find_by_id_and_user_id(
            document_id=document_id,
            user_id=user_id
        )

    async def delete_document(
        self,
        document_id: int,
        user_id: int
    ) -> bool:
        """
        문서 삭제 (MinIO 파일 삭제 + DB 삭제)

        Args:
            document_id: 삭제할 문서 ID
            user_id: 요청하는 사용자 ID

        Returns:
            삭제 성공 여부

        Raises:
            HTTPException: 문서를 찾을 수 없거나 삭제 실패 시
        """
        # 1. 문서 조회 (권한 검증)
        document = await self.document_repository.find_by_id_and_user_id(
            document_id=document_id,
            user_id=user_id
        )

        if not document:
            logger.warning(f"문서 찾을 수 없음: document_id={document_id}, user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="문서를 찾을 수 없습니다."
            )

        try:
            # 2. MinIO에서 파일 삭제
            minio_client.delete_file(document.storage_path)
            logger.info(f"MinIO 파일 삭제 성공: {document.storage_path}")

            # 3. PostgreSQL에서 메타데이터 삭제 (CASCADE로 관련 태그도 자동 삭제)
            success = await self.document_repository.delete(document)

            if success:
                logger.info(f"문서 삭제 성공: document_id={document_id}")
                return True
            else:
                logger.error(f"DB에서 문서 삭제 실패: document_id={document_id}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="문서 삭제 중 오류가 발생했습니다."
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"문서 삭제 실패: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="문서 삭제 중 오류가 발생했습니다."
            )

    async def search_documents_by_filename(
        self,
        user_id: int,
        query: str
    ) -> List[Document]:
        """
        파일명으로 문서 검색 (Elasticsearch 사용)

        Args:
            user_id: 사용자 ID
            query: 검색 쿼리 (파일명)

        Returns:
            Document 객체 리스트
        """
        # Elasticsearch에서 파일명 검색
        search_results = await elasticsearch_client.search_documents_by_filename(
            user_id=user_id,
            query=query
        )

        if not search_results:
            logger.info(f"파일명 검색 결과 없음: user_id={user_id}, query={query}")
            return []

        # Elasticsearch에서 반환된 document_id 리스트로 DB에서 문서 조회
        document_ids = [result["document_id"] for result in search_results]

        documents = []
        for document_id in document_ids:
            document = await self.document_repository.find_by_id_and_user_id(
                document_id=document_id,
                user_id=user_id
            )
            if document:
                documents.append(document)

        logger.info(f"파일명 검색 완료: {len(documents)}개 문서 발견")
        return documents

    async def search_documents_by_tags(
        self,
        user_id: int,
        tag_names: List[str]
    ) -> List[Document]:
        """
        태그로 문서 검색 (PostgreSQL 사용)

        Args:
            user_id: 사용자 ID
            tag_names: 검색할 태그 이름 리스트

        Returns:
            Document 객체 리스트
        """
        documents = await self.document_repository.find_by_tag_names(
            user_id=user_id,
            tag_names=tag_names
        )

        logger.info(f"태그 검색 완료: {len(documents)}개 문서 발견")
        return documents
