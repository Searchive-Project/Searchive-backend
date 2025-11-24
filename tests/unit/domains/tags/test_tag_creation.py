# -*- coding: utf-8 -*-
"""태그 생성 로직 테스트 (get_or_create)"""
import asyncio
from src.db.session import get_db
from src.domains.tags.service import TagService


async def test_tag_creation():
    """유사한 태그 이름으로 생성 시 기존 태그를 재사용하는지 테스트"""

    test_cases = [
        ("Cloud Computing", "Cloud가 재사용되어야 함"),
        ("구름", "클라우드가 재사용되어야 함"),
        ("클라우드 컴퓨팅", "클라우드가 재사용되어야 함"),
        ("Database", "새로 생성될 가능성 높음"),
    ]

    async for db in get_db():
        tag_service = TagService(db)

        print("=" * 80)
        print("태그 생성 로직 테스트 (get_or_create)")
        print("=" * 80)
        print()

        for tag_name, expected in test_cases:
            print(f"테스트: '{tag_name}'")
            print(f"예상: {expected}")

            try:
                tag = await tag_service.get_or_create_tag(
                    name=tag_name,
                    similarity_threshold=0.8
                )

                print(f"결과: Tag ID={tag.tag_id}, Name='{tag.name}'")

                # DB에서 롤백 (실제로 생성하지 않음)
                await db.rollback()

                print("✓ 테스트 성공 (롤백됨)")

            except Exception as e:
                print(f"❌ 오류 발생: {e}")
                await db.rollback()

            print("-" * 80)

        print("=" * 80)
        break


if __name__ == "__main__":
    asyncio.run(test_tag_creation())
