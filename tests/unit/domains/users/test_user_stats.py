# -*- coding: utf-8 -*-
"""User 통계 API 테스트"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.users.repository import UserRepository
from src.domains.users.service import UserService
from src.domains.users.models import User, UserActivity


# ============================================
# UserRepository Tests - Topic Preference
# ============================================

class TestUserRepositoryTopicPreference:
    """UserRepository.get_topic_preference 테스트"""

    @pytest.fixture
    def mock_db(self):
        """Mock AsyncSession"""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def user_repository(self, mock_db):
        """UserRepository 인스턴스"""
        return UserRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_topic_preference_with_data(self, user_repository, mock_db):
        """태그 데이터가 있을 때 정상 집계"""
        # Mock 결과 설정
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            MagicMock(tag="Python", cnt=10),
            MagicMock(tag="FastAPI", cnt=8),
            MagicMock(tag="SQLAlchemy", cnt=5),
        ]
        mock_db.execute.return_value = mock_result

        # 실행
        result = await user_repository.get_topic_preference(user_id=1, days=30, limit=5)

        # 검증
        assert result == {
            "Python": 10,
            "FastAPI": 8,
            "SQLAlchemy": 5
        }
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_topic_preference_no_data(self, user_repository, mock_db):
        """활동 기록이 없을 때 빈 딕셔너리 반환"""
        # Mock 결과 설정
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        # 실행
        result = await user_repository.get_topic_preference(user_id=999, days=30, limit=5)

        # 검증
        assert result == {}
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_topic_preference_custom_params(self, user_repository, mock_db):
        """커스텀 days, limit 파라미터 전달 테스트"""
        # Mock 결과 설정
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            MagicMock(tag="AI", cnt=20),
        ]
        mock_db.execute.return_value = mock_result

        # 실행 - 7일, 최대 3개
        result = await user_repository.get_topic_preference(user_id=1, days=7, limit=3)

        # 검증
        assert result == {"AI": 20}

        # execute 호출 시 전달된 파라미터 확인
        call_args = mock_db.execute.call_args
        assert call_args[0][1]["days"] == 7
        assert call_args[0][1]["limit"] == 3


# ============================================
# UserRepository Tests - Activity Heatmap
# ============================================

class TestUserRepositoryActivityHeatmap:
    """UserRepository.get_activity_heatmap 테스트"""

    @pytest.fixture
    def mock_db(self):
        """Mock AsyncSession"""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def user_repository(self, mock_db):
        """UserRepository 인스턴스"""
        return UserRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_activity_heatmap_with_data(self, user_repository, mock_db):
        """활동 데이터가 있을 때 정상 집계"""
        # Mock 결과 설정
        from datetime import date
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            MagicMock(day=date(2025, 12, 23), cnt=5),
            MagicMock(day=date(2025, 12, 22), cnt=3),
            MagicMock(day=date(2025, 12, 21), cnt=7),
        ]
        mock_db.execute.return_value = mock_result

        # 실행
        result = await user_repository.get_activity_heatmap(user_id=1, days=365)

        # 검증
        assert len(result) == 3
        assert result[0] == {"date": "2025-12-23", "count": 5}
        assert result[1] == {"date": "2025-12-22", "count": 3}
        assert result[2] == {"date": "2025-12-21", "count": 7}
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_activity_heatmap_no_data(self, user_repository, mock_db):
        """활동 기록이 없을 때 빈 리스트 반환"""
        # Mock 결과 설정
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        # 실행
        result = await user_repository.get_activity_heatmap(user_id=999, days=365)

        # 검증
        assert result == []
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_activity_heatmap_custom_days(self, user_repository, mock_db):
        """커스텀 days 파라미터 전달 테스트"""
        # Mock 결과 설정
        from datetime import date
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            MagicMock(day=date(2025, 12, 23), cnt=2),
        ]
        mock_db.execute.return_value = mock_result

        # 실행 - 최근 7일
        result = await user_repository.get_activity_heatmap(user_id=1, days=7)

        # 검증
        assert len(result) == 1
        assert result[0]["count"] == 2

        # execute 호출 시 전달된 파라미터 확인
        call_args = mock_db.execute.call_args
        assert call_args[0][1]["days"] == 7


# ============================================
# UserService Tests
# ============================================

class TestUserServiceStats:
    """UserService 통계 메서드 테스트"""

    @pytest.fixture
    def mock_repository(self):
        """Mock UserRepository"""
        return AsyncMock(spec=UserRepository)

    @pytest.fixture
    def user_service(self, mock_repository):
        """UserService 인스턴스"""
        return UserService(mock_repository)

    @pytest.mark.asyncio
    async def test_get_topic_preference(self, user_service, mock_repository):
        """관심 주제 조회 서비스 레이어 테스트"""
        # Mock 설정
        mock_repository.get_topic_preference.return_value = {
            "Python": 10,
            "FastAPI": 8
        }

        # 실행
        result = await user_service.get_topic_preference(user_id=1, days=30, limit=5)

        # 검증
        assert result == {"Python": 10, "FastAPI": 8}
        mock_repository.get_topic_preference.assert_called_once_with(1, 30, 5)

    @pytest.mark.asyncio
    async def test_get_topic_preference_default_params(self, user_service, mock_repository):
        """기본 파라미터로 호출 시 테스트"""
        # Mock 설정
        mock_repository.get_topic_preference.return_value = {}

        # 실행 - 기본값 사용
        result = await user_service.get_topic_preference(user_id=1)

        # 검증
        assert result == {}
        mock_repository.get_topic_preference.assert_called_once_with(1, 30, 5)

    @pytest.mark.asyncio
    async def test_get_activity_heatmap(self, user_service, mock_repository):
        """활동 히트맵 조회 서비스 레이어 테스트"""
        # Mock 설정
        mock_repository.get_activity_heatmap.return_value = [
            {"date": "2025-12-23", "count": 5},
            {"date": "2025-12-22", "count": 3}
        ]

        # 실행
        result = await user_service.get_activity_heatmap(user_id=1, days=365)

        # 검증
        assert len(result) == 2
        assert result[0]["count"] == 5
        mock_repository.get_activity_heatmap.assert_called_once_with(1, 365)

    @pytest.mark.asyncio
    async def test_get_activity_heatmap_default_days(self, user_service, mock_repository):
        """기본 days 파라미터로 호출 시 테스트"""
        # Mock 설정
        mock_repository.get_activity_heatmap.return_value = []

        # 실행 - 기본값 365일 사용
        result = await user_service.get_activity_heatmap(user_id=1)

        # 검증
        assert result == []
        mock_repository.get_activity_heatmap.assert_called_once_with(1, 365)


# ============================================
# API Endpoint Tests (Integration)
# ============================================

class TestUserStatsEndpoints:
    """User 통계 API 엔드포인트 테스트"""

    @pytest.mark.asyncio
    async def test_get_topic_preference_endpoint_success(self):
        """관심 주제 API 성공 케이스"""
        mock_service = AsyncMock(spec=UserService)
        mock_service.get_topic_preference.return_value = {
            "Python": 15,
            "FastAPI": 10,
            "Docker": 5
        }

        # Mock 의존성 주입
        from src.domains.users.controller import get_user_service
        from src.core.security import get_current_user_id
        from fastapi.testclient import TestClient
        from src.main import app

        app.dependency_overrides[get_current_user_id] = lambda: 1
        app.dependency_overrides[get_user_service] = lambda: mock_service

        client = TestClient(app)
        response = client.get("/api/v1/users/stats/topics")

        # 검증
        assert response.status_code == 200
        data = response.json()
        assert "topics" in data
        assert data["topics"]["Python"] == 15
        assert data["topics"]["FastAPI"] == 10
        assert data["topics"]["Docker"] == 5

        # Cleanup
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_topic_preference_endpoint_no_data(self):
        """관심 주제 API - 데이터 없을 때"""
        mock_service = AsyncMock(spec=UserService)
        mock_service.get_topic_preference.return_value = {}

        from src.domains.users.controller import get_user_service
        from src.core.security import get_current_user_id
        from fastapi.testclient import TestClient
        from src.main import app

        app.dependency_overrides[get_current_user_id] = lambda: 999
        app.dependency_overrides[get_user_service] = lambda: mock_service

        client = TestClient(app)
        response = client.get("/api/v1/users/stats/topics")

        # 검증
        assert response.status_code == 200
        data = response.json()
        assert data["topics"] == {}

        # Cleanup
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_activity_heatmap_endpoint_success(self):
        """활동 히트맵 API 성공 케이스"""
        mock_service = AsyncMock(spec=UserService)
        mock_service.get_activity_heatmap.return_value = [
            {"date": "2025-12-23", "count": 5},
            {"date": "2025-12-22", "count": 3},
            {"date": "2025-12-21", "count": 8}
        ]

        from src.domains.users.controller import get_user_service
        from src.core.security import get_current_user_id
        from fastapi.testclient import TestClient
        from src.main import app

        app.dependency_overrides[get_current_user_id] = lambda: 1
        app.dependency_overrides[get_user_service] = lambda: mock_service

        client = TestClient(app)
        response = client.get("/api/v1/users/stats/heatmap")

        # 검증
        assert response.status_code == 200
        data = response.json()
        assert "activities" in data
        assert len(data["activities"]) == 3
        assert data["activities"][0]["date"] == "2025-12-23"
        assert data["activities"][0]["count"] == 5

        # Cleanup
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_activity_heatmap_endpoint_no_data(self):
        """활동 히트맵 API - 데이터 없을 때"""
        mock_service = AsyncMock(spec=UserService)
        mock_service.get_activity_heatmap.return_value = []

        from src.domains.users.controller import get_user_service
        from src.core.security import get_current_user_id
        from fastapi.testclient import TestClient
        from src.main import app

        app.dependency_overrides[get_current_user_id] = lambda: 999
        app.dependency_overrides[get_user_service] = lambda: mock_service

        client = TestClient(app)
        response = client.get("/api/v1/users/stats/heatmap")

        # 검증
        assert response.status_code == 200
        data = response.json()
        assert data["activities"] == []

        # Cleanup
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_endpoints_require_authentication(self):
        """인증 없이 API 호출 시 401 반환"""
        from fastapi.testclient import TestClient
        from src.main import app
        from src.core.security import get_current_user_id
        from fastapi import HTTPException, status

        def mock_auth_fail():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="인증이 필요합니다"
            )

        app.dependency_overrides[get_current_user_id] = mock_auth_fail

        client = TestClient(app)

        # 관심 주제 API
        response1 = client.get("/api/v1/users/stats/topics")
        assert response1.status_code == 401

        # 활동 히트맵 API
        response2 = client.get("/api/v1/users/stats/heatmap")
        assert response2.status_code == 401

        # Cleanup
        app.dependency_overrides.clear()
