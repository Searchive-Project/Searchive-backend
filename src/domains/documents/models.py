# -*- coding: utf-8 -*-
from sqlalchemy import Column, BigInteger, String, Integer, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.db.session import Base


class Document(Base):
    """업로드된 파일을 위한 문서 모델"""

    __tablename__ = "documents"

    document_id = Column(BigInteger, primary_key=True, autoincrement=True)  # 문서 고유 ID
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)  # 문서 소유자 ID
    original_filename = Column(String(255), nullable=False)  # 원본 파일 이름
    storage_path = Column(String(1024), unique=True, nullable=False)  # MinIO 저장 경로
    file_type = Column(String(100), nullable=False)  # 파일 MIME 타입
    file_size_kb = Column(Integer)  # 파일 크기 (KB)
    summary = Column(String(500), nullable=True)  # 문서 요약 (평서문 형식)
    uploaded_at = Column(TIMESTAMP, nullable=False, server_default=func.now())  # 업로드 일시
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())  # 최종 수정 일시

    # 관계 설정
    owner = relationship("User", back_populates="documents")
    document_tags = relationship("DocumentTag", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document(document_id={self.document_id}, filename={self.original_filename})>"
