# -*- coding: utf-8 -*-
"""AIChat 도메인 Service"""
from typing import List, Optional, Dict, Tuple
import math
from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from src.domains.aichat.repository import (
    ConversationRepository,
    MessageRepository,
    ConversationDocumentRepository
)
from src.domains.aichat.models import Conversation, Message
from src.domains.documents.models import Document
from src.core.elasticsearch_client import elasticsearch_client
from src.core.ollama_chat import ollama_chat
import logging

logger = logging.getLogger(__name__)


class AIChatService:
    """AIChat 비즈니스 로직 처리 계층"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.conversation_repo = ConversationRepository(db)
        self.message_repo = MessageRepository(db)
        self.conv_doc_repo = ConversationDocumentRepository(db)

    async def create_conversation(
        self,
        user_id: int,
        title: str,
        document_ids: List[int]
    ) -> Conversation:
        """
        채팅방 생성 + 문서 연결

        Args:
            user_id: 사용자 ID
            title: 채팅방 제목
            document_ids: 연결할 문서 ID 리스트

        Returns:
            생성된 Conversation 객체

        Raises:
            HTTPException: 문서가 없거나 권한이 없을 때
        """
        # 1. 문서 ID 유효성 검증 (모두 해당 사용자의 문서인지 확인)
        if not document_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="최소 1개 이상의 문서를 선택해야 합니다."
            )

        # 2. 문서 소유권 검증 (N+1 방지)
        result = await self.db.execute(
            select(Document.document_id)
            .where(
                and_(
                    Document.document_id.in_(document_ids),
                    Document.user_id == user_id
                )
            )
        )
        valid_doc_ids = set(result.scalars().all())

        invalid_ids = set(document_ids) - valid_doc_ids
        if invalid_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"접근 권한이 없는 문서입니다: {invalid_ids}"
            )

        try:
            # 3. 채팅방 생성 (commit하지 않음)
            conversation = await self.conversation_repo.create(
                user_id=user_id,
                title=title,
                commit=False
            )
            logger.info(f"채팅방 생성: conversation_id={conversation.conversation_id}")

            # 4. 문서 연결 (commit하지 않음)
            await self.conv_doc_repo.add_documents(
                conversation_id=conversation.conversation_id,
                document_ids=document_ids,
                commit=False
            )
            logger.info(f"문서 {len(document_ids)}개 연결 완료")

            # 5. 모든 작업 완료 후 commit
            await self.db.commit()
            await self.db.refresh(conversation)

            return conversation

        except Exception as e:
            await self.db.rollback()
            logger.error(f"채팅방 생성 실패: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="채팅방 생성 중 오류가 발생했습니다."
            )

    async def get_conversation_list(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20
    ) -> Dict:
        """
        채팅방 목록 조회 (페이징)

        Args:
            user_id: 사용자 ID
            page: 페이지 번호 (1부터 시작)
            page_size: 페이지당 항목 수

        Returns:
            {
                "conversations": Conversation 리스트,
                "total": 전체 개수,
                "page": 현재 페이지,
                "page_size": 페이지 크기,
                "total_pages": 전체 페이지 수
            }
        """
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20

        skip = (page - 1) * page_size

        conversations = await self.conversation_repo.find_all_by_user_id(
            user_id=user_id,
            skip=skip,
            limit=page_size
        )
        total = await self.conversation_repo.count_by_user_id(user_id)
        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return {
            "conversations": conversations,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

    async def get_conversation_detail(
        self,
        conversation_id: int,
        user_id: int
    ) -> Optional[Conversation]:
        """
        채팅방 상세 조회 (메시지 포함)

        Args:
            conversation_id: 채팅방 ID
            user_id: 사용자 ID (권한 검증)

        Returns:
            Conversation 객체 또는 None
        """
        return await self.conversation_repo.find_by_id_and_user_id(
            conversation_id=conversation_id,
            user_id=user_id,
            include_messages=True,
            include_documents=False
        )

    async def delete_conversation(
        self,
        conversation_id: int,
        user_id: int
    ) -> bool:
        """
        채팅방 삭제

        Args:
            conversation_id: 채팅방 ID
            user_id: 사용자 ID (권한 검증)

        Returns:
            삭제 성공 여부

        Raises:
            HTTPException: 채팅방을 찾을 수 없거나 권한이 없을 때
        """
        conversation = await self.conversation_repo.find_by_id_and_user_id(
            conversation_id=conversation_id,
            user_id=user_id
        )

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="채팅방을 찾을 수 없습니다."
            )

        success = await self.conversation_repo.delete(conversation)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="채팅방 삭제 중 오류가 발생했습니다."
            )

        logger.info(f"채팅방 삭제 완료: conversation_id={conversation_id}")
        return True

    async def update_conversation_title(
        self,
        conversation_id: int,
        user_id: int,
        new_title: str
    ) -> Conversation:
        """
        채팅방 제목 수정

        Args:
            conversation_id: 채팅방 ID
            user_id: 사용자 ID (권한 검증)
            new_title: 새 제목

        Returns:
            수정된 Conversation 객체

        Raises:
            HTTPException: 채팅방을 찾을 수 없거나 권한이 없을 때
        """
        conversation = await self.conversation_repo.find_by_id_and_user_id(
            conversation_id=conversation_id,
            user_id=user_id
        )

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="채팅방을 찾을 수 없습니다."
            )

        return await self.conversation_repo.update_title(conversation, new_title)

    async def send_message_and_get_response(
        self,
        conversation_id: int,
        user_id: int,
        user_message: str
    ) -> Tuple[Message, Message]:
        """
        메시지 전송 및 AI 응답 생성 (RAG 방식)

        Args:
            conversation_id: 채팅방 ID
            user_id: 사용자 ID (권한 검증)
            user_message: 사용자 질문

        Returns:
            (사용자 메시지, AI 응답 메시지)

        Raises:
            HTTPException: 채팅방을 찾을 수 없거나 권한이 없을 때
        """
        # 1. 채팅방 존재 및 권한 검증
        conversation = await self.conversation_repo.find_by_id_and_user_id(
            conversation_id=conversation_id,
            user_id=user_id
        )

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="채팅방을 찾을 수 없습니다."
            )

        try:
            # 2. 사용자 메시지 저장 (commit하지 않음)
            user_msg = await self.message_repo.create(
                conversation_id=conversation_id,
                role="user",
                content=user_message,
                commit=False
            )
            logger.info(f"사용자 메시지 저장: message_id={user_msg.message_id}")

            # 3. RAG 컨텍스트 생성
            logger.info(f"RAG 컨텍스트 생성 중... conversation_id={conversation_id}")
            context = await self._build_rag_context(
                user_id=user_id,
                conversation_id=conversation_id,
                user_query=user_message
            )
            logger.info(f"RAG 컨텍스트 생성 완료 - 길이: {len(context)}자")

            # 4. 대화 히스토리 조회 (최근 10개 메시지)
            history = await self.message_repo.find_recent_messages(
                conversation_id=conversation_id,
                limit=10
            )
            logger.info(f"대화 히스토리 조회 완료 - {len(history)}개 메시지")

            # 5. Ollama에 질문 전송
            logger.info(f"Ollama에 질문 전송 중... query={user_message[:50]}...")
            ai_response = await ollama_chat.chat(
                user_query=user_message,
                context=context,
                history=history
            )
            logger.info(f"Ollama 응답 수신 완료 - 길이: {len(ai_response) if ai_response else 0}자")

            if not ai_response:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="AI 응답 생성에 실패했습니다."
                )

            # 6. AI 응답 저장 (commit하지 않음)
            assistant_msg = await self.message_repo.create(
                conversation_id=conversation_id,
                role="assistant",
                content=ai_response,
                commit=False
            )
            logger.info(f"AI 응답 저장: message_id={assistant_msg.message_id}")

            # 7. 모든 작업 완료 후 commit
            await self.db.commit()
            await self.db.refresh(user_msg)
            await self.db.refresh(assistant_msg)

            return user_msg, assistant_msg

        except HTTPException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"메시지 처리 실패: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="메시지 처리 중 오류가 발생했습니다."
            )

    async def _build_rag_context(
        self,
        user_id: int,
        conversation_id: int,
        user_query: str,
        max_results: int = 5
    ) -> str:
        """
        RAG 컨텍스트 생성 (Elasticsearch 검색)

        Args:
            user_id: 사용자 ID
            conversation_id: 채팅방 ID
            user_query: 사용자 질문
            max_results: 최대 검색 결과 수

        Returns:
            컨텍스트 문자열
        """
        logger.info(f"[RAG] 컨텍스트 생성 시작 - conversation_id={conversation_id}, user_id={user_id}, query={user_query}")

        # 1. 채팅방에 연결된 문서 ID 조회
        document_ids = await self.conv_doc_repo.find_document_ids_by_conversation_id(
            conversation_id=conversation_id
        )
        logger.info(f"[RAG] 연결된 문서 ID: {document_ids}")

        if not document_ids:
            logger.warning(f"[RAG] 채팅방 {conversation_id}에 연결된 문서가 없습니다.")
            return "관련 문서를 찾을 수 없습니다."

        # 2. Elasticsearch로 관련 문서 내용 검색
        logger.info(f"[RAG] Elasticsearch 검색 시작 - user_id={user_id}, document_ids={document_ids}, query={user_query}")
        search_results = await elasticsearch_client.search_documents_by_content(
            user_id=user_id,
            query=user_query,
            document_ids=document_ids,
            size=max_results
        )
        logger.info(f"[RAG] Elasticsearch 검색 결과: {len(search_results)}개")

        if not search_results:
            logger.warning(f"[RAG] 검색 결과 없음: query={user_query}, document_ids={document_ids}")
            return "질문과 관련된 문서 내용을 찾을 수 없습니다."

        # 3. 컨텍스트 구성 (상위 결과만 사용)
        context_parts = []
        for i, result in enumerate(search_results[:max_results], 1):
            filename = result.get("filename", "Unknown")
            content_snippet = result.get("content_snippet", "")
            logger.info(f"[RAG] 문서 {i}: filename={filename}, snippet_length={len(content_snippet)}")
            context_parts.append(f"[문서 {i}: {filename}]\n{content_snippet}")

        context = "\n\n".join(context_parts)
        logger.info(f"[RAG] 컨텍스트 생성 완료: {len(search_results)}개 문서, {len(context)}자")
        logger.debug(f"[RAG] 생성된 컨텍스트:\n{context[:500]}...")

        return context

    async def get_messages(
        self,
        conversation_id: int,
        user_id: int
    ) -> List[Message]:
        """
        채팅방의 메시지 목록 조회

        Args:
            conversation_id: 채팅방 ID
            user_id: 사용자 ID (권한 검증)

        Returns:
            Message 리스트

        Raises:
            HTTPException: 채팅방을 찾을 수 없거나 권한이 없을 때
        """
        # 권한 검증
        conversation = await self.conversation_repo.find_by_id_and_user_id(
            conversation_id=conversation_id,
            user_id=user_id
        )

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="채팅방을 찾을 수 없습니다."
            )

        return await self.message_repo.find_by_conversation_id(conversation_id)

    async def get_conversation_documents(
        self,
        conversation_id: int,
        user_id: int
    ) -> List:
        """
        채팅방에 연결된 문서 목록 조회

        Args:
            conversation_id: 채팅방 ID
            user_id: 사용자 ID (권한 검증)

        Returns:
            Document 객체 리스트

        Raises:
            HTTPException: 채팅방을 찾을 수 없거나 권한이 없을 때
        """
        # 권한 검증
        conversation = await self.conversation_repo.find_by_id_and_user_id(
            conversation_id=conversation_id,
            user_id=user_id
        )

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="채팅방을 찾을 수 없습니다."
            )

        conv_docs = await self.conv_doc_repo.find_documents_by_conversation_id(
            conversation_id=conversation_id
        )

        return [cd.document for cd in conv_docs]
