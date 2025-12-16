# -*- coding: utf-8 -*-
"""AIChat 도메인 Repository"""
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.domains.aichat.models import Conversation, Message, ConversationDocument


class ConversationRepository:
    """Conversation 엔티티 데이터 접근 계층"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: int,
        title: str,
        commit: bool = True
    ) -> Conversation:
        """
        신규 채팅방 생성

        Args:
            user_id: 소유자 ID
            title: 채팅방 제목
            commit: 즉시 commit 여부

        Returns:
            생성된 Conversation 객체
        """
        conversation = Conversation(user_id=user_id, title=title)
        self.db.add(conversation)
        if commit:
            await self.db.commit()
            await self.db.refresh(conversation)
        else:
            await self.db.flush()
            await self.db.refresh(conversation)
        return conversation

    async def find_by_id_and_user_id(
        self,
        conversation_id: int,
        user_id: int,
        include_messages: bool = False,
        include_documents: bool = False
    ) -> Optional[Conversation]:
        """
        채팅방 ID와 사용자 ID로 조회 (권한 검증용, N+1 방지)

        Args:
            conversation_id: 채팅방 ID
            user_id: 사용자 ID
            include_messages: 메시지 포함 여부
            include_documents: 문서 포함 여부
        """
        query = select(Conversation).where(
            Conversation.conversation_id == conversation_id,
            Conversation.user_id == user_id
        )

        # Eager loading 설정
        if include_messages:
            query = query.options(selectinload(Conversation.messages))
        if include_documents:
            query = query.options(
                selectinload(Conversation.conversation_documents).selectinload(ConversationDocument.document)
            )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def find_all_by_user_id(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> List[Conversation]:
        """
        사용자의 채팅방 목록 조회 (페이징, 최신순)

        Args:
            user_id: 사용자 ID
            skip: 건너뛸 항목 수
            limit: 가져올 항목 수
        """
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_user_id(self, user_id: int) -> int:
        """사용자의 전체 채팅방 수"""
        result = await self.db.execute(
            select(func.count(Conversation.conversation_id))
            .where(Conversation.user_id == user_id)
        )
        return result.scalar_one()

    async def update_title(
        self,
        conversation: Conversation,
        new_title: str
    ) -> Conversation:
        """채팅방 제목 수정"""
        conversation.title = new_title
        await self.db.commit()
        await self.db.refresh(conversation)
        return conversation

    async def delete(self, conversation: Conversation) -> bool:
        """채팅방 삭제 (CASCADE로 메시지, 문서 연결 모두 삭제)"""
        try:
            await self.db.delete(conversation)
            await self.db.commit()
            return True
        except Exception:
            await self.db.rollback()
            return False


class MessageRepository:
    """Message 엔티티 데이터 접근 계층"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        conversation_id: int,
        role: str,
        content: str,
        commit: bool = True
    ) -> Message:
        """
        메시지 생성

        Args:
            conversation_id: 채팅방 ID
            role: 'user' | 'assistant'
            content: 메시지 내용
            commit: 즉시 commit 여부
        """
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content
        )
        self.db.add(message)
        if commit:
            await self.db.commit()
            await self.db.refresh(message)
        else:
            await self.db.flush()
            await self.db.refresh(message)
        return message

    async def find_by_conversation_id(
        self,
        conversation_id: int,
        limit: Optional[int] = None
    ) -> List[Message]:
        """
        채팅방의 메시지 목록 조회 (시간순)

        Args:
            conversation_id: 채팅방 ID
            limit: 최대 메시지 수 (None이면 전체)
        """
        query = select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc())

        if limit:
            query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def find_recent_messages(
        self,
        conversation_id: int,
        limit: int = 10
    ) -> List[Message]:
        """
        최근 N개 메시지 조회 (RAG 컨텍스트용)

        Args:
            conversation_id: 채팅방 ID
            limit: 최대 메시지 수
        """
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        # 시간순으로 뒤집어서 반환 (오래된 것부터)
        return list(reversed(result.scalars().all()))


class ConversationDocumentRepository:
    """ConversationDocument 연결 테이블 데이터 접근 계층"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_documents(
        self,
        conversation_id: int,
        document_ids: List[int],
        commit: bool = True
    ) -> List[ConversationDocument]:
        """
        채팅방에 문서 연결 (일괄 추가)

        Args:
            conversation_id: 채팅방 ID
            document_ids: 문서 ID 리스트
            commit: 즉시 commit 여부
        """
        conv_docs = [
            ConversationDocument(
                conversation_id=conversation_id,
                document_id=doc_id
            )
            for doc_id in document_ids
        ]

        self.db.add_all(conv_docs)
        if commit:
            await self.db.commit()
        else:
            await self.db.flush()

        return conv_docs

    async def find_document_ids_by_conversation_id(
        self,
        conversation_id: int
    ) -> List[int]:
        """
        채팅방에 연결된 문서 ID 리스트 조회

        Args:
            conversation_id: 채팅방 ID
        """
        result = await self.db.execute(
            select(ConversationDocument.document_id)
            .where(ConversationDocument.conversation_id == conversation_id)
        )
        return list(result.scalars().all())

    async def find_documents_by_conversation_id(
        self,
        conversation_id: int
    ) -> List[ConversationDocument]:
        """
        채팅방에 연결된 문서 조회 (Document 객체 포함)

        Args:
            conversation_id: 채팅방 ID
        """
        result = await self.db.execute(
            select(ConversationDocument)
            .options(selectinload(ConversationDocument.document))
            .where(ConversationDocument.conversation_id == conversation_id)
        )
        return list(result.scalars().all())
