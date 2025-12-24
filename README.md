# Searchive Backend

Searchive 프로젝트의 핵심 두뇌 역할을 하는 Python/FastAPI 기반 API 서버입니다. 사용자 인증, 문서 관리, 검색, 그리고 지능형 RAG 파이프라인을 총괄합니다.

---

## ✨ 아키텍처: 도메인 주도 계층형 아키텍처

본 프로젝트는 유지보수성과 확장성을 극대화하기 위해 **도메인 주도 설계(Domain-Driven Design)**의 개념을 도입한 계층형 아키텍처를 따릅니다. 모든 소스 코드는 `src/domains` 폴더 아래에 각 기능(도메인)별로 그룹화됩니다.

### 각 계층의 역할

-   **`router.py` (Controller/API Layer)**: HTTP 요청을 받아 유효성을 검사하고, 적절한 서비스로 요청을 전달하는 API 엔드포인트 계층입니다.
-   **`schemas.py` (DTO Layer)**: Pydantic 모델을 사용하여 API 요청 및 응답의 데이터 구조를 정의하고 유효성을 검사합니다.
-   **`services.py` (Service/Business Logic Layer)**: 실제 비즈니스 로직을 수행합니다. 여러 리포지토리를 조합하여 복잡한 작업을 처리합니다.
-   **`repositories.py` (Data Access Layer)**: 데이터베이스와의 상호작용을 담당하며, CRUD 연산을 추상화합니다.
-   **`models.py` (Domain/Entity Layer)**: SQLAlchemy ORM 모델로, 데이터베이스 테이블 구조를 정의합니다.

---

## 📂 폴더 구조

```
Searchive-backend/
├── .env                    # 실제 환경 변수 파일 (Git 무시)
├── .env_example            # 환경 변수 예시 파일
├── .gitignore              # Git 무시 목록
├── alembic/                # Alembic 마이그레이션 스크립트 저장 폴더
│   ├── versions/           # 마이그레이션 버전 파일들
│   ├── env.py              # Alembic 환경 설정
│   ├── script.py.mako      # 마이그레이션 템플릿
│   └── README
├── alembic.ini             # Alembic 설정 파일
├── requirements.txt        # Python 의존성 목록
├── pytest.ini              # Pytest 설정 파일
├── README.md               # 프로젝트 설명 파일 (이 파일)
├── docs/                   # 문서 폴더
│   ├── NORI_SETUP.md       # Elasticsearch Nori 형태소 분석기 설정 가이드
│   └── ...
├── scripts/                # 유틸리티 스크립트
│   ├── reindex_with_nori.py  # Elasticsearch 재색인 스크립트
│   ├── migrate_tags_to_elasticsearch.py  # 태그 Elasticsearch 마이그레이션 스크립트
│   └── check_tag_embeddings.py  # 태그 임베딩 검증 스크립트
├── tests/                  # 테스트 코드
│   ├── __init__.py
│   ├── conftest.py         # Pytest 설정 및 픽스처
│   ├── README.md           # 테스트 가이드
│   ├── fixtures/           # 테스트용 샘플 파일
│   ├── unit/               # 단위 테스트
│   │   └── domains/
│   │       ├── documents/  # 문서 도메인 단위 테스트
│   │       └── tags/       # 태그 도메인 단위 테스트
│   └── integration/        # 통합 테스트
│       └── domains/
└── src/                    # 소스 코드 루트
    ├── __init__.py
    ├── main.py             # FastAPI 앱 생성 및 라우터 포함
    ├── core/               # 프로젝트 핵심 인프라 (상세: src/core/README.md)
    │   ├── __init__.py
    │   ├── README.md       # ✨ Core 모듈 상세 가이드 (Elasticsearch, MinIO, TextExtractor, KeyBERT)
    │   ├── config.py       # 환경 변수 관리
    │   ├── exception.py    # 예외 처리 핸들러
    │   ├── redis.py        # Redis 세션 관리
    │   ├── security.py     # JWT 보안 유틸리티
    │   ├── minio_client.py # MinIO 객체 스토리지 클라이언트
    │   ├── elasticsearch_client.py  # Elasticsearch 검색 엔진 클라이언트
    │   ├── text_extractor.py        # 파일 → 텍스트 추출기 (PDF, DOCX, HWP 등)
    │   ├── keyword_extraction.py    # AI 키워드 추출 (KeyBERT, Elasticsearch TF-IDF)
    │   └── embedding_service.py     # 텍스트 임베딩 서비스 (Sentence Transformers)
    ├── db/                 # 데이터베이스 연결 및 세션 관리
    │   ├── __init__.py
    │   └── session.py
    └── domains/            # ✨ 핵심: 도메인별 모듈 (상세: src/domains/README.md)
        ├── __init__.py
        ├── README.md       # ✨ 도메인 아키텍처 상세 가이드 (DDD, 계층형 아키텍처)
        ├── auth/           # 인증 도메인
        │   ├── controller.py   # API 엔드포인트
        │   ├── schema/         # Pydantic 스키마
        │   └── service/        # 비즈니스 로직 (카카오 OAuth, 세션 관리)
        ├── users/          # 사용자 도메인
        │   ├── models.py       # User 엔티티 모델
        │   ├── schema.py       # User Pydantic 스키마
        │   ├── repository.py   # User 데이터 접근 계층
        │   └── service.py      # User 비즈니스 로직
        ├── documents/      # 문서 관리 도메인 (상세: src/domains/documents/README.md)
        │   ├── README.md       # ✨ Documents 도메인 상세 가이드 (업로드 워크플로우, AI 태깅)
        │   ├── models.py       # Document 엔티티 모델
        │   ├── schema.py       # Document Pydantic 스키마
        │   ├── repository.py   # Document 데이터 접근 계층
        │   ├── service.py      # Document 비즈니스 로직
        │   └── controller.py   # Document API 엔드포인트
        ├── tags/           # 태그 시스템 도메인 (상세: src/domains/tags/README.md)
        │   ├── README.md       # ✨ Tags 도메인 상세 가이드 (Get-or-Create, N+1 방지)
        │   ├── models.py       # Tag, DocumentTag 엔티티 모델
        │   ├── schema.py       # Tag Pydantic 스키마
        │   ├── repository.py   # Tag 데이터 접근 계층
        │   └── service.py      # Tag 비즈니스 로직
        └── aichat/         # AI 채팅 도메인
            ├── __init__.py
            ├── models.py       # Conversation, Message, ConversationDocument 엔티티 모델
            ├── schema.py       # AIChat Pydantic 스키마
            ├── repository.py   # AIChat 데이터 접근 계층
            ├── service.py      # AIChat 비즈니스 로직 (RAG 파이프라인)
            └── controller.py   # AIChat API 엔드포인트
```

