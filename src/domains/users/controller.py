# -*- coding: utf-8 -*-
"""User 도메인 컨트롤러 (API 엔드포인트)"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.domains.users.repository import UserRepository
from src.domains.users.service import UserService
from src.domains.users.schema import (
    TopicPreferenceResponse,
    ActivityHeatmapResponse,
    ActivityDataPoint
)
from src.core.security import get_current_user_id


router = APIRouter()


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """UserService 의존성 주입"""
    user_repository = UserRepository(db)
    return UserService(user_repository)


@router.get(
    "/stats/topics",
    response_model=TopicPreferenceResponse,
    status_code=status.HTTP_200_OK,
    summary="관심사 분석 (최근 관심 주제)"
)
async def get_topic_preference(
    user_id: int = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    """
    최근 30일 동안 사용자가 가장 많이 조회/업로드한 태그를 집계합니다.

    Args:
        user_id: get_current_user_id 의존성에서 주입된 사용자 ID
        user_service: UserService 의존성 주입

    Returns:
        TopicPreferenceResponse: 태그별 출현 횟수
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"관심사 분석 요청: user_id={user_id}")

    topics = await user_service.get_topic_preference(user_id=user_id)

    logger.info(f"관심사 분석 완료: user_id={user_id}, 태그 개수={len(topics)}")

    return TopicPreferenceResponse(topics=topics)


@router.get(
    "/stats/heatmap",
    response_model=ActivityHeatmapResponse,
    status_code=status.HTTP_200_OK,
    summary="활동 패턴 분석 (히트맵)"
)
async def get_activity_heatmap(
    user_id: int = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    """
    최근 1년간 날짜별 활동 횟수를 집계합니다. (GitHub 잔디 심기 스타일)

    Args:
        user_id: get_current_user_id 의존성에서 주입된 사용자 ID
        user_service: UserService 의존성 주입

    Returns:
        ActivityHeatmapResponse: 날짜별 활동 데이터
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"활동 패턴 분석 요청: user_id={user_id}")

    activities = await user_service.get_activity_heatmap(user_id=user_id)

    logger.info(f"활동 패턴 분석 완료: user_id={user_id}, 데이터 개수={len(activities)}")

    return ActivityHeatmapResponse(
        activities=[
            ActivityDataPoint(date=activity["date"], count=activity["count"])
            for activity in activities
        ]
    )
