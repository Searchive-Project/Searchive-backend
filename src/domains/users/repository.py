# -*- coding: utf-8 -*-
"""User 도메인 Repository"""
from typing import Optional, List, Dict
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from src.domains.users.models import User, UserActivity


class UserRepository:
    """User 엔티티 데이터 접근 계층"""

    def __init__(self, db: AsyncSession):
        """
        UserRepository 초기화

        Args:
            db: SQLAlchemy AsyncSession
        """
        self.db = db

    async def find_by_kakao_id(self, kakao_id: str) -> Optional[User]:
        """
        카카오 ID로 사용자 조회

        Args:
            kakao_id: 카카오 소셜 ID

        Returns:
            User 객체 또는 None
        """
        result = await self.db.execute(
            select(User).where(User.kakao_id == kakao_id)
        )
        return result.scalar_one_or_none()

    async def find_by_user_id(self, user_id: int) -> Optional[User]:
        """
        사용자 ID로 사용자 조회

        Args:
            user_id: 사용자 고유 ID

        Returns:
            User 객체 또는 None
        """
        result = await self.db.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, kakao_id: str, nickname: str) -> User:
        """
        신규 사용자 생성

        Args:
            kakao_id: 카카오 소셜 ID
            nickname: 사용자 닉네임

        Returns:
            생성된 User 객체
        """
        user = User(
            kakao_id=kakao_id,
            nickname=nickname
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_nickname(self, user_id: int, nickname: str) -> Optional[User]:
        """
        사용자 닉네임 업데이트

        Args:
            user_id: 사용자 고유 ID
            nickname: 새로운 닉네임

        Returns:
            업데이트된 User 객체 또는 None (사용자 없을 경우)
        """
        user = await self.find_by_user_id(user_id)
        if not user:
            return None

        user.nickname = nickname
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def delete(self, user_id: int) -> bool:
        """
        사용자 삭제

        Args:
            user_id: 사용자 고유 ID

        Returns:
            삭제 성공 여부
        """
        user = await self.find_by_user_id(user_id)
        if not user:
            return False

        await self.db.delete(user)
        await self.db.commit()
        return True

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
        meta_data = {"tags": tags}
        if doc_id:
            meta_data["doc_id"] = doc_id

        activity = UserActivity(
            user_id=user_id,
            activity_type=activity_type,
            meta_data=meta_data
        )
        self.db.add(activity)
        await self.db.commit()
        await self.db.refresh(activity)
        return activity

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
        query = text("""
            SELECT tag, COUNT(*) as cnt
            FROM user_activities, jsonb_array_elements_text(meta_data->'tags') as tag
            WHERE user_id = :uid
              AND created_at > NOW() - (INTERVAL '1 day' * :days)
            GROUP BY tag
            ORDER BY cnt DESC
            LIMIT :limit
        """)

        result = await self.db.execute(
            query,
            {"uid": user_id, "days": days, "limit": limit}
        )

        return {row.tag: row.cnt for row in result.fetchall()}

    async def get_activity_heatmap(self, user_id: int, days: int = 365) -> List[Dict[str, any]]:
        """
        최근 N일 동안 날짜별 활동 횟수 집계

        Args:
            user_id: 사용자 ID
            days: 집계할 기간 (기본값: 365일)

        Returns:
            [{"date": "2024-01-01", "count": 5}, ...] 형식의 리스트
        """
        query = text("""
            SELECT date(created_at) as day, COUNT(*) as cnt
            FROM user_activities
            WHERE user_id = :uid
              AND created_at > NOW() - (INTERVAL '1 day' * :days)
            GROUP BY day
            ORDER BY day ASC
        """)

        result = await self.db.execute(
            query,
            {"uid": user_id, "days": days}
        )

        return [{"date": str(row.day), "count": row.cnt} for row in result.fetchall()]
