# -*- coding: utf-8 -*-
"""Document 도메인 스키마"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class TagSchema(BaseModel):
    """태그 스키마"""
    tag_id: int = Field(..., description="태그 고유 ID")
    name: str = Field(..., description="태그 이름")

    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    """문서 업로드 응답 스키마"""
    document_id: int = Field(..., description="문서 고유 ID")
    user_id: int = Field(..., description="문서 소유자 ID")
    original_filename: str = Field(..., description="원본 파일 이름")
    storage_path: str = Field(..., description="MinIO 저장 경로")
    file_type: str = Field(..., description="파일 MIME 타입")
    file_size_kb: int = Field(..., description="파일 크기 (KB)")
    summary: Optional[str] = Field(None, description="문서 요약")
    uploaded_at: datetime = Field(..., description="업로드 일시")
    updated_at: datetime = Field(..., description="최종 수정 일시")
    tags: List[TagSchema] = Field(default=[], description="자동 생성된 태그 목록")
    extraction_method: Optional[str] = Field(None, description="키워드 추출 방법 (keybert 또는 elasticsearch)")

    class Config:
        from_attributes = True  # ORM 모델 → Pydantic 변환 지원


class DocumentListResponse(BaseModel):
    """문서 목록 조회 응답 스키마"""
    document_id: int = Field(..., description="문서 고유 ID")
    original_filename: str = Field(..., description="원본 파일 이름")
    file_type: str = Field(..., description="파일 MIME 타입")
    file_size_kb: int = Field(..., description="파일 크기 (KB)")
    summary: Optional[str] = Field(None, description="문서 요약")
    uploaded_at: datetime = Field(..., description="업로드 일시")
    updated_at: datetime = Field(..., description="최종 수정 일시")
    tags: List[TagSchema] = Field(default=[], description="태그 목록")

    class Config:
        from_attributes = True


class DocumentDetailResponse(BaseModel):
    """문서 상세 조회 응답 스키마"""
    document_id: int = Field(..., description="문서 고유 ID")
    user_id: int = Field(..., description="문서 소유자 ID")
    original_filename: str = Field(..., description="원본 파일 이름")
    storage_path: str = Field(..., description="MinIO 저장 경로")
    file_type: str = Field(..., description="파일 MIME 타입")
    file_size_kb: int = Field(..., description="파일 크기 (KB)")
    summary: Optional[str] = Field(None, description="문서 요약")
    uploaded_at: datetime = Field(..., description="업로드 일시")
    updated_at: datetime = Field(..., description="최종 수정 일시")
    tags: List[TagSchema] = Field(default=[], description="태그 목록")

    class Config:
        from_attributes = True


class DocumentDeleteResponse(BaseModel):
    """문서 삭제 응답 스키마"""
    message: str = Field(..., description="삭제 결과 메시지")
    document_id: int = Field(..., description="삭제된 문서 ID")


class PaginatedDocumentListResponse(BaseModel):
    """페이징된 문서 목록 조회 응답 스키마"""
    items: List[DocumentListResponse] = Field(..., description="문서 목록")
    total: int = Field(..., description="전체 문서 수")
    page: int = Field(..., description="현재 페이지 번호 (1부터 시작)")
    page_size: int = Field(..., description="페이지당 항목 수")
    total_pages: int = Field(..., description="전체 페이지 수")

    class Config:
        from_attributes = True
