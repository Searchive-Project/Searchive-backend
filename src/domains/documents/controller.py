# -*- coding: utf-8 -*-
"""Document 도메인 컨트롤러 (API 엔드포인트)"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.domains.documents.repository import DocumentRepository
from src.domains.documents.service import DocumentService
from src.domains.documents.schema import (
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentDetailResponse,
    DocumentDeleteResponse,
    PaginatedDocumentListResponse
)
from src.core.security import get_current_user_id


router = APIRouter()


def get_document_service(db: AsyncSession = Depends(get_db)) -> DocumentService:
    """DocumentService 의존성 주입"""
    document_repository = DocumentRepository(db)
    return DocumentService(document_repository, db)


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="문서 업로드"
)
async def upload_document(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    사용자가 문서를 업로드합니다.

    Args:
        file: 업로드할 파일 (multipart/form-data)
        user_id: get_current_user_id 의존성에서 주입된 사용자 ID
        document_service: DocumentService 의존성 주입

    Returns:
        DocumentUploadResponse: 업로드된 문서의 메타데이터

    Raises:
        HTTPException: 파일 형식이 허용되지 않거나 업로드 실패 시
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"문서 업로드 요청: user_id={user_id}, filename={file.filename}")

    document, tags, extraction_method = await document_service.upload_document(
        user_id=user_id,
        file=file
    )

    logger.info(f"문서 업로드 성공: document_id={document.document_id}, tags={len(tags)}개")

    from src.domains.documents.schema import TagSchema

    return DocumentUploadResponse(
        document_id=document.document_id,
        user_id=document.user_id,
        original_filename=document.original_filename,
        storage_path=document.storage_path,
        file_type=document.file_type,
        file_size_kb=document.file_size_kb,
        uploaded_at=document.uploaded_at,
        updated_at=document.updated_at,
        tags=[TagSchema(tag_id=tag.tag_id, name=tag.name) for tag in tags],
        extraction_method=extraction_method
    )


@router.get(
    "",
    response_model=List[DocumentListResponse],
    summary="문서 목록 조회"
)
async def get_documents(
    user_id: int = Depends(get_current_user_id),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    현재 로그인된 사용자의 모든 문서 목록을 조회합니다.

    Args:
        user_id: get_current_user_id 의존성에서 주입된 사용자 ID
        document_service: DocumentService 의존성 주입

    Returns:
        List[DocumentListResponse]: 문서 메타데이터 목록
    """
    documents = await document_service.get_user_documents(user_id)

    from src.domains.documents.schema import TagSchema

    return [
        DocumentListResponse(
            document_id=doc.document_id,
            original_filename=doc.original_filename,
            file_type=doc.file_type,
            file_size_kb=doc.file_size_kb,
            summary=doc.summary,
            uploaded_at=doc.uploaded_at,
            updated_at=doc.updated_at,
            tags=[TagSchema(tag_id=dt.tag.tag_id, name=dt.tag.name) for dt in doc.document_tags]
        )
        for doc in documents
    ]


@router.get(
    "/paginated",
    response_model=PaginatedDocumentListResponse,
    summary="문서 목록 조회 (페이징)"
)
async def get_documents_paginated(
    page: int = 1,
    page_size: int = 10,
    user_id: int = Depends(get_current_user_id),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    현재 로그인된 사용자의 문서 목록을 페이징하여 조회합니다.

    Args:
        page: 페이지 번호 (1부터 시작, 기본값: 1)
        page_size: 페이지당 항목 수 (기본값: 10)
        user_id: get_current_user_id 의존성에서 주입된 사용자 ID
        document_service: DocumentService 의존성 주입

    Returns:
        PaginatedDocumentListResponse: 페이징된 문서 메타데이터 목록
    """
    result = await document_service.get_user_documents_paginated(
        user_id=user_id,
        page=page,
        page_size=page_size
    )

    from src.domains.documents.schema import TagSchema

    return PaginatedDocumentListResponse(
        items=[
            DocumentListResponse(
                document_id=doc.document_id,
                original_filename=doc.original_filename,
                file_type=doc.file_type,
                file_size_kb=doc.file_size_kb,
                summary=doc.summary,
                uploaded_at=doc.uploaded_at,
                updated_at=doc.updated_at,
                tags=[TagSchema(tag_id=dt.tag.tag_id, name=dt.tag.name) for dt in doc.document_tags]
            )
            for doc in result["documents"]
        ],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"]
    )


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="문서 상세 조회"
)
async def get_document(
    document_id: int,
    user_id: int = Depends(get_current_user_id),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    특정 문서의 상세 정보를 조회합니다. (권한 검증 포함)

    Args:
        document_id: 조회할 문서 ID
        user_id: get_current_user_id 의존성에서 주입된 사용자 ID
        document_service: DocumentService 의존성 주입

    Returns:
        DocumentDetailResponse: 문서 상세 정보

    Raises:
        HTTPException: 문서를 찾을 수 없는 경우
    """
    document = await document_service.get_document_by_id(
        document_id=document_id,
        user_id=user_id
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문서를 찾을 수 없습니다."
        )

    from src.domains.documents.schema import TagSchema

    return DocumentDetailResponse(
        document_id=document.document_id,
        user_id=document.user_id,
        original_filename=document.original_filename,
        storage_path=document.storage_path,
        file_type=document.file_type,
        file_size_kb=document.file_size_kb,
        summary=document.summary,
        uploaded_at=document.uploaded_at,
        updated_at=document.updated_at,
        tags=[TagSchema(tag_id=dt.tag.tag_id, name=dt.tag.name) for dt in document.document_tags]
    )


@router.delete(
    "/{document_id}",
    response_model=DocumentDeleteResponse,
    summary="문서 삭제"
)
async def delete_document(
    document_id: int,
    user_id: int = Depends(get_current_user_id),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    특정 문서를 삭제합니다. (MinIO 파일 + DB 메타데이터 + 관련 태그)

    Args:
        document_id: 삭제할 문서 ID
        user_id: get_current_user_id 의존성에서 주입된 사용자 ID
        document_service: DocumentService 의존성 주입

    Returns:
        DocumentDeleteResponse: 삭제 성공 메시지

    Raises:
        HTTPException: 문서를 찾을 수 없거나 삭제 실패 시
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"문서 삭제 요청: document_id={document_id}, user_id={user_id}")

    await document_service.delete_document(
        document_id=document_id,
        user_id=user_id
    )

    logger.info(f"문서 삭제 완료: document_id={document_id}")

    return DocumentDeleteResponse(
        message="문서가 성공적으로 삭제되었습니다.",
        document_id=document_id
    )