---

## 🛠️ 기술 스택

-   **Framework**: FastAPI
-   **Database**: PostgreSQL (SQLAlchemy ORM, Alembic)
-   **Cache**: Redis
-   **Search**: Elasticsearch
-   **Object Storage**: MinIO
-   **Data Validation**: Pydantic
-   **AI Frameworks**:
    -   LangChain, LangGraph (RAG 파이프라인)
    -   KeyBERT (키워드 추출)
    -   Sentence Transformers (임베딩)
    -   Ollama (로컬 LLM)
-   **Async Runtime**: Uvicorn

---

## 🏁 시작하기 (Getting Started)

### 1. 레포지토리 클론 및 가상 환경 설정

```bash
git clone https://github.com/Chaehyunli/Searchive-backend.git 
cd Searchive-backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

`.env_example` 파일을 복사하여 `.env` 파일을 생성하고, `Searchive-db` 스택의 접속 정보를 입력합니다.

```bash
cp .env_example .env
```

그 후 `.env` 파일을 열어 데이터베이스 정보 및 API 키를 설정합니다.

**필수 환경 변수:**
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`: PostgreSQL 설정
- `REDIS_HOST`, `REDIS_PORT`: Redis 설정
- `ELASTICSEARCH_HOST`, `ELASTICSEARCH_PORT`: Elasticsearch 설정
- `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`: MinIO 설정
- `KEYWORD_EXTRACTION_COUNT`: 자동 태그 추출 개수 (기본값: 3)
- `KAKAO_CLIENT_ID`, `KAKAO_CLIENT_SECRET`: 카카오 OAuth 설정
- `OLLAMA_HOST`: Ollama 서버 주소 (AI 채팅 기능 사용)

### 4. DB 인프라 실행

`Searchive-db` 레포지토리에서 `docker compose up -d`를 실행하여 모든 데이터베이스를 준비시킵니다.

### 5. 데이터베이스 마이그레이션

백엔드 서버를 실행하기 전에, 아래 명령어로 데이터베이스 스키마를 생성합니다.

