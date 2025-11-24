# -*- coding: utf-8 -*-
"""DB의 태그 임베딩 상태 확인 스크립트"""
import asyncio
from sqlalchemy import text
from src.db.session import get_db


async def check_tag_embeddings():
    """DB의 모든 태그와 임베딩 상태 확인"""

    async for db in get_db():
        # 모든 태그 조회 (raw SQL 사용)
        result = await db.execute(text("SELECT tag_id, name, embedding, created_at FROM tags ORDER BY created_at DESC"))
        tags = result.fetchall()

        print("=" * 80)
        print("DB 태그 임베딩 상태 확인")
        print("=" * 80)
        print(f"총 태그 개수: {len(tags)}")
        print("-" * 80)
        print(f"{'Tag ID':<10} {'Tag Name':<30} {'Has Embedding':<15} {'Created At'}")
        print("-" * 80)

        tags_without_embedding = 0
        tags_with_embedding = 0

        for tag in tags:
            tag_id, name, embedding, created_at = tag
            has_embedding = "✓ YES" if embedding else "✗ NO"
            if embedding:
                tags_with_embedding += 1
            else:
                tags_without_embedding += 1

            print(f"{tag_id:<10} {name:<30} {has_embedding:<15} {created_at}")

        print("-" * 80)
        print(f"임베딩 있음: {tags_with_embedding}개")
        print(f"임베딩 없음: {tags_without_embedding}개")
        print("=" * 80)

        # 임베딩이 없는 태그가 있으면 경고
        if tags_without_embedding > 0:
            print("\n⚠️  경고: 임베딩이 없는 태그가 있습니다!")
            print("   유사도 검색이 작동하지 않아 중복 태그가 생성될 수 있습니다.")
            print("   해결방법: 기존 태그들의 임베딩을 생성하는 마이그레이션이 필요합니다.")

        break


if __name__ == "__main__":
    asyncio.run(check_tag_embeddings())
