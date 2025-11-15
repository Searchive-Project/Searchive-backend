# -*- coding: utf-8 -*-
"""임베딩 벡터 생성 서비스 (Sentence Transformers)"""
from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    태그 임베딩 생성 및 유사도 계산 서비스

    - Sentence Transformers의 다국어 모델 사용
    - 384차원 벡터 생성 (paraphrase-multilingual-MiniLM-L12-v2)
    - 한국어, 영어 모두 지원
    """

    def __init__(self, model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2'):
        """
        EmbeddingService 초기화

        Args:
            model_name: 사용할 Sentence Transformer 모델 이름
                        기본값: paraphrase-multilingual-MiniLM-L12-v2 (384차원)
        """
        self.model_name = model_name
        self.model = None
        self._embedding_dim = 384  # 모델의 임베딩 차원

    def _load_model(self):
        """모델 로드 (Lazy Loading)"""
        if self.model is None:
            try:
                logger.info(f"임베딩 모델 로드 중: {self.model_name}")
                self.model = SentenceTransformer(self.model_name)
                logger.info(f"임베딩 모델 로드 완료: {self.model_name} (차원: {self._embedding_dim})")
            except Exception as e:
                logger.error(f"임베딩 모델 로드 실패: {e}", exc_info=True)
                raise RuntimeError(f"임베딩 모델 로드 실패: {e}")

    def encode(self, text: Union[str, List[str]]) -> Union[np.ndarray, List[np.ndarray]]:
        """
        텍스트를 임베딩 벡터로 변환

        Args:
            text: 단일 텍스트 또는 텍스트 리스트

        Returns:
            임베딩 벡터 (numpy array) 또는 벡터 리스트
        """
        self._load_model()

        try:
            if isinstance(text, str):
                # 단일 텍스트
                embedding = self.model.encode(text, convert_to_numpy=True)
                logger.debug(f"임베딩 생성 완료: '{text[:50]}...' -> {embedding.shape}")
                return embedding
            else:
                # 텍스트 리스트
                embeddings = self.model.encode(text, convert_to_numpy=True)
                logger.debug(f"임베딩 {len(text)}개 생성 완료")
                return embeddings
        except Exception as e:
            logger.error(f"임베딩 생성 실패: {e}", exc_info=True)
            raise RuntimeError(f"임베딩 생성 실패: {e}")

    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        두 임베딩 벡터 간의 코사인 유사도 계산

        Args:
            embedding1: 첫 번째 임베딩 벡터
            embedding2: 두 번째 임베딩 벡터

        Returns:
            코사인 유사도 (-1 ~ 1, 1에 가까울수록 유사)
        """
        try:
            # 코사인 유사도 = (A·B) / (||A|| * ||B||)
            dot_product = np.dot(embedding1, embedding2)
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
        except Exception as e:
            logger.error(f"유사도 계산 실패: {e}", exc_info=True)
            return 0.0

    def find_most_similar(
        self,
        query_embedding: np.ndarray,
        candidate_embeddings: List[np.ndarray],
        threshold: float = 0.8
    ) -> tuple[int, float]:
        """
        쿼리 임베딩과 가장 유사한 후보 임베딩 찾기

        Args:
            query_embedding: 쿼리 임베딩 벡터
            candidate_embeddings: 후보 임베딩 벡터 리스트
            threshold: 최소 유사도 임계값 (기본값: 0.8)

        Returns:
            (가장 유사한 후보의 인덱스, 유사도 점수)
            유사도가 임계값 이하면 (-1, 0.0) 반환
        """
        if not candidate_embeddings:
            return -1, 0.0

        max_similarity = -1.0
        max_index = -1

        for idx, candidate_embedding in enumerate(candidate_embeddings):
            similarity = self.compute_similarity(query_embedding, candidate_embedding)
            if similarity > max_similarity:
                max_similarity = similarity
                max_index = idx

        # 임계값보다 높은 유사도를 가진 후보가 있는 경우에만 반환
        if max_similarity >= threshold:
            return max_index, max_similarity
        else:
            return -1, 0.0

    @property
    def embedding_dim(self) -> int:
        """임베딩 벡터 차원 반환"""
        return self._embedding_dim


# 전역 임베딩 서비스 인스턴스
embedding_service = EmbeddingService()
