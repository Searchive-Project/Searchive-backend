# -*- coding: utf-8 -*-
"""태그 테이블에 임베딩 벡터 컬럼 추가

Revision ID: 3d63d0d3e953
Revises: 533ac94f3177
Create Date: 2025-11-15 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# Alembic에서 사용하는 리비전 식별자
revision: str = '3d63d0d3e953'
down_revision: Union[str, Sequence[str], None] = '533ac94f3177'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """스키마 업그레이드"""
    # 1. pgvector extension 활성화
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # 2. tags 테이블에 embedding 컬럼 추가 (384차원 벡터)
    # sentence-transformers의 paraphrase-multilingual-MiniLM-L12-v2 모델은 384차원 임베딩 생성
    op.add_column('tags', sa.Column('embedding', Vector(384), nullable=True))

    # 3. 벡터 유사도 검색을 위한 IVFFlat 인덱스 생성
    # cosine distance 기준으로 유사도 검색
    # lists=100: 클러스터 개수 (일반적으로 행 수 / 1000 권장, 초기에는 100으로 설정)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tags_embedding_cosine
        ON tags
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )


def downgrade() -> None:
    """스키마 다운그레이드"""
    # 1. 인덱스 삭제
    op.execute('DROP INDEX IF EXISTS idx_tags_embedding_cosine')

    # 2. embedding 컬럼 삭제
    op.drop_column('tags', 'embedding')

    # 3. pgvector extension 삭제 (주의: 다른 테이블에서 사용 중일 수 있음)
    # op.execute('DROP EXTENSION IF EXISTS vector')
