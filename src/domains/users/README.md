# Users 도메인

Users 도메인은 사용자 정보 관리 및 통계/활동 분석 기능을 제공합니다. 사용자의 관심사와 활동 패턴을 분석하여 개인화된 인사이트를 제공합니다.

---

## 아키텍처

```
src/domains/users/
├── models.py       # User, UserActivity 엔티티
├── schema.py       # Pydantic 스키마
├── repository.py   # 데이터 접근 계층
├── service.py      # 비즈니스 로직
└── controller.py   # API 엔드포인트
```

---

## 데이터 모델

### User 모델

사용자 기본 정보를 저장하는 엔티티입니다.

```python
class User(Base):
    user_id: int              # Primary Key
    kakao_id: str             # 카카오 소셜 ID (Unique)
    nickname: str             # 사용자 닉네임
    created_at: datetime      # 가입 일시
```

### UserActivity 모델

사용자 활동 로그를 저장하는 엔티티입니다.

```python
class UserActivity(Base):
    activity_id: int          # Primary Key
    user_id: int              # Foreign Key → User
    document_id: int          # Foreign Key → Document
    activity_type: str        # 활동 유형 (upload, view 등)
    created_at: datetime      # 활동 일시
```

**활동 유형:**
- `upload`: 문서 업로드
- `view`: 문서 조회
- `search`: 문서 검색
- `chat`: AI 채팅

---

## 핵심 기술

### 1. 관심사 분석
- **데이터 소스**: `user_activities` 테이블
- **집계 방식**: SQL JOIN을 통해 활동과 문서 태그 연결
- **기간**: 최근 30일 (기본값)
- **결과**: 태그별 출현 횟수 (상위 5개)

### 2. 활동 패턴 분석
- **데이터 소스**: `user_activities` 테이블
- **집계 방식**: 날짜별 GROUP BY
- **기간**: 최근 365일 (기본값)
- **결과**: GitHub 잔디 심기 스타일의 히트맵 데이터

### 3. 효율적인 쿼리
- **PostgreSQL 집계 쿼리**: COUNT, GROUP BY, ORDER BY
- **인덱싱**: user_id, created_at에 인덱스 적용
- **JOIN 최적화**: INNER JOIN으로 필요한 데이터만 조회

---

## API 엔드포인트

### 1. 관심사 분석 (GET /api/v1/users/stats/topics)

최근 30일 동안 사용자가 가장 많이 조회/업로드한 태그를 집계하여 관심 주제를 분석합니다.

**요청:**
```http
GET /api/v1/users/stats/topics
Cookie: session_id=YOUR_SESSION_ID
```

**응답 (200 OK):**
```json
{
  "topics": {
    "Deep Learning": 15,
    "Backend": 8,
    "Python": 7,
    "FastAPI": 5,
    "Docker": 3
  }
}
```

**응답 필드:**
- `topics`: 태그별 출현 횟수를 나타내는 딕셔너리
  - 키: 태그명
  - 값: 해당 태그가 포함된 문서에 대한 활동 횟수
  - 정렬: 활동 횟수 기준 내림차순
  - 개수: 최대 5개 (상위 5개 태그)

**활용 사례:**
- 사용자 대시보드에 관심 주제 차트 표시
- 추천 시스템에서 사용자 선호도 파악
- 개인화된 문서 추천 기반 데이터
- 사용자 온보딩 시 관심 분야 자동 추천

**기술 스펙:**
```sql
-- 실제 실행되는 쿼리 (간략화)
SELECT t.name AS tag, COUNT(*) AS cnt
FROM user_activities ua
JOIN documents d ON ua.document_id = d.document_id
JOIN document_tags dt ON d.document_id = dt.document_id
JOIN tags t ON dt.tag_id = t.tag_id
WHERE ua.user_id = :user_id
  AND ua.created_at >= NOW() - INTERVAL '30 days'
GROUP BY t.name
ORDER BY cnt DESC
LIMIT 5;
```

---

### 2. 활동 패턴 분석 (GET /api/v1/users/stats/heatmap)

최근 1년간 날짜별 활동 횟수를 집계하여 GitHub 잔디 심기 스타일의 히트맵 데이터를 제공합니다.

