# -*- coding: utf-8 -*-
"""태그 유사도 테스트 스크립트"""
import numpy as np
from src.core.embedding_service import embedding_service


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    코사인 유사도 계산

    Args:
        vec1: 첫 번째 벡터
        vec2: 두 번째 벡터

    Returns:
        코사인 유사도 (0.0 ~ 1.0)
    """
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    return dot_product / (norm1 * norm2)


def cosine_distance(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    코사인 거리 계산 (pgvector의 <=> 연산자와 동일)

    Args:
        vec1: 첫 번째 벡터
        vec2: 두 번째 벡터

    Returns:
        코사인 거리 (0.0 ~ 2.0, 작을수록 유사)
    """
    return 1 - cosine_similarity(vec1, vec2)


def test_tag_pairs():
    """다양한 태그 쌍의 유사도 테스트"""

    test_pairs = [
        ("Cloud", "클라우드"),
        ("Cloud", "cloud"),
        ("클라우드", "클라우드 컴퓨팅"),
        ("Computing", "컴퓨팅"),
        ("Principles", "원리"),
        ("Database", "데이터베이스"),
        ("API", "API"),
        ("Python", "Java"),  # 다른 개념
        ("Dog", "Cat"),  # 완전히 다른 개념
    ]

    print("=" * 80)
    print("태그 유사도 테스트")
    print("=" * 80)
    print(f"{'Tag 1':<20} {'Tag 2':<20} {'Similarity':>12} {'Distance':>12} {'Threshold 0.8':>15}")
    print("-" * 80)

    for tag1, tag2 in test_pairs:
        # 임베딩 생성
        emb1 = embedding_service.encode(tag1)
        emb2 = embedding_service.encode(tag2)

        # 유사도 계산
        similarity = cosine_similarity(emb1, emb2)
        distance = cosine_distance(emb1, emb2)

        # threshold 0.8 기준 (distance < 0.2)
        max_distance = 1 - 0.8  # 0.2
        passes_threshold = "✓ PASS" if distance < max_distance else "✗ FAIL"

        print(f"{tag1:<20} {tag2:<20} {similarity:>12.4f} {distance:>12.4f} {passes_threshold:>15}")

    print("=" * 80)
    print("\n설명:")
    print("- Similarity: 1.0에 가까울수록 유사 (cosine similarity)")
    print("- Distance: 0.0에 가까울수록 유사 (cosine distance, pgvector <=> 연산자)")
    print("- Threshold 0.8: distance < 0.2이면 PASS (유사한 태그로 간주)")
    print()


if __name__ == "__main__":
    test_tag_pairs()
