# -*- coding: utf-8 -*-
from sqlalchemy import Column, BigInteger, String, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from src.db.session import Base


class Tag(Base):
    """문서 분류를 위한 태그 모델"""

    __tablename__ = "tags"

    tag_id = Column(BigInteger, primary_key=True, autoincrement=True)  # 태그 고유 ID
    name = Column(String(100), unique=True, nullable=False, index=True)  # 태그 이름
    embedding = Column(Vector(384), nullable=True)  # 태그 임베딩 벡터 (384차원)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())  # 생성 일시

    # 관계 설정
    document_tags = relationship("DocumentTag", back_populates="tag", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tag(tag_id={self.tag_id}, name={self.name})>"


class DocumentTag(Base):
    """문서-태그 다대다 관계를 위한 연결 테이블"""

    __tablename__ = "document_tags"

    document_id = Column(BigInteger, ForeignKey("documents.document_id", ondelete="CASCADE"), primary_key=True, nullable=False)  # 문서 ID
    tag_id = Column(BigInteger, ForeignKey("tags.tag_id", ondelete="CASCADE"), primary_key=True, nullable=False)  # 태그 ID
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())  # 연결 생성 일시

    # 관계 설정
    document = relationship("Document", back_populates="document_tags")
    tag = relationship("Tag", back_populates="document_tags")

    def __repr__(self):
        return f"<DocumentTag(document_id={self.document_id}, tag_id={self.tag_id})>"
