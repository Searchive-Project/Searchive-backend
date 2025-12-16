# -*- coding: utf-8 -*-
"""AIChat 도메인 스키마"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ========== Request Schemas ==========

class ConversationCreateRequest(BaseModel):
    """채팅방 생성 요청"""
    title: str = Field(..., min_length=1, max_length=255, description="채팅방 제목")
    document_ids: List[int] = Field(..., min_items=1, description="연결할 문서 ID 리스트")


class MessageSendRequest(BaseModel):
    """메시지 전송 요청"""
    content: str = Field(..., min_length=1, description="사용자 질문")


class ConversationUpdateRequest(BaseModel):
    """채팅방 제목 수정 요청"""
    title: str = Field(..., min_length=1, max_length=255, description="새 제목")


# ========== Response Schemas ==========

class MessageSchema(BaseModel):
    """메시지 스키마"""
    message_id: int = Field(..., description="메시지 ID")
    role: str = Field(..., description="역할 (user | assistant)")
    content: str = Field(..., description="메시지 내용")
    created_at: datetime = Field(..., description="생성 일시")

    class Config:
        from_attributes = True


class ConversationListItemSchema(BaseModel):
    """채팅방 목록 아이템 스키마"""
    conversation_id: int = Field(..., description="채팅방 ID")
    title: str = Field(..., description="채팅방 제목")
    created_at: datetime = Field(..., description="생성 일시")
    updated_at: datetime = Field(..., description="최종 수정 일시")

    class Config:
        from_attributes = True


class ConversationDetailSchema(BaseModel):
    """채팅방 상세 스키마 (메시지 포함)"""
    conversation_id: int = Field(..., description="채팅방 ID")
    user_id: int = Field(..., description="소유자 ID")
    title: str = Field(..., description="채팅방 제목")
    created_at: datetime = Field(..., description="생성 일시")
    updated_at: datetime = Field(..., description="최종 수정 일시")
    messages: List[MessageSchema] = Field(default=[], description="메시지 목록")

    class Config:
        from_attributes = True


class ConversationCreateResponse(BaseModel):
    """채팅방 생성 응답"""
    conversation_id: int = Field(..., description="생성된 채팅방 ID")
    title: str = Field(..., description="채팅방 제목")
    created_at: datetime = Field(..., description="생성 일시")

    class Config:
        from_attributes = True


class MessageSendResponse(BaseModel):
    """메시지 전송 응답"""
    user_message: MessageSchema = Field(..., description="사용자 메시지")
    assistant_message: MessageSchema = Field(..., description="AI 응답 메시지")


class ConversationDeleteResponse(BaseModel):
    """채팅방 삭제 응답"""
    message: str = Field(..., description="삭제 결과 메시지")
    conversation_id: int = Field(..., description="삭제된 채팅방 ID")


class PaginatedConversationListResponse(BaseModel):
    """페이징된 채팅방 목록 응답"""
    items: List[ConversationListItemSchema] = Field(..., description="채팅방 목록")
    total: int = Field(..., description="전체 채팅방 수")
    page: int = Field(..., description="현재 페이지 번호")
    page_size: int = Field(..., description="페이지당 항목 수")
    total_pages: int = Field(..., description="전체 페이지 수")


class DocumentSchema(BaseModel):
    """문서 스키마 (간소화)"""
    document_id: int = Field(..., description="문서 ID")
    original_filename: str = Field(..., description="파일명")
    file_type: str = Field(..., description="파일 타입")
    uploaded_at: datetime = Field(..., description="업로드 일시")

    class Config:
        from_attributes = True


class ConversationDocumentsResponse(BaseModel):
    """채팅방 문서 목록 응답"""
    conversation_id: int = Field(..., description="채팅방 ID")
    documents: List[DocumentSchema] = Field(..., description="연결된 문서 목록")
