# -*- coding: utf-8 -*-
"""User 도메인 Service"""
from typing import Optional, List, Dict
from src.domains.users.repository import UserRepository
from src.domains.users.models import User, UserActivity


class UserService:
    """User 비즈니스 로직 처리 계층"""

    def __init__(self, user_repository: UserRepository):
        """
        UserService 초기화

        Args:
            user_repository: UserRepository 인스턴스
        """
        self.user_repository = user_repository

    async def get_or_create_user(self, kakao_id: str, nickname: str) -> tuple[User, bool]:
        """
        카카오 ID로 사용자 조회, 없으면 생성

        Args:
            kakao_id: 카카오 소셜 ID
            nickname: 사용자 닉네임

        Returns:
            (User 객체, 신규 생성 여부)
        """
        user = await self.user_repository.find_by_kakao_id(kakao_id)

        if user:
            return user, False

        # 신규 사용자 생성
        new_user = await self.user_repository.create(kakao_id, nickname)
        return new_user, True

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        사용자 ID로 사용자 조회

        Args:
            user_id: 사용자 고유 ID

        Returns:
            User 객체 또는 None
        """
        return await self.user_repository.find_by_user_id(user_id)

    async def get_user_by_kakao_id(self, kakao_id: str) -> Optional[User]:
        """
        카카오 ID로 사용자 조회

        Args:
            kakao_id: 카카오 소셜 ID

        Returns:
            User 객체 또는 None
        """
        return await self.user_repository.find_by_kakao_id(kakao_id)

    async def update_nickname(self, user_id: int, nickname: str) -> Optional[User]:
        """
        사용자 닉네임 업데이트

        Args:
            user_id: 사용자 고유 ID
            nickname: 새로운 닉네임

        Returns:
            업데이트된 User 객체 또는 None
        """
        return await self.user_repository.update_nickname(user_id, nickname)

    async def delete_user(self, user_id: int) -> bool:
        """
        사용자 삭제

        Args:
            user_id: 사용자 고유 ID

        Returns:
            삭제 성공 여부
        """
        return await self.user_repository.delete(user_id)

    async def log_activity(self, user_id: int, activity_type: str, tags: List[str], doc_id: Optional[int] = None) -> UserActivity:
        """
        사용자 활동 로그 기록

        Args:
            user_id: 사용자 ID
            activity_type: 활동 타입 ('VIEW' 또는 'UPLOAD')
            tags: 태그 리스트
            doc_id: 문서 ID (선택)

        Returns:
            생성된 UserActivity 객체
        """
        return await self.user_repository.log_activity(user_id, activity_type, tags, doc_id)

    async def get_topic_preference(self, user_id: int, days: int = 30, limit: int = 5) -> Dict[str, int]:
        """
        최근 N일 동안 사용자의 관심 주제(태그) 집계

        Args:
            user_id: 사용자 ID
            days: 집계할 기간 (기본값: 30일)
            limit: 반환할 최대 태그 개수 (기본값: 5)

        Returns:
            {"태그명": 출현횟수} 형식의 딕셔너리
        """
        return await self.user_repository.get_topic_preference(user_id, days, limit)

    async def get_activity_heatmap(self, user_id: int, days: int = 365) -> List[Dict[str, any]]:
        """
        최근 N일 동안 날짜별 활동 횟수 집계

        Args:
            user_id: 사용자 ID
            days: 집계할 기간 (기본값: 365일)

        Returns:
            [{"date": "2024-01-01", "count": 5}, ...] 형식의 리스트
        """
        return await self.user_repository.get_activity_heatmap(user_id, days)
