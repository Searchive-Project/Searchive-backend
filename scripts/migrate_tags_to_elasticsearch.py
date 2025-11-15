# -*- coding: utf-8 -*-
"""
기존 태그 데이터를 Elasticsearch로 마이그레이션하는 스크립트

사용법:
    python scripts/migrate_tags_to_elasticsearch.py

설명:
    PostgreSQL의 tags 테이블에 있는 모든 태그 데이터를 Elasticsearch의 tags 인덱스로 마이그레이션합니다.
    임베딩 벡터를 포함하여 색인하므로, 벡터 유사도 검색이 가능합니다.
"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트 경로를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.core.config import settings
from src.core.elasticsearch_client import elasticsearch_client
from src.domains.tags.models import Tag


async def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("태그 데이터 Elasticsearch 마이그레이션 스크립트")
    print("=" * 60)
    print()

    # 1. Elasticsearch 연결
    print("[1/4] Elasticsearch 연결 중...")
    await elasticsearch_client.connect()
    print("✅ Elasticsearch 연결 성공")

    # 2. Tags 인덱스 생성 (이미 존재하면 스킵)
    print()
    print("[2/4] Tags 인덱스 확인 및 생성 중...")
    await elasticsearch_client.create_tags_index_if_not_exists()
    print("✅ Tags 인덱스 준비 완료")

    # 3. PostgreSQL에서 기존 태그 데이터 로드
    print()
    print("[3/4] PostgreSQL에서 기존 태그 데이터 로드 중...")

    # AsyncEngine 생성
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    tags_data = []

    async with async_session() as session:
        # 모든 태그 조회
        result = await session.execute(select(Tag))
        tags = result.scalars().all()

        print(f"📌 총 {len(tags)}개의 태그를 발견했습니다.")

        if len(tags) == 0:
            print("⚠️  마이그레이션할 태그가 없습니다.")
            await elasticsearch_client.close()
            await engine.dispose()
            return

        # 태그 데이터 준비
        for idx, tag in enumerate(tags, 1):
            try:
                # 임베딩이 있는 태그만 마이그레이션
                if tag.embedding is not None:
                    tags_data.append({
                        "tag_id": tag.tag_id,
                        "name": tag.name,
                        "embedding": tag.embedding,
                        "created_at": tag.created_at.isoformat() if tag.created_at else None
                    })
                    print(f"  ✓ [{idx}/{len(tags)}] {tag.name} (ID: {tag.tag_id})")
                else:
                    print(f"  ⚠️  [{idx}/{len(tags)}] {tag.name} (ID: {tag.tag_id}) - 임베딩 없음, 스킵")

            except Exception as e:
                print(f"  ❌ [{idx}/{len(tags)}] {tag.name} (ID: {tag.tag_id}) - 오류: {e}")

        print(f"✅ {len(tags_data)}개 태그의 데이터 준비 완료")

    await engine.dispose()

    # 4. Elasticsearch에 태그 색인
    if len(tags_data) > 0:
        print()
        print(f"[4/4] {len(tags_data)}개 태그를 Elasticsearch에 색인 중...")

        success_count = 0
        failed_count = 0

        for idx, tag_data in enumerate(tags_data, 1):
            try:
                success = await elasticsearch_client.index_tag(
                    tag_id=tag_data["tag_id"],
                    name=tag_data["name"],
                    embedding=tag_data["embedding"],
                    created_at=tag_data["created_at"]
                )

                if success:
                    success_count += 1
                    print(f"  ✓ [{idx}/{len(tags_data)}] {tag_data['name']} (ID: {tag_data['tag_id']})")
                else:
                    failed_count += 1
                    print(f"  ❌ [{idx}/{len(tags_data)}] {tag_data['name']} (ID: {tag_data['tag_id']}) - 색인 실패")

            except Exception as e:
                failed_count += 1
                print(f"  ❌ [{idx}/{len(tags_data)}] {tag_data['name']} (ID: {tag_data['tag_id']}) - 오류: {e}")

        print()
        print(f"✅ 색인 완료: 성공 {success_count}개, 실패 {failed_count}개")

        if failed_count > 0:
            print("⚠️  일부 태그 색인 실패. 로그를 확인하세요.")

    else:
        print()
        print("[4/4] 색인할 태그가 없습니다.")

    # 종료
    await elasticsearch_client.close()

    print()
    print("=" * 60)
    print("마이그레이션 완료!")
    print("=" * 60)
    print()
    print("이제 Elasticsearch를 사용한 고속 벡터 검색이 가능합니다.")
    print("새로운 태그 추가 시 자동으로 Elasticsearch에 색인됩니다.")
    print()


if __name__ == "__main__":
    asyncio.run(main())