```bash
# Alembic 초기화 (최초 1회만)
alembic init alembic

# 마이그레이션 파일 생성
alembic revision --autogenerate -m "Initial migration"

# 마이그레이션 실행
alembic upgrade head
```

### 6. 서버 실행

```bash
# 개발 모드 (자동 리로드)
.\venv\Scripts\activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 또는
# python src/main.py
```

서버가 실행되면 다음 URL에서 확인할 수 있습니다:

-   API 서버: http://localhost:8000
-   API 문서 (Swagger): http://localhost:8000/docs
-   API 문서 (ReDoc): http://localhost:8000/redoc

---

## 📚 상세 가이드

프로젝트의 각 모듈에 대한 상세 가이드는 하위 README.md 파일을 참고하세요:

### Core 모듈 (인프라)
**상세 가이드**: [`src/core/README.md`](./src/core/README.md)

- **Elasticsearch**: 문서 검색 엔진, TF-IDF 키워드 추출, Nori 형태소 분석기
- **MinIO**: 객체 스토리지, 파일 업로드/다운로드/삭제
- **TextExtractor**: PDF, DOCX, XLSX, PPTX, TXT, HWP 텍스트 추출
- **KeyBERT**: AI 기반 키워드 추출 (하이브리드 전략)

### Domains (비즈니스 로직)
**상세 가이드**: [`src/domains/README.md`](./src/domains/README.md)

- **도메인 주도 설계 (DDD)**: 계층형 아키텍처, SOLID 원칙
- **새로운 도메인 추가 방법**: 7단계 가이드
- **테스트 전략**: 단위 테스트 / 통합 테스트

#### Documents 도메인
**상세 가이드**: [`src/domains/documents/README.md`](./src/domains/documents/README.md)

- **문서 업로드 워크플로우**: 9단계 프로세스 (파일 검증 → MinIO 업로드 → AI 태깅)
- **AI 자동 태깅**: 하이브리드 키워드 추출 (KeyBERT + Elasticsearch TF-IDF)
- **한국어 키워드 품질 개선**: Nori 형태소 분석기 적용
- **보안 및 권한**: 사용자별 격리, MIME 타입 검증

#### Tags 도메인
**상세 가이드**: [`src/domains/tags/README.md`](./src/domains/tags/README.md)

- **다대다(Many-to-Many) 관계**: Tag ↔ Document
- **Get-or-Create 패턴**: 중복 방지, 데이터 일관성
- **N+1 문제 방지**: Bulk Operations, Eager Loading
- **CASCADE 삭제**: 문서 삭제 시 연결 자동 삭제

---

## 📄 Documents API

Documents 도메인은 문서 업로드, 관리, 검색 기능을 제공합니다. **AI 기반 자동 태깅**과 Elasticsearch를 통한 강력한 검색 기능이 핵심입니다.

### 주요 기능

- **문서 업로드 및 관리**: MinIO 객체 스토리지에 파일 저장, PostgreSQL에 메타데이터 관리
- **AI 자동 태깅**: KeyBERT 및 Elasticsearch TF-IDF를 활용한 하이브리드 키워드 추출
- **문서 검색**: 파일명 검색 (Elasticsearch), 태그 검색 (PostgreSQL)
- **권한 관리**: 사용자별 문서 격리 및 접근 제어

### API 엔드포인트 (빠른 참조)

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| POST | `/api/v1/documents/upload` | 문서 업로드 (AI 자동 태깅 포함) |
| GET | `/api/v1/documents` | 문서 목록 조회 |
| GET | `/api/v1/documents/{id}` | 문서 상세 조회 |
| DELETE | `/api/v1/documents/{id}` | 문서 삭제 |
| GET | `/api/v1/documents/search/filename` | 파일명 검색 |
| GET | `/api/v1/documents/search/tags` | 태그 검색 |

### 상세 문서

Documents 도메인의 상세한 API 명세, 워크플로우, 구현 가이드는 다음 문서를 참고하세요:

**[📖 Documents 도메인 상세 가이드](./src/domains/documents/README.md)**

- 문서 업로드 워크플로우 (9단계)
- AI 자동 태깅 상세 로직
- Elasticsearch 검색 구현
- 성능 최적화 및 보안

---

## 💬 AIChat API

AIChat 도메인은 RAG(Retrieval-Augmented Generation) 방식의 AI 채팅 기능을 제공합니다. 문서 기반 Q&A와 대화형 AI 어시스턴트 기능을 결합했습니다.