**요청:**
```http
GET /api/v1/users/stats/heatmap
Cookie: session_id=YOUR_SESSION_ID
```

**응답 (200 OK):**
```json
{
  "activities": [
    {
      "date": "2025-12-23",
      "count": 8
    },
    {
      "date": "2025-12-22",
      "count": 5
    },
    {
      "date": "2025-12-21",
      "count": 3
    },
    {
      "date": "2025-12-20",
      "count": 0
    }
  ]
}
```

**응답 필드:**
- `activities`: 날짜별 활동 데이터 배열
  - `date`: 날짜 (YYYY-MM-DD 형식)
  - `count`: 해당 날짜의 활동 횟수 (문서 업로드, 조회 등)
  - 정렬: 날짜 기준 내림차순 (최신순)
  - 기간: 최근 365일

**활용 사례:**
- GitHub 스타일의 활동 히트맵 시각화
- 사용자 참여도 분석 및 리텐션 측정
- 활동 패턴 기반 알림 발송 시점 최적화
- 비활성 사용자 탐지 및 리인게이지먼트

**기술 스펙:**
```sql
-- 실제 실행되는 쿼리 (간략화)
SELECT DATE(created_at) AS day, COUNT(*) AS cnt
FROM user_activities
WHERE user_id = :user_id
  AND created_at >= NOW() - INTERVAL '365 days'
GROUP BY day
ORDER BY day DESC;
```

---

## 사용 예시

### cURL 예시

```bash
# 1. 관심사 분석 조회
curl -X GET "http://localhost:8000/api/v1/users/stats/topics" \
  -H "Cookie: session_id=YOUR_SESSION_ID"

# 2. 활동 히트맵 조회
curl -X GET "http://localhost:8000/api/v1/users/stats/heatmap" \
  -H "Cookie: session_id=YOUR_SESSION_ID"
```

### Python 예시

```python
import requests

cookies = {"session_id": "YOUR_SESSION_ID"}

# 관심사 분석 조회
response = requests.get(
    "http://localhost:8000/api/v1/users/stats/topics",
    cookies=cookies
)
topics = response.json()["topics"]
print("관심 주제:")
for tag, count in topics.items():
    print(f"  - {tag}: {count}회")

# 활동 히트맵 조회
response = requests.get(
    "http://localhost:8000/api/v1/users/stats/heatmap",
    cookies=cookies
)
activities = response.json()["activities"]
print(f"\n최근 활동 데이터 {len(activities)}개:")
for activity in activities[:5]:  # 최근 5일만 출력
    print(f"  {activity['date']}: {activity['count']}회")
```

### JavaScript (Fetch API) 예시

```javascript
// 관심사 분석 조회
const topicsResponse = await fetch('http://localhost:8000/api/v1/users/stats/topics', {
  credentials: 'include' // 쿠키 포함
});
const { topics } = await topicsResponse.json();
console.log('관심 주제:', topics);

// 활동 히트맵 조회
const heatmapResponse = await fetch('http://localhost:8000/api/v1/users/stats/heatmap', {
  credentials: 'include'
});
const { activities } = await heatmapResponse.json();
console.log('활동 데이터:', activities);
```

---

## 프론트엔드 연동 예시

### React + Chart.js로 관심사 차트 그리기

```jsx
import { useEffect, useState } from 'react';
import { Pie } from 'react-chartjs-2';

function TopicPreferenceChart() {
  const [topics, setTopics] = useState({});

  useEffect(() => {
    fetch('http://localhost:8000/api/v1/users/stats/topics', {
      credentials: 'include'
    })
      .then(res => res.json())
      .then(data => setTopics(data.topics));
  }, []);

  const chartData = {
    labels: Object.keys(topics),
    datasets: [{
      data: Object.values(topics),
      backgroundColor: [
        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'
      ]
    }]
  };

  return <Pie data={chartData} />;
}
```

### React + GitHub-style 히트맵

