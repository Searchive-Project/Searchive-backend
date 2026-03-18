# -*- coding: utf-8 -*-
"""Gemini(OpenAI-Compatible)를 이용한 문서 요약 서비스 (LangChain 기반)"""
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.core.config import settings
import logging
import re

logger = logging.getLogger(__name__)


class GeminiSummarizer:
    """LangChain ChatOpenAI(Gemini Compatible)를 사용한 문서 요약 서비스"""

    def __init__(self):
        """GeminiSummarizer 초기화"""
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL_NAME,
            openai_api_key=settings.OPENAI_API_KEY,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            temperature=0.3,  # 낮은 temperature로 일관성 있는 요약 생성
        )
        
        # 요약 프롬프트 템플릿 설정
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """아래 문서 내용을 읽고, 핵심 주제를 한 문장으로 새롭게 작성하세요.
원본 텍스트를 그대로 복사하지 말고, 내용을 이해한 후 간결하게 요약하세요.
반드시 "~다" 또는 "~한다"로 끝나는 평서문으로 답변하세요.

좋은 예시:
- "인공지능 기술의 발전과 미래 전망을 다룬다"
- "딥러닝 알고리즘 최적화 기법을 설명한다"
- "데이터 구조와 알고리즘의 시간 복잡도를 분석한다" """),
            ("human", "문서:\n{text}\n\n요약 (한 문장):")
        ])
        
        # 체인 구성
        self.chain = self.prompt | self.llm | StrOutputParser()

    async def summarize(self, text: str, max_length: int = 1500) -> Optional[str]:
        """
        문서 텍스트를 평서문 형식으로 요약

        Args:
            text: 요약할 텍스트
            max_length: 처리할 최대 텍스트 길이 (기본값: 1500자)

        Returns:
            요약된 텍스트 (예: "인공지능 기술의 발전과 미래를 다룬다") 또는 None
        """
        # 텍스트가 너무 짧으면 요약하지 않음
        if not text or len(text.strip()) < 50:
            logger.warning("텍스트가 너무 짧아 요약하지 않습니다.")
            return None

        # 텍스트 전처리: 마크다운 제거
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)
        text = re.sub(r'\n\s*\n', '\n', text)
        text = text.strip()

        # 텍스트가 너무 길면 앞부분만 사용 (속도 최적화)
        if len(text) > max_length:
            text = text[:max_length]
            logger.info(f"텍스트가 {max_length}자로 잘렸습니다.")

        try:
            # LangChain 체인 실행
            logger.info("[Gemini] 요약 생성 시작")
            summary = await self.chain.ainvoke({"text": text})
            summary = summary.strip()

            if summary:
                # 후처리: 한 줄로 정리
                summary = summary.replace('\n', ' ').replace('\r', ' ')
                summary = re.sub(r'\s+', ' ', summary)
                summary = summary.strip().strip('"').strip("'").strip()

                # 마침표 제거
                if summary.endswith('.'):
                    summary = summary[:-1]

                # 평서문 형식 보정
                if not (summary.endswith('다') or summary.endswith('한다')):
                    summary = f"{summary}를 다룬다"

                # 길이 제한 (DB 컬럼: 500자)
                if len(summary) > 500:
                    summary = summary[:497] + "..."

                logger.info(f"문서 요약 생성 완료: {summary[:50]}...")
                return summary
            
            return None

        except Exception as e:
            logger.error(f"Gemini 요약 생성 실패: {e}", exc_info=True)
            return None


# 전역 Gemini Summarizer 인스턴스 (기존 ollama_summarizer 변수명 유지하여 호환성 확보)
ollama_summarizer = GeminiSummarizer()