### 주요 기능

- **RAG 파이프라인**: Elasticsearch로 문서 검색 → 컨텍스트 구성 → AI 응답 생성
- **로컬 LLM**: Ollama(qwen2.5:7b)를 통한 프라이빗 AI 처리
- **대화 기억**: 최근 10개 메시지를 유지하여 맥락 있는 대화 지원
- **다중 문서 지원**: 채팅방당 여러 문서를 연결하여 통합 분석 가능

### API 엔드포인트 (빠른 참조)

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| POST | `/api/v1/aichat/conversations` | 채팅방 생성 (문서 선택) |
| GET | `/api/v1/aichat/conversations` | 채팅방 목록 조회 (페이징) |
| GET | `/api/v1/aichat/conversations/{id}` | 채팅방 상세 조회 (메시지 포함) |
| POST | `/api/v1/aichat/conversations/{id}/messages` | 메시지 전송 및 AI 응답 받기 |
| GET | `/api/v1/aichat/conversations/{id}/messages` | 메시지 목록 조회 |
| GET | `/api/v1/aichat/conversations/{id}/documents` | 연결된 문서 목록 조회 |
| PATCH | `/api/v1/aichat/conversations/{id}` | 채팅방 제목 수정 |
| DELETE | `/api/v1/aichat/conversations/{id}` | 채팅방 삭제 |

### 상세 문서

AIChat 도메인의 상세한 API 명세, RAG 파이프라인, 프론트엔드 연동 가이드는 다음 문서를 참고하세요:

**[📖 AIChat 도메인 상세 가이드](./src/domains/aichat/README.md)**

- RAG 파이프라인 상세 구현
- Ollama LLM 설정 및 최적화
- 프롬프트 엔지니어링
- 스트리밍 응답 구현 (향후 개선)

---

## 👤 Users API

Users 도메인은 사용자 정보 관리 및 통계/활동 분석 기능을 제공합니다. 사용자의 관심사와 활동 패턴을 분석하여 개인화된 인사이트를 제공합니다.

### 주요 기능

- **관심사 분석**: 최근 30일간 활동 기록을 기반으로 사용자 관심 주제 파악
- **활동 히트맵**: GitHub 잔디 심기 스타일의 날짜별 활동 시각화 데이터
- **사용자 관리**: 사용자 정보 조회, 수정, 삭제 (Auth 도메인과 연동)

### API 엔드포인트 (빠른 참조)

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| GET | `/api/v1/users/stats/topics` | 관심사 분석 (태그별 활동 집계) |
| GET | `/api/v1/users/stats/heatmap` | 활동 히트맵 (날짜별 활동 집계) |

### 상세 문서

Users 도메인의 상세한 API 명세, 데이터 모델, 프론트엔드 연동 가이드는 다음 문서를 참고하세요:

**[📖 Users 도메인 상세 가이드](./src/domains/users/README.md)**

- 사용자 통계 쿼리 최적화
- React 차트 연동 예시
- 활동 로깅 시스템
- 성능 개선 및 캐싱 전략

---

## 📖 개발 가이드

### 새로운 도메인 추가하기

1. `src/domains/` 아래에 새 폴더 생성 (예: `users`)
2. 다음 파일들을 생성:
   - `models.py`: SQLAlchemy 모델 정의
   - `schemas.py`: Pydantic 스키마 정의
   - `repositories.py`: 데이터 액세스 로직
   - `services.py`: 비즈니스 로직
   - `router.py`: API 엔드포인트
3. `src/main.py`에 라우터 등록

```python
from src.domains.users.router import router as users_router
app.include_router(users_router, prefix="/api/users", tags=["Users"])
```

### 코드 스타일

프로젝트는 다음 도구들을 사용하여 코드 품질을 유지합니다:

```bash
# 코드 포맷팅
black .

# 린팅
flake8 .

# 타입 체크
mypy src/
```

### 테스트

```bash
# 전체 테스트 실행
pytest

# 특정 테스트 파일 실행
pytest tests/test_auth.py

# 커버리지 포함
pytest --cov=src tests/
```

---

## 📝 라이센스

이 프로젝트는 MIT 라이센스 하에 있습니다.

---

## 👥 기여

기여를 환영합니다! Pull Request를 보내주세요.

---

## 📞 문의

프로젝트에 대한 문의사항이 있으시면 이슈를 등록해주세요.
