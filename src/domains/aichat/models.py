# -*- coding: utf-8 -*-
"""AIChat 도메인 모델"""
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.db.session import Base


class Conversation(Base):
    """AI 채팅방 모델"""

    __tablename__ = "conversations"

    conversation_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())

    # 관계 설정
    owner = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    conversation_documents = relationship("ConversationDocument", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Conversation(conversation_id={self.conversation_id}, title={self.title})>"


class Message(Base):
    """채팅 메시지 모델"""

    __tablename__ = "messages"

    message_id = Column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id = Column(BigInteger, ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user' | 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    # 관계 설정
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message(message_id={self.message_id}, role={self.role})>"


class ConversationDocument(Base):
    """채팅방-문서 연결 테이블 (M:N)"""

    __tablename__ = "conversation_documents"

    conversation_id = Column(BigInteger, ForeignKey("conversations.conversation_id", ondelete="CASCADE"), primary_key=True, nullable=False)
    document_id = Column(BigInteger, ForeignKey("documents.document_id", ondelete="CASCADE"), primary_key=True, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    # 관계 설정
    conversation = relationship("Conversation", back_populates="conversation_documents")
    document = relationship("Document")  # Document 측에서 역참조 불필요

    def __repr__(self):
        return f"<ConversationDocument(conversation_id={self.conversation_id}, document_id={self.document_id})>"
