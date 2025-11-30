# -*- coding: utf-8 -*-
"""키워드 추출 서비스 (Hybrid: KeyBERT + Elasticsearch Significant Text)"""
from typing import List, Tuple, Set
from abc import ABC, abstractmethod
from src.core.config import settings
from src.core.elasticsearch_client import elasticsearch_client
import logging

logger = logging.getLogger(__name__)

# 영어 불용어 (접속사, 전치사, 관사, 대명사 등)
ENGLISH_STOPWORDS: Set[str] = {
    # 관사
    'a', 'an', 'the',
    # 접속사
    'and', 'or', 'but', 'nor', 'so', 'for', 'yet',
    # 전치사
    'of', 'in', 'on', 'at', 'to', 'by', 'with', 'from', 'up', 'about', 'into',
    'through', 'during', 'before', 'after', 'above', 'below', 'between', 'under',
    'over', 'out', 'off', 'down', 'upon', 'across', 'against', 'along', 'among',
    'around', 'as', 'behind', 'beside', 'besides', 'beyond', 'inside', 'outside',
    'near', 'next', 'onto', 'per', 'since', 'than', 'till', 'toward', 'towards',
    'underneath', 'until', 'via', 'within', 'without',
    # 대명사
    'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
    'my', 'your', 'his', 'its', 'our', 'their', 'mine', 'yours', 'hers', 'ours', 'theirs',
    'this', 'that', 'these', 'those', 'who', 'whom', 'whose', 'which', 'what',
    # be 동사
    'is', 'am', 'are', 'was', 'were', 'be', 'been', 'being',
    # 조동사
    'can', 'could', 'may', 'might', 'must', 'shall', 'should', 'will', 'would',
    # 기타 일반 불용어
    'do', 'does', 'did', 'doing', 'done', 'have', 'has', 'had', 'having',
    'if', 'then', 'else', 'when', 'where', 'why', 'how', 'all', 'any', 'both',
    'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'not', 'only',
    'own', 'same', 'too', 'very', 'just', 'also', 'etc', 'eg', 'ie', 'vs',
}

# 한글 불용어 (조사, 접속사, 대명사 등)
KOREAN_STOPWORDS: Set[str] = {
    # 조사 (확장)
    '이', '가', '을', '를', '은', '는', '에', '에서', '로', '으로', '의', '와', '과',
    '도', '만', '까지', '부터', '한테', '께', '보다', '처럼', '같이', '마다', '조차',
    '에게', '한테서', '께서', '에게서', '로부터', '으로부터', '라고', '이라고',
    '라는', '이라는', '라며', '이라며', '라면', '이라면',
    # 접속사
    '그리고', '또는', '하지만', '그러나', '그래서', '그러므로', '따라서', '즉', '또한',
    # 대명사
    '저', '나', '너', '우리', '그', '이것', '그것', '저것', '여기', '거기', '저기',
    # 지시사
    '이런', '그런', '저런', '이렇게', '그렇게', '저렇게',
    # 의존명사 및 기타
    '등', '및', '또', '더', '덜', '좀', '약', '혹은', '즉', '예를', '들어', '통해',
    '것', '수', '때', '점', '바', '중', '간', '내', '외', '간',
}

# 단일 문자 제외 (너무 짧은 키워드)
MIN_KEYWORD_LENGTH = 2


def is_stopword(keyword: str) -> bool:
    """
    키워드가 불용어인지 확인

    Args:
        keyword: 확인할 키워드

    Returns:
        불용어이면 True, 아니면 False
    """
    keyword_lower = keyword.lower().strip()

    # 길이 체크
    if len(keyword_lower) < MIN_KEYWORD_LENGTH:
        return True

    # 영어 불용어 체크
    if keyword_lower in ENGLISH_STOPWORDS:
        return True

    # 한글 불용어 체크
    if keyword_lower in KOREAN_STOPWORDS:
        return True

    # 숫자만 있는 경우 제외
    if keyword_lower.isdigit():
        return True

    return False


# 한글 조사 목록 (키워드에서 제거할 조사)
KOREAN_PARTICLES = ['이', '가', '을', '를', '은', '는', '에', '에서', '로', '으로', '의', '와', '과', '도', '만']