```jsx
import { useEffect, useState } from 'react';
import CalendarHeatmap from 'react-calendar-heatmap';
import 'react-calendar-heatmap/dist/styles.css';

function ActivityHeatmap() {
  const [activities, setActivities] = useState([]);

  useEffect(() => {
    fetch('http://localhost:8000/api/v1/users/stats/heatmap', {
      credentials: 'include'
    })
      .then(res => res.json())
      .then(data => setActivities(data.activities));
  }, []);

  return (
    <CalendarHeatmap
      startDate={new Date(new Date().setFullYear(new Date().getFullYear() - 1))}
      endDate={new Date()}
      values={activities}
      classForValue={(value) => {
        if (!value || value.count === 0) return 'color-empty';
        if (value.count < 3) return 'color-scale-1';
        if (value.count < 6) return 'color-scale-2';
        if (value.count < 9) return 'color-scale-3';
        return 'color-scale-4';
      }}
    />
  );
}
```

---

## 비즈니스 로직

### Repository Layer (repository.py)

데이터베이스 쿼리를 담당합니다.

```python
class UserRepository:
    async def get_topic_preference(
        self,
        user_id: int,
        days: int = 30,
        limit: int = 5
    ) -> Dict[str, int]:
        """
        최근 N일간 사용자가 가장 많이 활동한 태그 집계

        Args:
            user_id: 사용자 ID
            days: 조회 기간 (기본 30일)
            limit: 최대 결과 개수 (기본 5개)

        Returns:
            태그별 출현 횟수 딕셔너리 (내림차순 정렬)
        """
        # SQL 쿼리 실행
        # ...
        return {"Python": 10, "FastAPI": 8, ...}

    async def get_activity_heatmap(
        self,
        user_id: int,
        days: int = 365
    ) -> List[Dict[str, Any]]:
        """
        최근 N일간 날짜별 활동 횟수 집계

        Args:
            user_id: 사용자 ID
            days: 조회 기간 (기본 365일)

        Returns:
            날짜별 활동 데이터 리스트 (날짜 내림차순)
        """
        # SQL 쿼리 실행
        # ...
        return [
            {"date": "2025-12-23", "count": 5},
            {"date": "2025-12-22", "count": 3},
            ...
        ]
```

### Service Layer (service.py)

비즈니스 로직을 처리합니다 (현재는 단순 위임).

```python
class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def get_topic_preference(
        self,
        user_id: int,
        days: int = 30,
        limit: int = 5
    ) -> Dict[str, int]:
        """관심 주제 조회"""
        return await self.user_repository.get_topic_preference(
            user_id, days, limit
        )

    async def get_activity_heatmap(
        self,
        user_id: int,
        days: int = 365
    ) -> List[Dict[str, Any]]:
        """활동 히트맵 조회"""
        return await self.user_repository.get_activity_heatmap(
            user_id, days
        )
```

### Controller Layer (controller.py)

HTTP 요청을 처리하고 응답을 반환합니다.

```python
@router.get("/stats/topics", response_model=TopicPreferenceResponse)
async def get_topic_preference(
    user_id: int = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    """관심사 분석 API"""
    topics = await user_service.get_topic_preference(user_id=user_id)
    return TopicPreferenceResponse(topics=topics)

@router.get("/stats/heatmap", response_model=ActivityHeatmapResponse)
async def get_activity_heatmap(
    user_id: int = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    """활동 패턴 분석 API"""
    activities = await user_service.get_activity_heatmap(user_id=user_id)
    return ActivityHeatmapResponse(
        activities=[
            ActivityDataPoint(date=activity["date"], count=activity["count"])
            for activity in activities
        ]
    )
```

---

## 스키마 정의

### 요청 스키마

현재 통계 API는 별도의 요청 바디가 없으며, 인증된 사용자의 쿠키만 필요합니다.

### 응답 스키마

```python
from pydantic import BaseModel, Field
from typing import Dict, List

class TopicPreferenceResponse(BaseModel):
    """관심 주제 분석 응답"""
    topics: Dict[str, int] = Field(
        ...,
        description="태그별 출현 횟수",
        example={"Deep Learning": 15, "Backend": 8}
    )

class ActivityDataPoint(BaseModel):
    """활동 데이터 포인트"""
    date: str = Field(
        ...,
        description="날짜 (YYYY-MM-DD)",
        example="2024-01-01"
    )
    count: int = Field(
        ...,
        description="활동 횟수",
        example=5
    )

class ActivityHeatmapResponse(BaseModel):
    """활동 히트맵 응답"""
    activities: List[ActivityDataPoint] = Field(
        ...,
        description="날짜별 활동 데이터"
    )
```

