# -*- coding: utf-8 -*-
"""Ollama를 이용한 AI 채팅 서비스 (LangChain 기반)"""
import os
from typing import Optional, List
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from src.core.config import settings
import logging

logger = logging.getLogger(__name__)

# LangChain Tracing 설정 (환경 변수 적용)
os.environ["LANGCHAIN_TRACING_V2"] = str(settings.LANGCHAIN_TRACING_V2).lower()
os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT

class OllamaChat:
    """LangChain ChatOllama를 사용한 AI 채팅 서비스"""

    def __init__(self):
        """OllamaChat 초기화"""
        self.llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_URL,
            temperature=0.7,
        )

    async def chat(
        self,
        user_query: str,
        context: str,
        history: List = None,
        max_history: int = 10
    ) -> Optional[str]:
        """
        RAG 기반 채팅 응답 생성

        Args:
            user_query: 사용자 질문
            context: RAG로 검색된 문서 내용 (컨텍스트)
            history: 대화 히스토리 (Message 객체 리스트)
            max_history: 최대 히스토리 개수

        Returns:
            AI 응답 문자열 또는 None
        """
        if not user_query or len(user_query.strip()) < 1:
            logger.warning("사용자 질문이 비어있습니다.")
            return None

        # 1. 메시지 리스트 구성
        messages = []

        # 시스템 프롬프트 추가
        system_prompt = """당신은 문서 내용을 기반으로 질문에 답변하되, 필요시 일반 지식으로 보충하는 AI 어시스턴트입니다.

다음 규칙을 따르세요:
1. 제공된 문서 내용(컨텍스트)을 최우선으로 참고하여 답변하세요.
2. 문서에 관련 내용이 있다면, 해당 부분을 구체적으로 인용하거나 참고했음을 명시하세요.
3. 문서에 충분한 정보가 없거나 추가 설명이 필요한 경우, 일반적인 지식을 활용하여 답변을 보충하세요.
4. 일반 지식으로 보충할 때는 "문서에는 상세 설명이 없지만, 일반적으로...", "추가로 설명하자면..." 같은 표현으로 구분하세요.
5. 답변은 친절하고 자연스러운 한국어로 작성하세요.
6. 문서 기반 정보와 일반 지식을 조화롭게 결합하여 유용한 답변을 제공하세요."""
        
        messages.append(SystemMessage(content=system_prompt))

        # 2. 컨텍스트 추가
        if context:
            logger.info(f"[Ollama] 컨텍스트 추가 - 길이: {len(context)}자")
            messages.append(SystemMessage(content=f"=== 참고 문서 내용 ===\n{context}"))
        else:
            logger.warning("[Ollama] 컨텍스트가 비어있습니다!")

        # 3. 대화 히스토리 추가 (최근 N개만)
        if history:
            recent_history = history[-max_history:]
            logger.info(f"[Ollama] 대화 히스토리 추가 - {len(recent_history)}개 메시지")
            for msg in recent_history:
                if msg.role == "user":
                    messages.append(HumanMessage(content=msg.content))
                elif msg.role == "assistant":
                    messages.append(AIMessage(content=msg.content))

        # 4. 현재 질문 추가
        messages.append(HumanMessage(content=user_query))

        try:
            # 5. LangChain invoke 실행
            logger.info(f"[Ollama] LLM 호출 시작 - 모델: {settings.OLLAMA_MODEL}")
            response = await self.llm.ainvoke(messages)
            
            ai_response = response.content.strip()
            if not ai_response:
                logger.warning("LangChain 응답이 비어있습니다.")
                return "죄송합니다. 응답을 생성할 수 없습니다."

            logger.info(f"AI 응답 생성 완료: {len(ai_response)}자")
            return ai_response

        except Exception as e:
            logger.error(f"Ollama AI 응답 생성 실패: {e}", exc_info=True)
            return None


# 전역 Ollama Chat 인스턴스
ollama_chat = OllamaChat()