def remove_particle(keyword: str) -> str:
    """
    키워드 끝에 붙은 조사 제거

    Args:
        keyword: 조사가 붙을 수 있는 키워드

    Returns:
        조사가 제거된 키워드
    """
    keyword = keyword.strip()

    # 한글이 포함된 경우에만 처리
    if any('\uac00' <= c <= '\ud7a3' for c in keyword):
        for particle in KOREAN_PARTICLES:
            if keyword.endswith(particle) and len(keyword) > len(particle) + 1:
                # 조사를 제거한 결과가 의미있는 길이인 경우에만 제거
                candidate = keyword[:-len(particle)]
                if len(candidate) >= MIN_KEYWORD_LENGTH:
                    return candidate

    return keyword


def filter_stopwords(keywords: List[str]) -> List[str]:
    """
    키워드 리스트에서 불용어 제거 및 조사 정리

    Args:
        keywords: 필터링할 키워드 리스트

    Returns:
        불용어가 제거되고 조사가 정리된 키워드 리스트
    """
    filtered = []
    for kw in keywords:
        kw_stripped = kw.strip()
        if not kw_stripped:
            continue

        # 조사 제거
        kw_cleaned = remove_particle(kw_stripped)

        # 단일 키워드인 경우 불용어 체크
        if ' ' not in kw_cleaned:
            if not is_stopword(kw_cleaned):
                filtered.append(kw_cleaned)
        else:
            # 다중 단어 키워드인 경우, 모든 단어가 불용어인지 체크
            words = kw_cleaned.split()
            # 모든 단어가 불용어가 아닌 경우만 포함
            if not all(is_stopword(word) for word in words):
                filtered.append(kw_cleaned)

    return filtered


class KeywordExtractor(ABC): # Abstract Base Class 추상 클래스 생성
    """키워드 추출 인터페이스 (Strategy Pattern)"""

    @abstractmethod
    async def extract_keywords(self, text: str, document_id: int = None) -> List[str]:
        """
        텍스트에서 키워드 추출

        Args:
            text: 대상 텍스트
            document_id: 문서 ID (Elasticsearch 사용 시 필요)

        Returns:
            추출된 키워드 리스트
        """
        pass

    @abstractmethod
    def get_method_name(self) -> str:
        """추출 방법 이름 반환"""
        pass


class KeyBERTExtractor(KeywordExtractor):
    """KeyBERT 기반 키워드 추출기 (Cold Start용)"""

    def __init__(self):
        """KeyBERTExtractor 초기화"""
        self.model = None

    def _load_model(self):
        """KeyBERT 모델 로드 (Lazy Loading)"""
        if self.model is None:
            try:
                from keybert import KeyBERT
                self.model = KeyBERT()
                logger.info("KeyBERT 모델 로드 성공")
            except ImportError:
                logger.error("KeyBERT 라이브러리가 설치되지 않았습니다. 'pip install keybert' 실행 필요")
                raise ImportError("keybert 라이브러리가 필요합니다.")

    async def extract_keywords(self, text: str, document_id: int = None) -> List[str]:
        """
        KeyBERT를 사용하여 키워드 추출

        Args:
            text: 대상 텍스트
            document_id: 사용하지 않음 (인터페이스 일관성 유지)

        Returns:
            추출된 키워드 리스트
        """
        self._load_model()

        try:
            # 여유있게 많이 추출 (필터링 후 개수 보장을 위해)
            keyword_count = settings.KEYWORD_EXTRACTION_COUNT
            # 필터링을 고려하여 3배 정도 많이 추출 (최소 10개)
            extraction_count = max(keyword_count * 3, 10)

            keywords_with_scores = self.model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 2),  # 1~2 단어 구문까지 키워드로 고려
                stop_words='english',  # 영어 불용어 제거(is,a, the 같은 불용어를 키워드에서 제거)
                top_n=extraction_count,  # 충분히 많이 추출
                use_maxsum=True,  # 다양성 증가(키워드 중복 방지)
                nr_candidates=30  # 후보 키워드 수 증가
            )

            # (키워드, 점수) 튜플에서 키워드만 추출
            keywords = [kw[0] for kw in keywords_with_scores]

            logger.info(f"KeyBERT 키워드 추출 완료 ({len(keywords)}개): {keywords}")
            return keywords

        except Exception as e:
            logger.error(f"KeyBERT 키워드 추출 실패: {e}", exc_info=True)
            return []

    def get_method_name(self) -> str:
        return "keybert"


