# -*- coding: utf-8 -*-
"""불용어 필터링 테스트 스크립트"""
from src.core.keyword_extraction import is_stopword, filter_stopwords


def test_stopword_filtering():
    """불용어 필터링 기능 테스트"""

    # 테스트 케이스: (입력 키워드, 기대 결과)
    test_cases = [
        # 영어 불용어
        ("of", True, "영어 전치사"),
        ("the", True, "영어 관사"),
        ("and", True, "영어 접속사"),
        ("is", True, "영어 be 동사"),
        ("a", True, "영어 관사"),
        ("in", True, "영어 전치사"),
        ("to", True, "영어 전치사"),
        ("for", True, "영어 전치사/접속사"),

        # 한글 불용어
        ("이", True, "한글 조사"),
        ("가", True, "한글 조사"),
        ("은", True, "한글 조사"),
        ("는", True, "한글 조사"),
        ("의", True, "한글 조사"),
        ("등", True, "한글 기타"),
        ("및", True, "한글 접속사"),

        # 유효한 키워드
        ("cloud", False, "영어 명사"),
        ("computing", False, "영어 명사"),
        ("database", False, "영어 명사"),
        ("클라우드", False, "한글 명사"),
        ("컴퓨팅", False, "한글 명사"),
        ("데이터베이스", False, "한글 명사"),
        ("machine learning", False, "영어 다중 단어"),
        ("인공지능", False, "한글 복합어"),

        # 짧은 키워드
        ("a", True, "단일 문자"),
        ("i", True, "단일 문자"),

        # 숫자
        ("123", True, "숫자만"),
        ("2024", True, "연도"),

        # 대소문자 혼합
        ("Of", True, "대문자 불용어"),
        ("THE", True, "대문자 불용어"),
        ("Cloud", False, "대문자 유효 키워드"),
    ]

    print("=" * 80)
    print("불용어 필터링 테스트")
    print("=" * 80)
    print(f"{'키워드':<20} {'예상':<10} {'실제':<10} {'결과':<10} {'설명'}")
    print("-" * 80)

    passed = 0
    failed = 0

    for keyword, expected, description in test_cases:
        result = is_stopword(keyword)
        status = "✓ PASS" if result == expected else "✗ FAIL"

        if result == expected:
            passed += 1
        else:
            failed += 1

        print(f"{keyword:<20} {str(expected):<10} {str(result):<10} {status:<10} {description}")

    print("-" * 80)
    print(f"총 테스트: {len(test_cases)}개")
    print(f"통과: {passed}개")
    print(f"실패: {failed}개")
    print("=" * 80)
    print()


def test_filter_stopwords_list():
    """키워드 리스트 필터링 테스트"""

    test_cases = [
        {
            "input": ["cloud", "of", "computing", "the", "database"],
            "expected": ["cloud", "computing", "database"],
            "description": "영어 불용어 제거"
        },
        {
            "input": ["클라우드", "의", "컴퓨팅", "및", "데이터베이스"],
            "expected": ["클라우드", "컴퓨팅", "데이터베이스"],
            "description": "한글 불용어 제거"
        },
        {
            "input": ["cloud computing", "of the", "machine learning"],
            "expected": ["cloud computing", "machine learning"],
            "description": "다중 단어 키워드 필터링"
        },
        {
            "input": ["Cloud", "Of", "Computing"],
            "expected": ["Cloud", "Computing"],
            "description": "대소문자 혼합"
        },
        {
            "input": ["a", "i", "123", "cloud"],
            "expected": ["cloud"],
            "description": "단일 문자 및 숫자 제거"
        },
    ]

    print("=" * 80)
    print("키워드 리스트 필터링 테스트")
    print("=" * 80)

    for i, test_case in enumerate(test_cases, 1):
        input_keywords = test_case["input"]
        expected_output = test_case["expected"]
        description = test_case["description"]

        result = filter_stopwords(input_keywords)

        # 순서와 무관하게 비교 (set 사용)
        result_set = set(result)
        expected_set = set(expected_output)

        status = "✓ PASS" if result_set == expected_set else "✗ FAIL"

        print(f"\n테스트 {i}: {description}")
        print(f"입력:    {input_keywords}")
        print(f"예상:    {expected_output}")
        print(f"결과:    {result}")
        print(f"상태:    {status}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_stopword_filtering()
    print()
    test_filter_stopwords_list()
