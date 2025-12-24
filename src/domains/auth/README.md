# Auth 도메인

Auth 도메인은 사용자 인증 및 세션 관리 기능을 담당합니다. 카카오 OAuth 2.0을 통한 소셜 로그인과 Redis 기반 세션 관리를 제공합니다.

---

## 아키텍처

```
src/domains/auth/
├── controller.py           # API 엔드포인트
├── schema/
│   ├── request.py         # 요청 스키마
│   └── response.py        # 응답 스키마
└── service/
    ├── kakao_service.py   # 카카오 OAuth 서비스
    └── session_service.py # 세션 관리 서비스
```

---

## 핵심 기술

- **OAuth 2.0**: 카카오 소셜 로그인
- **세션 관리**: Redis 기반 세션 스토어 (1시간 TTL)
- **보안**: HttpOnly 쿠키, 코드 재사용 방지 락

---

## API 엔드포인트

### 1. 카카오 로그인 시작 (GET /api/v1/auth/kakao/login)

카카오 인증 서버로 리디렉트하여 사용자 인증을 시작합니다.

**요청:**
```http
GET /api/v1/auth/kakao/login
```

**응답:**
- Status: `302 Found`
- Location: `https://kauth.kakao.com/oauth/authorize?...`

**워크플로우:**
1. 카카오 인증 URL 생성 (client_id, redirect_uri 포함)
2. 사용자를 카카오 로그인 페이지로 리디렉트

---

### 2. 카카오 인증 콜백 (GET /api/v1/auth/kakao/callback)

카카오로부터 받은 인가 코드로 사용자를 인증하고 세션을 생성합니다.

**요청:**
```http
GET /api/v1/auth/kakao/callback?code=AUTHORIZATION_CODE
```

**Query Parameters:**
- `code`: 카카오로부터 받은 인가 코드

**응답:**
- Status: `302 Found`
- Location: `{FRONTEND_URL}/auth/kakao/callback`
- Set-Cookie: `session_id=...; HttpOnly; Max-Age=3600; SameSite=Lax`

**워크플로우:**
1. 코드 중복 사용 방지를 위한 Redis 락 설정 (30초)
2. 카카오 API로 액세스 토큰 요청
3. 액세스 토큰으로 사용자 정보 조회 (kakao_id, nickname)
4. DB에서 사용자 조회 또는 신규 생성 (Get-or-Create 패턴)
5. Redis에 세션 생성 (`session:{session_id}` → `{"user_id": user_id}`)
6. HttpOnly 쿠키에 session_id 설정
7. 프론트엔드 콜백 URL로 리디렉트

**보안 기능:**
- 코드 재사용 방지: Redis 락으로 동시 요청 차단
- HttpOnly 쿠키: XSS 공격 방지
- SameSite=Lax: CSRF 공격 방지

---

### 3. 세션 정보 조회 (GET /api/v1/auth/session)

현재 로그인된 사용자의 세션 정보를 반환합니다.

**요청:**
```http
GET /api/v1/auth/session
Cookie: session_id=YOUR_SESSION_ID
```

**응답 (200 OK):**
```json
{
  "user_id": 1,
  "session_id": "abc123..."
}
```

**응답 필드:**
- `user_id`: 사용자 고유 ID
- `session_id`: 현재 세션 ID

**인증:**
- `get_current_user_id` 의존성을 통해 세션 유효성 검증
- 유효하지 않은 세션인 경우 401 Unauthorized 반환

---

### 4. 현재 사용자 정보 조회 (GET /api/v1/auth/me)

현재 로그인된 사용자의 상세 정보를 반환합니다.

**요청:**
```http
GET /api/v1/auth/me
Cookie: session_id=YOUR_SESSION_ID
```

