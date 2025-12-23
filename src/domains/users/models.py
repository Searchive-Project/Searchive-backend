# -*- coding: utf-8 -*-
from sqlalchemy import Column, BigInteger, String, TIMESTAMP, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
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
    activities = relationship("UserActivity", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(user_id={self.user_id}, kakao_id={self.kakao_id})>"


class UserActivity(Base):
    """사용자 활동 로그 모델 (문서 업로드/조회 등)"""

    __tablename__ = "user_activities"

    activity_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    activity_type = Column(String(20), nullable=False)  # 'VIEW' 또는 'UPLOAD'
    meta_data = Column(JSONB)  # {"tags": ["Deep Learning", "Backend"], "doc_id": 123}
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    # 관계 설정
    user = relationship("User", back_populates="activities")

    # 인덱스 설정 (쿼리 성능 최적화)
    __table_args__ = (
        Index("idx_user_activity_created", "user_id", "created_at"),
    )

    def __repr__(self):
        return f"<UserActivity(activity_id={self.activity_id}, user_id={self.user_id}, type={self.activity_type})>"
