# -*- coding: utf-8 -*-
"""Ollama를 이용한 문서 요약 서비스"""
import httpx
from typing import Optional
from src.core.config import settings
import logging

logger = logging.getLogger(__name__)


class OllamaSummarizer:
    """Ollama API를 사용한 문서 요약 서비스"""

    def __init__(self):
        """OllamaSummarizer 초기화"""
        self.ollama_url = settings.OLLAMA_URL
        self.model = settings.OLLAMA_MODEL

    async def summarize(self, text: str, max_length: int = 3000) -> Optional[str]:
        """
        문서 텍스트를 평서문 형식으로 요약

        Args:
            text: 요약할 텍스트
            max_length: 처리할 최대 텍스트 길이 (기본값: 3000자)

        Returns:
            요약된 텍스트 (예: "인공지능 기술의 발전과 미래를 다룬다") 또는 None
        """
        # 텍스트가 너무 짧으면 요약하지 않음
        if not text or len(text.strip()) < 50:
            logger.warning("텍스트가 너무 짧아 요약하지 않습니다.")
            return None

        # 텍스트가 너무 길면 앞부분만 사용
        if len(text) > max_length:
            text = text[:max_length]
            logger.info(f"텍스트가 {max_length}자로 잘렸습니다.")

        # Ollama API 요청 프롬프트
        prompt = f"""다음 문서의 핵심 주제를 한 문장의 평서문으로 요약하세요.
반드시 "~다" 또는 "~한다"로 끝나는 평서문으로만 답변하세요.

예시:
- "인공지능 기술의 발전과 미래 전망을 다룬다"
- "딥러닝 알고리즘 최적화 기법을 설명한다"
- "데이터 구조와 알고리즘의 시간 복잡도를 분석한다"

문서:
{text}

요약:"""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:  # 타임아웃 60초로 증가
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,  # 낮은 temperature로 일관성 있는 요약 생성
                            "num_predict": 50,  # 최대 50 토큰 (더 짧은 요약으로 속도 개선)
                            "num_ctx": 2048,  # 컨텍스트 길이 제한 (메모리 절약)
                        }
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    summary = result.get("response", "").strip()

                    # 후처리: 평서문 형식 정리
                    if summary:
                        # 앞뒤 공백 및 따옴표 제거
                        summary = summary.strip().strip('"').strip("'").strip()

                        # 마침표 제거 (이미 "~다"로 끝남)
                        if summary.endswith('.'):
                            summary = summary[:-1]

                        # 평서문으로 끝나지 않으면 "~를 다룬다" 추가
                        if not (summary.endswith('다') or summary.endswith('한다')):
                            summary = f"{summary}를 다룬다"

                    # 최대 길이 제한 (DB 컬럼 길이에 맞춤: 500자)
                    if len(summary) > 500:
                        summary = summary[:497] + "..."

                    logger.info(f"문서 요약 생성 완료: {summary[:50]}...")
                    return summary
                else:
                    logger.error(f"Ollama API 오류: status_code={response.status_code}")
                    return None

        except httpx.TimeoutException:
            logger.error("Ollama API 요청 시간 초과")
            return None
        except Exception as e:
            logger.error(f"문서 요약 생성 실패: {e}", exc_info=True)
            return None


# 전역 Ollama Summarizer 인스턴스
ollama_summarizer = OllamaSummarizer()
