# -*- coding: utf-8 -*-
from sqlalchemy import Column, BigInteger, String, TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.db.session import Base


class User(Base):
    """사용자 인증 및 관리를 위한 사용자 모델"""

    __tablename__ = "users"

    user_id = Column(BigInteger, primary_key=True, autoincrement=True)  # 사용자 고유 ID
    kakao_id = Column(String(255), unique=True, nullable=False, index=True)  # 카카오 소셜 ID
    nickname = Column(String(255))  # 사용자 닉네임
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())  # 가입 일시

    # 관계 설정
    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(user_id={self.user_id}, kakao_id={self.kakao_id})>"
