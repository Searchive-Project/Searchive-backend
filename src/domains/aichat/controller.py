# -*- coding: utf-8 -*-
"""AIChat 도메인 컨트롤러 (API 엔드포인트)"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.domains.aichat.service import AIChatService
from src.domains.aichat.schema import (
    ConversationCreateRequest,
    ConversationCreateResponse,
    ConversationListItemSchema,
    ConversationDetailSchema,
    ConversationDeleteResponse,
    ConversationUpdateRequest,
    MessageSendRequest,
    MessageSendResponse,
    MessageSchema,
    PaginatedConversationListResponse,
    ConversationDocumentsResponse,
    DocumentSchema
)
from src.core.security import get_current_user_id
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


def get_aichat_service(db: AsyncSession = Depends(get_db)) -> AIChatService:
    """AIChatService 의존성 주입"""
    return AIChatService(db)


@router.post(
    "/conversations",
    response_model=ConversationCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="채팅방 생성"
)
async def create_conversation(
    request: ConversationCreateRequest,
    user_id: int = Depends(get_current_user_id),
    service: AIChatService = Depends(get_aichat_service)
):
    """
    새 채팅방을 생성하고 문서를 연결합니다.

    Args:
        request: 채팅방 제목 + 문서 ID 리스트
        user_id: 현재 로그인한 사용자 ID
        service: AIChatService 의존성 주입

    Returns:
        ConversationCreateResponse: 생성된 채팅방 정보
    """
    logger.info(f"채팅방 생성 요청: user_id={user_id}, title={request.title}, documents={len(request.document_ids)}개")

    conversation = await service.create_conversation(
        user_id=user_id,
        title=request.title,
        document_ids=request.document_ids
    )

    logger.info(f"채팅방 생성 성공: conversation_id={conversation.conversation_id}")

    return ConversationCreateResponse(
        conversation_id=conversation.conversation_id,
        title=conversation.title,
        created_at=conversation.created_at
    )


@router.get(
    "/conversations",
    response_model=PaginatedConversationListResponse,
    summary="채팅방 목록 조회"
)
async def get_conversations(
    page: int = Query(1, ge=1, description="페이지 번호 (1부터 시작)"),
    page_size: int = Query(20, ge=1, le=100, description="페이지당 항목 수"),
    user_id: int = Depends(get_current_user_id),
    service: AIChatService = Depends(get_aichat_service)
):
    """
    현재 로그인한 사용자의 채팅방 목록을 조회합니다. (페이징)

    Args:
        page: 페이지 번호
        page_size: 페이지당 항목 수
        user_id: 현재 로그인한 사용자 ID
        service: AIChatService 의존성 주입

    Returns:
        PaginatedConversationListResponse: 페이징된 채팅방 목록
    """
    result = await service.get_conversation_list(
        user_id=user_id,
        page=page,
        page_size=page_size
    )

    return PaginatedConversationListResponse(
        items=[
            ConversationListItemSchema(
                conversation_id=conv.conversation_id,
                title=conv.title,
                created_at=conv.created_at,
                updated_at=conv.updated_at
            )
            for conv in result["conversations"]
        ],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"]
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailSchema,
    summary="채팅방 상세 조회"
)
async def get_conversation(
    conversation_id: int,
    user_id: int = Depends(get_current_user_id),
    service: AIChatService = Depends(get_aichat_service)
):
    """
    특정 채팅방의 상세 정보를 조회합니다. (메시지 포함)

    Args:
        conversation_id: 채팅방 ID
        user_id: 현재 로그인한 사용자 ID
        service: AIChatService 의존성 주입

    Returns:
        ConversationDetailSchema: 채팅방 상세 정보

    Raises:
        HTTPException: 채팅방을 찾을 수 없는 경우
    """
    conversation = await service.get_conversation_detail(
        conversation_id=conversation_id,
        user_id=user_id
    )

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="채팅방을 찾을 수 없습니다."
        )

    return ConversationDetailSchema(
        conversation_id=conversation.conversation_id,
        user_id=conversation.user_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            MessageSchema(
                message_id=msg.message_id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at
            )
            for msg in conversation.messages
        ]
    )


@router.delete(
    "/conversations/{conversation_id}",
    response_model=ConversationDeleteResponse,
    summary="채팅방 삭제"
)
async def delete_conversation(
    conversation_id: int,
    user_id: int = Depends(get_current_user_id),
    service: AIChatService = Depends(get_aichat_service)
):
    """
    특정 채팅방을 삭제합니다. (메시지, 문서 연결도 함께 삭제)

    Args:
        conversation_id: 채팅방 ID
        user_id: 현재 로그인한 사용자 ID
        service: AIChatService 의존성 주입

    Returns:
        ConversationDeleteResponse: 삭제 결과 메시지
    """
    logger.info(f"채팅방 삭제 요청: conversation_id={conversation_id}, user_id={user_id}")

    await service.delete_conversation(
        conversation_id=conversation_id,
        user_id=user_id
    )

    logger.info(f"채팅방 삭제 완료: conversation_id={conversation_id}")

    return ConversationDeleteResponse(
        message="채팅방이 성공적으로 삭제되었습니다.",
        conversation_id=conversation_id
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageSendResponse,
    status_code=status.HTTP_201_CREATED,
    summary="메시지 전송 및 AI 응답 받기"
)
async def send_message(
    conversation_id: int,
    request: MessageSendRequest,
    user_id: int = Depends(get_current_user_id),
    service: AIChatService = Depends(get_aichat_service)
):
    """
    사용자 질문을 전송하고 AI 응답을 받습니다. (RAG 방식)

    Args:
        conversation_id: 채팅방 ID
        request: 사용자 질문
        user_id: 현재 로그인한 사용자 ID
        service: AIChatService 의존성 주입

    Returns:
        MessageSendResponse: 사용자 메시지 + AI 응답 메시지
    """
    logger.info(f"메시지 전송: conversation_id={conversation_id}, user_id={user_id}")

    user_msg, assistant_msg = await service.send_message_and_get_response(
        conversation_id=conversation_id,
        user_id=user_id,
        user_message=request.content
    )

    logger.info(f"AI 응답 완료: user_msg_id={user_msg.message_id}, assistant_msg_id={assistant_msg.message_id}")

    return MessageSendResponse(
        user_message=MessageSchema(
            message_id=user_msg.message_id,
            role=user_msg.role,
            content=user_msg.content,
            created_at=user_msg.created_at
        ),
        assistant_message=MessageSchema(
            message_id=assistant_msg.message_id,
            role=assistant_msg.role,
            content=assistant_msg.content,
            created_at=assistant_msg.created_at
        )
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=List[MessageSchema],
    summary="메시지 목록 조회"
)
async def get_messages(
    conversation_id: int,
    user_id: int = Depends(get_current_user_id),
    service: AIChatService = Depends(get_aichat_service)
):
    """
    특정 채팅방의 메시지 목록을 조회합니다.

    Args:
        conversation_id: 채팅방 ID
        user_id: 현재 로그인한 사용자 ID
        service: AIChatService 의존성 주입

    Returns:
        List[MessageSchema]: 메시지 목록
    """
    messages = await service.get_messages(
        conversation_id=conversation_id,
        user_id=user_id
    )

    return [
        MessageSchema(
            message_id=msg.message_id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at
        )
        for msg in messages
    ]


@router.get(
    "/conversations/{conversation_id}/documents",
    response_model=ConversationDocumentsResponse,
    summary="채팅방에 연결된 문서 목록 조회"
)
async def get_conversation_documents(
    conversation_id: int,
    user_id: int = Depends(get_current_user_id),
    service: AIChatService = Depends(get_aichat_service)
):
    """
    특정 채팅방에 연결된 문서 목록을 조회합니다.

    Args:
        conversation_id: 채팅방 ID
        user_id: 현재 로그인한 사용자 ID
        service: AIChatService 의존성 주입

    Returns:
        ConversationDocumentsResponse: 문서 목록
    """
    documents = await service.get_conversation_documents(
        conversation_id=conversation_id,
        user_id=user_id
    )

    return ConversationDocumentsResponse(
        conversation_id=conversation_id,
        documents=[
            DocumentSchema(
                document_id=doc.document_id,
                original_filename=doc.original_filename,
                file_type=doc.file_type,
                uploaded_at=doc.uploaded_at
            )
            for doc in documents
        ]
    )


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationListItemSchema,
    summary="채팅방 제목 수정"
)
async def update_conversation(
    conversation_id: int,
    request: ConversationUpdateRequest,
    user_id: int = Depends(get_current_user_id),
    service: AIChatService = Depends(get_aichat_service)
):
    """
    특정 채팅방의 제목을 수정합니다.

    Args:
        conversation_id: 채팅방 ID
        request: 새 제목
        user_id: 현재 로그인한 사용자 ID
        service: AIChatService 의존성 주입

    Returns:
        ConversationListItemSchema: 수정된 채팅방 정보
    """
    logger.info(f"채팅방 제목 수정: conversation_id={conversation_id}, new_title={request.title}")

    conversation = await service.update_conversation_title(
        conversation_id=conversation_id,
        user_id=user_id,
        new_title=request.title
    )

    return ConversationListItemSchema(
        conversation_id=conversation.conversation_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at
    )