**응답 (200 OK):**
```json
{
  "user_id": 1,
  "kakao_id": "1234567890",
  "nickname": "홍길동",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**응답 필드:**
- `user_id`: 사용자 고유 ID
- `kakao_id`: 카카오 소셜 ID
- `nickname`: 사용자 닉네임
- `created_at`: 계정 생성 일시

**에러 응답:**
- `401 Unauthorized`: 인증되지 않은 사용자
- `404 Not Found`: 사용자를 찾을 수 없음

---

### 5. 로그아웃 (POST /api/v1/auth/logout)

Redis에서 세션을 삭제하고 쿠키를 만료시킵니다.

**요청:**
```http
POST /api/v1/auth/logout
Cookie: session_id=YOUR_SESSION_ID
```

**응답 (200 OK):**
```json
{
  "message": "로그아웃 성공"
}
```

**동작:**
1. 쿠키에서 session_id 추출
2. Redis에서 `session:{session_id}` 키 삭제
3. 응답 헤더에 쿠키 삭제 지시 (`Set-Cookie: session_id=; Max-Age=0`)

**특징:**
- session_id가 없어도 200 OK 반환 (멱등성 보장)
- 쿠키 삭제로 클라이언트에서도 세션 정보 제거

---

### 6. 테스트 로그인 (POST /api/v1/auth/test/login) [개발 전용]

개발 환경에서만 사용 가능한 테스트 로그인 엔드포인트입니다. 카카오 OAuth 없이 직접 로그인할 수 있습니다.

**요청:**
```http
POST /api/v1/auth/test/login?kakao_id=test_user_123
```

**Query Parameters:**
- `kakao_id`: 로그인할 카카오 ID (예: "test_user_123")

**응답 (200 OK):**
```json
{
  "message": "테스트 로그인 성공",
  "user_id": 1,
  "kakao_id": "test_user_123",
  "nickname": "테스트유저_test_user_123"
}
```

**제한사항:**
- `APP_ENV=development`일 때만 사용 가능
- 운영 환경에서 호출 시 403 Forbidden 반환

**사용 목적:**
- 로컬 개발 시 카카오 OAuth 우회
- API 테스트 자동화
- 프론트엔드 개발 시 간편한 인증

---

## 사용 예시

### 카카오 로그인 플로우 (프론트엔드)

```javascript
// 1. 로그인 버튼 클릭 시 카카오 로그인 페이지로 이동
window.location.href = 'http://localhost:8000/api/v1/auth/kakao/login';

// 2. 카카오 인증 후 콜백 페이지에서 세션 확인
// URL: http://frontend.com/auth/kakao/callback
// 쿠키에 session_id가 자동으로 설정됨

// 3. 현재 사용자 정보 조회
const response = await fetch('http://localhost:8000/api/v1/auth/me', {
  credentials: 'include' // 쿠키 포함
});
const user = await response.json();
console.log('로그인된 사용자:', user);

// 4. 로그아웃
await fetch('http://localhost:8000/api/v1/auth/logout', {
  method: 'POST',
  credentials: 'include'
});
```

### 테스트 로그인 (개발 환경)

```bash
# cURL
curl -X POST "http://localhost:8000/api/v1/auth/test/login?kakao_id=test123" \
  -c cookies.txt

# 세션 정보 확인
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -b cookies.txt
```

```python
# Python
import requests

# 테스트 로그인
session = requests.Session()
response = session.post(
    'http://localhost:8000/api/v1/auth/test/login',
    params={'kakao_id': 'test123'}
)
print(response.json())

# 자동으로 쿠키가 저장되어 이후 요청에 포함됨
me = session.get('http://localhost:8000/api/v1/auth/me')
print('현재 사용자:', me.json())
```

---

## 세션 관리

### Redis 세션 구조

```
Key: session:{session_id}
Value: {"user_id": 123}
TTL: 3600초 (1시간)
```

### 세션 검증 (의존성 주입)

```python
from src.core.security import get_current_user_id
from fastapi import Depends

@router.get("/protected")
async def protected_route(user_id: int = Depends(get_current_user_id)):
    # user_id는 자동으로 세션에서 추출됨
    # 유효하지 않은 세션인 경우 401 에러 발생
    return {"message": f"안녕하세요, 사용자 {user_id}님!"}
```

### 세션 생명주기

1. **생성**: 카카오 로그인 콜백 시 또는 테스트 로그인 시
2. **갱신**: 자동 갱신 없음 (1시간 고정)
3. **삭제**: 로그아웃 시 또는 1시간 후 자동 만료

---

## 환경 변수

Auth 도메인에서 사용하는 환경 변수:

```bash
# 카카오 OAuth 설정
KAKAO_CLIENT_ID=your_kakao_app_key
KAKAO_CLIENT_SECRET=your_kakao_client_secret
KAKAO_REDIRECT_URI=http://localhost:8000/api/v1/auth/kakao/callback

# 프론트엔드 URL (콜백 후 리디렉트 대상)
FRONTEND_URL=http://localhost:3000

# 앱 환경 (development/production)
APP_ENV=development

