# -*- coding: utf-8 -*-
"""DB의 실제 태그 데이터로 유사도 검색 테스트"""
import asyncio
import numpy as np
from sqlalchemy import text
from src.db.session import get_db
from src.core.embedding_service import embedding_service


async def test_similarity_search():
    """실제 DB 데이터로 유사도 검색 테스트"""

    async for db in get_db():
        # 1. "Cloud" 태그의 임베딩 가져오기
        result = await db.execute(
            text("SELECT tag_id, name, embedding FROM tags WHERE name = :name"),
            {"name": "Cloud"}
        )
        cloud_tag = result.fetchone()

        if not cloud_tag:
            print("❌ 'Cloud' 태그를 찾을 수 없습니다.")
            break

        cloud_id, cloud_name, cloud_embedding = cloud_tag
        print("=" * 80)
        print(f"기존 태그: {cloud_name} (ID: {cloud_id})")
        print(f"임베딩 있음: {cloud_embedding is not None}")
        print()

        # 2. "클라우드" 임베딩 생성
        korean_cloud = "클라우드"
        korean_embedding = embedding_service.encode(korean_cloud)

        # 3. 유사도 계산
        if cloud_embedding:
            # pgvector에서 반환된 문자열을 float 배열로 변환
            if isinstance(cloud_embedding, str):
                # "[0.1, 0.2, ...]" 형식에서 리스트로 변환
                cloud_vec = np.array(eval(cloud_embedding))
            else:
                cloud_vec = np.array(cloud_embedding)
            korean_vec = np.array(korean_embedding)

            # Cosine similarity
            similarity = np.dot(cloud_vec, korean_vec) / (np.linalg.norm(cloud_vec) * np.linalg.norm(korean_vec))
            distance = 1 - similarity

            print(f"새 태그: {korean_cloud}")
            print(f"Similarity: {similarity:.4f}")
            print(f"Distance: {distance:.4f}")
            print(f"Threshold 0.8: distance < 0.2? {distance < 0.2} ({'PASS' if distance < 0.2 else 'FAIL'})")
            print()

        # 4. find_similar_tag 쿼리 직접 실행 (수정된 버전)
        print("-" * 80)
        print("수정된 SQL 쿼리 테스트:")
        print("-" * 80)

        threshold = 0.8
        max_distance = 1 - threshold  # 0.2
        embedding_str = f"[{','.join(map(str, korean_embedding.tolist()))}]"

        query = text("""
            SELECT tag_id, name, embedding, created_at,
                   (embedding <=> cast(:embedding as vector)) as distance
            FROM tags
            WHERE embedding IS NOT NULL
              AND (embedding <=> cast(:embedding as vector)) < :max_distance
            ORDER BY distance ASC
            LIMIT 1
        """)

        try:
            result = await db.execute(
                query,
                {"embedding": embedding_str, "max_distance": max_distance}
            )

            row = result.fetchone()

            if row:
                tag_id, name, embedding, created_at, distance = row
                print(f"✓ 유사한 태그 발견:")
                print(f"  - Tag ID: {tag_id}")
                print(f"  - Tag Name: {name}")
                print(f"  - Distance: {distance:.4f}")
                print(f"  - Created At: {created_at}")
                print()
                print(f"✅ 수정된 쿼리가 정상 작동합니다!")
                print(f"   '{korean_cloud}' 검색 시 '{name}' 태그를 찾았습니다.")
            else:
                print(f"❌ 유사한 태그를 찾지 못했습니다.")
                print(f"   threshold: {threshold} (max_distance: {max_distance})")

        except Exception as e:
            print(f"❌ SQL 쿼리 실행 실패:")
            print(f"   {e}")

        print("=" * 80)
        break


if __name__ == "__main__":
    asyncio.run(test_similarity_search())