---

## 성능 최적화

### 1. 인덱스 전략

```sql
-- user_activities 테이블에 복합 인덱스 추가
CREATE INDEX idx_user_activities_user_created
ON user_activities(user_id, created_at DESC);

-- document_tags 테이블에 인덱스 추가
CREATE INDEX idx_document_tags_document
ON document_tags(document_id);
```

### 2. 쿼리 최적화

- **INNER JOIN만 사용**: LEFT JOIN 대신 INNER JOIN으로 불필요한 NULL 처리 제거
- **서브쿼리 회피**: JOIN으로 한 번에 처리
- **날짜 필터 먼저**: WHERE 절에서 날짜 조건을 먼저 적용하여 스캔 범위 축소

### 3. 캐싱 전략 (향후 개선)

```python
# Redis 캐싱 예시 (향후 추가 가능)
from functools import wraps

def cache_result(ttl: int = 300):
    """결과를 Redis에 캐싱 (5분)"""
    def decorator(func):
        @wraps(func)
        async def wrapper(user_id: int, *args, **kwargs):
            cache_key = f"user_stats:{func.__name__}:{user_id}"
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)

            result = await func(user_id, *args, **kwargs)
            await redis_client.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator

# 사용 예시
@cache_result(ttl=300)
async def get_topic_preference(user_id: int, days: int = 30, limit: int = 5):
    # ...
```

---

## 테스트

### 단위 테스트 구조

```
tests/unit/domains/users/
├── __init__.py
└── test_user_stats.py
    ├── TestUserRepositoryTopicPreference
    ├── TestUserRepositoryActivityHeatmap
    ├── TestUserServiceStats
    └── TestUserStatsEndpoints
```

### 테스트 실행

```bash
# 전체 Users 도메인 테스트
pytest tests/unit/domains/users/ -v

# 특정 테스트 클래스만 실행
pytest tests/unit/domains/users/test_user_stats.py::TestUserStatsEndpoints -v

# 커버리지 포함
pytest tests/unit/domains/users/ --cov=src.domains.users --cov-report=html
```

### 테스트 예시

```python
class TestUserStatsEndpoints:
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
        assert data["topics"]["Python"] == 15

        # Cleanup
        app.dependency_overrides.clear()
```

---

## 에러 처리

### 일반적인 에러 응답

| Status Code | 설명 | 발생 시점 |
|------------|------|----------|
| 401 Unauthorized | 인증되지 않은 사용자 | 유효하지 않은 세션으로 API 호출 |
| 500 Internal Server Error | 서버 오류 | DB 연결 실패, 쿼리 에러 등 |

### 에러 응답 예시

```json
{
  "detail": "인증이 필요합니다"
}
```

---

## 향후 개선 방향

### 1. 고급 분석 기능
- **활동 트렌드**: 주간/월간 활동 증가율 분석
- **피크 타임**: 사용자가 가장 활동적인 시간대 분석
- **문서 타입 선호도**: PDF, Word 등 선호하는 파일 형식 분석

### 2. 추천 시스템 연동
- 관심 주제 기반 문서 추천
- 유사한 관심사를 가진 사용자 발견
- 태그 기반 협업 필터링

### 3. 성능 개선
- Redis 캐싱 도입 (5분 TTL)
- 배치 집계 작업 (매일 자정 사전 계산)
- Materialized View 활용

### 4. 알림 기능
- 비활성 사용자 리인게이지먼트
- 새로운 관심 주제 발견 알림
- 주간 활동 리포트 이메일

---

## 관련 문서

- [Auth 도메인](../auth/README.md) - 사용자 인증 및 세션 관리
- [Documents 도메인](../documents/README.md) - 문서 업로드 및 활동 로깅
- [Tags 도메인](../tags/README.md) - 태그 시스템
- [Core 모듈](../../core/README.md) - 인프라 및 유틸리티