class ElasticsearchExtractor(KeywordExtractor): # 다른 문서들과 비교해서 키워드 추출
    """Elasticsearch Significant Text 기반 키워드 추출기 (Normal용)"""

    async def extract_keywords(self, text: str, document_id: int = None) -> List[str]:
        """
        Elasticsearch Significant Text Aggregation을 사용하여 키워드 추출

        Args:
            text: 사용하지 않음 (Elasticsearch에서 직접 조회)
            document_id: 문서 ID (필수)

        Returns:
            추출된 키워드 리스트
        """
        if document_id is None:
            logger.error("ElasticsearchExtractor는 document_id가 필요합니다.")
            return []

        try:
            # 여유있게 많이 추출 (필터링 후 개수 보장을 위해)
            keyword_count = settings.KEYWORD_EXTRACTION_COUNT
            # 필터링을 고려하여 3배 정도 많이 추출 (최소 10개)
            extraction_count = max(keyword_count * 3, 10)

            keywords = await elasticsearch_client.extract_significant_terms(
                document_id=document_id,
                size=extraction_count  # 충분히 많이 추출
            )

            logger.info(f"Elasticsearch Significant Text 추출 완료 ({len(keywords)}개): {keywords}")
            return keywords

        except Exception as e:
            logger.error(f"Elasticsearch 키워드 추출 실패: {e}", exc_info=True)
            return []

    def get_method_name(self) -> str:
        return "elasticsearch"


class HybridKeywordExtractionService:
    """
    하이브리드 키워드 추출 서비스 (Orchestrator)

    - Cold Start (문서 < 임계값): KeyBERT 사용
    - Normal (문서 >= 임계값): Elasticsearch Significant Text 사용
    """

    def __init__(self):
        """HybridKeywordExtractionService 초기화"""
        self.keybert_extractor = KeyBERTExtractor()
        self.elasticsearch_extractor = ElasticsearchExtractor()
        self.threshold = settings.KEYWORD_EXTRACTION_THRESHOLD

    async def extract_keywords(
        self,
        text: str,
        document_id: int = None
    ) -> Tuple[List[str], str]:
        """
        하이브리드 방식으로 키워드 추출

        Args:
            text: 대상 텍스트
            document_id: 문서 ID (Elasticsearch 사용 시 필요)

        Returns:
            (추출된 키워드 리스트, 사용된 추출 방법)
        """
        # 1. Elasticsearch의 전체 문서 수 확인
        document_count = await elasticsearch_client.get_document_count()

        logger.info(f"현재 Elasticsearch 문서 수: {document_count}, 임계값: {self.threshold}")

        # 2. 임계값 기반 추출 전략 선택 (많이 추출)
        if document_count < self.threshold:
            # Cold Start: KeyBERT 사용
            logger.info(f"Cold Start 모드: KeyBERT 사용 (문서 수: {document_count} < {self.threshold})")
            keywords = await self.keybert_extractor.extract_keywords(text)
            method = self.keybert_extractor.get_method_name()
        else:
            # Normal: Elasticsearch Significant Text 사용
            logger.info(f"Normal 모드: Elasticsearch 사용 (문서 수: {document_count} >= {self.threshold})")
            keywords = await self.elasticsearch_extractor.extract_keywords(text, document_id)
            method = self.elasticsearch_extractor.get_method_name()

        logger.info(f"초기 추출 키워드 ({len(keywords)}개): {keywords}")

        # 3. 불용어 필터링
        keywords = filter_stopwords(keywords)
        logger.info(f"불용어 필터링 후 ({len(keywords)}개): {keywords}")

        # 4. 키워드 정규화 (중복 제거하되 순서 유지)
        # dict.fromkeys()를 사용하여 순서를 유지하면서 중복 제거
        seen = {}
        for kw in keywords:
            kw_normalized = kw.strip().lower()
            if kw_normalized and kw_normalized not in seen:
                seen[kw_normalized] = True
        keywords = list(seen.keys())

        logger.info(f"정규화 후 ({len(keywords)}개): {keywords}")

        # 5. 설정된 개수만큼만 선택 (상위 N개)
        target_count = settings.KEYWORD_EXTRACTION_COUNT
        final_keywords = keywords[:target_count]

        logger.info(f"최종 키워드 ({len(final_keywords)}개): {final_keywords}, 추출 방법: {method}")
        return final_keywords, method


# 전역 키워드 추출 서비스 인스턴스
keyword_extraction_service = HybridKeywordExtractionService()