# Redis 설정 (세션 저장)
REDIS_HOST=localhost
REDIS_PORT=6379
```

---

## 에러 처리

### 일반적인 에러 응답

| Status Code | 설명 | 발생 시점 |
|------------|------|----------|
| 401 Unauthorized | 인증되지 않은 사용자 | 유효하지 않은 세션으로 보호된 API 호출 |
| 403 Forbidden | 권한 없음 | 운영 환경에서 테스트 로그인 시도 |
| 404 Not Found | 사용자를 찾을 수 없음 | /me 호출 시 사용자 삭제됨 |
| 409 Conflict | 충돌 | 카카오 인가 코드 중복 사용 시도 |
| 500 Internal Server Error | 서버 오류 | 카카오 API 통신 실패 등 |

### 에러 응답 예시

```json
{
  "detail": "인증이 필요합니다"
}
```

---

## 보안 고려사항

### 1. 코드 재사용 방지
- 카카오 인가 코드는 일회용
- Redis 락으로 동시 요청 차단 (30초 TTL)
- 동일 코드로 두 번째 요청 시 409 Conflict 반환

### 2. 세션 보안
- HttpOnly 쿠키: JavaScript에서 접근 불가 (XSS 방지)
- SameSite=Lax: CSRF 공격 방지
- 1시간 자동 만료

### 3. 환경 분리
- 테스트 로그인은 개발 환경에서만 활성화
- 운영 환경에서는 카카오 OAuth만 허용

### 4. 로깅
- 모든 인증 이벤트 로깅 (로그인, 로그아웃, 세션 생성 등)
- 민감 정보 마스킹 (session_id는 앞 10자만 로깅)

---

## 카카오 OAuth 플로우 다이어그램

```
사용자           프론트엔드         백엔드(Auth)      카카오 API        Redis         PostgreSQL
  │                 │                 │                │               │              │
  │  로그인 클릭     │                 │                │               │              │
  ├────────────────>│                 │                │               │              │
  │                 │  GET /kakao/login │              │               │              │
  │                 ├────────────────>│                │               │              │
  │                 │  302 Redirect   │                │               │              │
  │                 │<────────────────┤                │               │              │
  │<────────────────┤                 │                │               │              │
  │                                   │                │               │              │
  │         카카오 로그인 화면         │                │               │              │
  │<──────────────────────────────────┤                │               │              │
  │  ID/PW 입력 & 동의               │                │               │              │
  ├──────────────────────────────────>│                │               │              │
  │                                   │                │               │              │
  │  Redirect with code               │                │               │              │
  │<──────────────────────────────────┤                │               │              │
  │                 │                 │                │               │              │
  │                 │  GET /kakao/callback?code=XXX     │               │              │
  │                 ├────────────────>│                │               │              │
  │                 │                 │  Redis Lock    │               │              │
  │                 │                 ├───────────────────────────────>│              │
  │                 │                 │  토큰 요청      │               │              │
  │                 │                 ├───────────────>│               │              │
  │                 │                 │  Access Token  │               │              │
  │                 │                 │<───────────────┤               │              │
  │                 │                 │  사용자 정보    │               │              │
  │                 │                 ├───────────────>│               │              │
  │                 │                 │  User Info     │               │              │
  │                 │                 │<───────────────┤               │              │
  │                 │                 │  Get or Create User            │              │
  │                 │                 ├──────────────────────────────────────────────>│
  │                 │                 │  User                          │              │
  │                 │                 │<──────────────────────────────────────────────┤
  │                 │                 │  Create Session                │              │
  │                 │                 ├───────────────────────────────>│              │
  │                 │  302 Redirect   │                                │              │
  │                 │  Set-Cookie     │                                │              │
  │                 │<────────────────┤                                │              │
  │<────────────────┤                 │                                │              │
```

---

## 트러블슈팅

### 문제: "인증이 필요합니다" 에러

**원인:**
- 세션 쿠키가 전송되지 않음
- 세션이 만료됨 (1시간 경과)

**해결:**
- 프론트엔드에서 `credentials: 'include'` 옵션 사용
- 재로그인 유도

### 문제: "로그인 처리 중입니다" 에러 (409 Conflict)

**원인:**
- 카카오 인가 코드를 동시에 두 번 사용
- 브라우저가 콜백 URL을 중복 호출

**해결:**
- 자동으로 해결됨 (30초 후 락 해제)
- 페이지 새로고침 방지

### 문제: 카카오 로그인 후 403 에러

**원인:**
- KAKAO_CLIENT_ID 또는 KAKAO_CLIENT_SECRET 불일치
- KAKAO_REDIRECT_URI가 카카오 앱 설정과 다름

**해결:**
- .env 파일의 카카오 설정 확인
- 카카오 개발자 콘솔에서 Redirect URI 확인

---

## 관련 문서

- [Users 도메인](../users/README.md) - 사용자 정보 관리 및 통계
- [Documents 도메인](../documents/README.md) - 문서 업로드 및 권한 검증
- [Core 보안 모듈](../../core/README.md) - JWT 및 세션 유틸리티
