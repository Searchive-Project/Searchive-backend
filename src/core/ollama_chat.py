# -*- coding: utf-8 -*-
"""Ollama를 이용한 AI 채팅 서비스 (RAG 방식)"""
import httpx
from typing import Optional, List
from src.core.config import settings
import logging

logger = logging.getLogger(__name__)


class OllamaChat:
    """Ollama API를 사용한 AI 채팅 서비스"""

    def __init__(self):
        """OllamaChat 초기화"""
        self.ollama_url = settings.OLLAMA_URL
        self.model = settings.OLLAMA_MODEL

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

        # 1. 시스템 프롬프트 구성
        system_prompt = """당신은 문서 내용을 기반으로 질문에 답변하되, 필요시 일반 지식으로 보충하는 AI 어시스턴트입니다.

다음 규칙을 따르세요:
1. 제공된 문서 내용(컨텍스트)을 최우선으로 참고하여 답변하세요.
2. 문서에 관련 내용이 있다면, 해당 부분을 구체적으로 인용하거나 참고했음을 명시하세요.
3. 문서에 충분한 정보가 없거나 추가 설명이 필요한 경우, 일반적인 지식을 활용하여 답변을 보충하세요.
4. 일반 지식으로 보충할 때는 "문서에는 상세 설명이 없지만, 일반적으로...", "추가로 설명하자면..." 같은 표현으로 구분하세요.
5. 답변은 친절하고 자연스러운 한국어로 작성하세요.
6. 문서 기반 정보와 일반 지식을 조화롭게 결합하여 유용한 답변을 제공하세요."""

        # 2. 컨텍스트 추가
        prompt_parts = [system_prompt]

        if context:
            logger.info(f"[Ollama] 컨텍스트 추가 - 길이: {len(context)}자")
            prompt_parts.append(f"\n\n=== 참고 문서 내용 ===\n{context}")
        else:
            logger.warning("[Ollama] 컨텍스트가 비어있습니다!")

        # 3. 대화 히스토리 추가 (최근 N개만)
        if history:
            recent_history = history[-max_history:]
            logger.info(f"[Ollama] 대화 히스토리 추가 - {len(recent_history)}개 메시지")
            history_text = "\n\n=== 이전 대화 ===\n"
            for msg in recent_history:
                role_label = "사용자" if msg.role == "user" else "AI"
                history_text += f"{role_label}: {msg.content}\n"
            prompt_parts.append(history_text)

        # 4. 현재 질문 추가
        prompt_parts.append(f"\n\n=== 현재 질문 ===\n사용자: {user_query}\n\nAI:")

        # 5. 최종 프롬프트
        full_prompt = "".join(prompt_parts)
        logger.info(f"[Ollama] 최종 프롬프트 길이: {len(full_prompt)}자")
        logger.debug(f"[Ollama] 프롬프트 미리보기:\n{full_prompt[:1000]}...")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,  # 창의성과 정확성의 균형
                            "num_predict": 512,  # 최대 512 토큰 (긴 답변 허용)
                            "num_ctx": 2048,  # 컨텍스트 길이 (문서 내용 + 히스토리)
                            "top_k": 40,
                            "top_p": 0.9,
                        }
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    ai_response = result.get("response", "").strip()

                    if not ai_response:
                        logger.warning("Ollama 응답이 비어있습니다.")
                        return "죄송합니다. 응답을 생성할 수 없습니다."

                    logger.info(f"AI 응답 생성 완료: {len(ai_response)}자")
                    return ai_response
                else:
                    logger.error(f"Ollama API 오류: status_code={response.status_code}")
                    return None

        except httpx.TimeoutException:
            logger.error("Ollama API 요청 시간 초과")
            return None
        except Exception as e:
            logger.error(f"AI 응답 생성 실패: {e}", exc_info=True)
            return None


# 전역 Ollama Chat 인스턴스
ollama_chat = OllamaChat()
