# Documents 도메인 (문서 관리)

Documents 도메인은 사용자의 파일 업로드, 조회, 삭제 기능을 제공하며, **AI 기반 자동 태그 생성** 기능을 포함합니다.

---

## 📂 모듈 구조

```
src/domains/documents/
├── models.py           # Document 엔티티 모델
├── schema.py           # Document Pydantic 스키마
├── repository.py       # Document 데이터 접근 계층
├── service.py          # Document 비즈니스 로직
└── controller.py       # Document API 엔드포인트
```

---

## 🗄️ 데이터베이스 모델

### Document 테이블 (`models.py`)

```sql
CREATE TABLE documents (
    document_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    original_filename VARCHAR(255) NOT NULL,
    storage_path VARCHAR(500) UNIQUE NOT NULL,
    file_type VARCHAR(100) NOT NULL,
    file_size_kb INTEGER NOT NULL,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**컬럼 설명**:
- `document_id`: 문서 고유 ID (자동 증가)
- `user_id`: 소유자 사용자 ID (외래 키)
- `original_filename`: 원본 파일명 (예: "report.pdf")
- `storage_path`: MinIO 저장 경로 (예: "123/a1b2c3d4-uuid.pdf")
- `file_type`: MIME 타입 (예: "application/pdf")
- `file_size_kb`: 파일 크기 (킬로바이트)
- `uploaded_at`: 업로드 일시
- `updated_at`: 수정 일시

**관계**:
```python
class Document(Base):
    user = relationship("User", back_populates="documents")
    document_tags = relationship("DocumentTag", back_populates="document", cascade="all, delete-orphan")
```

---

## 🌐 API 엔드포인트

### 1. 문서 업로드 (POST /api/v1/documents/upload)

사용자가 문서를 업로드하고 AI가 자동으로 태그를 생성합니다.

**요청**:
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: `file` (파일)
- Headers: `Cookie: session_id` (인증 필요)

**허용된 파일 형식**:
| 형식 | 확장자 | MIME Type |
|------|--------|-----------|
| PDF | `.pdf` | `application/pdf` |
| Word | `.doc`, `.docx` | `application/msword`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| Excel | `.xls`, `.xlsx` | `application/vnd.ms-excel`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| PowerPoint | `.ppt`, `.pptx` | `application/vnd.ms-powerpoint`, `application/vnd.openxmlformats-officedocument.presentationml.presentation` |
| 텍스트 | `.txt` | `text/plain` |
| 한글 | `.hwp` | `application/x-hwp`, `application/haansofthwp` |

**응답 (201 Created)**:
```json
{
  "document_id": 101,
  "user_id": 1,
  "original_filename": "my_report.pdf",
  "storage_path": "1/a1b2c3d4-...-uuid.pdf",
  "file_type": "application/pdf",
  "file_size_kb": 1234,
  "uploaded_at": "2025-10-08T15:30:00Z",
  "updated_at": "2025-10-08T15:30:00Z",
  "tags": [
    {"tag_id": 1, "name": "machine learning"},
    {"tag_id": 2, "name": "deep learning"},
    {"tag_id": 3, "name": "neural network"}
  ],
  "extraction_method": "keybert"
}
```

### 2. 문서 목록 조회 (GET /api/v1/documents)

현재 로그인된 사용자의 모든 문서 목록을 조회합니다.

**응답 (200 OK)**:
```json
[
  {
    "document_id": 101,
    "original_filename": "report.pdf",
    "file_type": "application/pdf",
    "file_size_kb": 1234,
    "uploaded_at": "2025-10-08T15:30:00Z",
    "updated_at": "2025-10-08T15:30:00Z",
    "tags": [
      {"tag_id": 1, "name": "machine learning"},
      {"tag_id": 2, "name": "deep learning"}
    ]
  }
]
```

### 3. 문서 상세 조회 (GET /api/v1/documents/{document_id})

특정 문서의 상세 정보를 조회합니다. (권한 검증 포함)

**응답 (200 OK)**:
```json
{
  "document_id": 101,
  "user_id": 1,
  "original_filename": "my_report.pdf",
  "storage_path": "1/a1b2c3d4-...-uuid.pdf",
  "file_type": "application/pdf",
  "file_size_kb": 1234,
  "uploaded_at": "2025-10-08T15:30:00Z",
  "updated_at": "2025-10-08T15:30:00Z",
  "tags": [
    {"tag_id": 1, "name": "machine learning"}
  ]
}
```

### 4. 문서 삭제 (DELETE /api/v1/documents/{document_id})

문서를 MinIO와 PostgreSQL에서 완전히 삭제합니다. (관련 태그 연결도 CASCADE 삭제)

**응답 (200 OK)**:
```json
{
  "message": "문서가 성공적으로 삭제되었습니다.",
  "document_id": 101
}
```

### 5. 파일명으로 문서 검색 (GET /api/v1/documents/search/filename)

Elasticsearch를 사용하여 파일명으로 문서를 검색합니다.

**요청**:
- Method: `GET`
- Query Parameter: `query` (검색할 파일명)
- Headers: `Cookie: session_id` (인증 필요)

**요청 예시**:
```http
GET /api/v1/documents/search/filename?query=report
```

**응답 (200 OK)**:
```json
{
  "documents": [
    {
      "document_id": 101,
      "original_filename": "annual_report_2024.pdf",
      "file_type": "application/pdf",
      "file_size_kb": 2048,
      "summary": "2024년도 연간 보고서입니다.",
      "uploaded_at": "2024-01-15T10:30:00",
      "updated_at": "2024-01-15T10:30:00",
      "tags": [
        {"tag_id": 5, "name": "보고서"},
        {"tag_id": 12, "name": "재무"}
      ]
    }
  ],
  "query": "report",
  "total": 1
}
```

**검색 방식** (하이브리드: Wildcard + Fuzzy):
- **Wildcard 쿼리**: 부분 일치 검색 (대소문자 구분 없음, 높은 가중치)
  - 예: "report" → "annual_report_2024.pdf" ✅
- **Fuzzy 쿼리**: 오타 보정 검색 (1-2글자 차이 허용, 낮은 가중치)
  - 예: "reprot" → "report" ✅ (1글자 오타)
  - 예: "rprt" → "report" ✅ (2글자 오타)
- 사용자별 격리 (본인이 업로드한 문서만 검색)

### 6. 태그로 문서 검색 (GET /api/v1/documents/search/tags)

PostgreSQL을 사용하여 태그로 문서를 검색합니다.

**요청**:
- Method: `GET`
- Query Parameter: `tags` (검색할 태그 이름, 쉼표로 구분)
- Headers: `Cookie: session_id` (인증 필요)

**요청 예시**:
```http
GET /api/v1/documents/search/tags?tags=python,fastapi
```

**응답 (200 OK)**:
```json
{
  "documents": [
    {
      "document_id": 10,
      "original_filename": "fastapi_tutorial.pdf",
      "file_type": "application/pdf",
      "file_size_kb": 1024,
      "summary": "FastAPI 프레임워크 튜토리얼 문서입니다.",
      "uploaded_at": "2024-03-10T14:20:00",
      "updated_at": "2024-03-10T14:20:00",
      "tags": [
        {"tag_id": 15, "name": "python"},
        {"tag_id": 23, "name": "fastapi"}
      ]
    }
  ],
  "query": "python,fastapi",
  "total": 1
}
```

**검색 방식**:
- PostgreSQL JOIN + IN 조건 사용
- 여러 태그 검색 시 OR 조건 (하나 이상의 태그가 일치하면 결과에 포함)
- 업로드 시간 내림차순 정렬
- 사용자별 격리 (본인이 업로드한 문서만 검색)

---

## 🔍 문서 검색 API 상세

### Request/Response DTO

#### DocumentSearchResponse
```python
class DocumentSearchResponse(BaseModel):
    """문서 검색 응답 스키마"""
    documents: List[DocumentListResponse]  # 검색된 문서 목록
    query: str                             # 검색 쿼리
    total: int                             # 검색 결과 수
```

#### DocumentListResponse
```python
class DocumentListResponse(BaseModel):
    """문서 목록 응답 스키마"""
    document_id: int                    # 문서 고유 ID
    original_filename: str              # 원본 파일 이름
    file_type: str                      # 파일 MIME 타입
    file_size_kb: int                   # 파일 크기 (KB)
    summary: Optional[str]              # 문서 요약
    uploaded_at: datetime               # 업로드 일시
    updated_at: datetime                # 최종 수정 일시
    tags: List[TagSchema]               # 태그 목록
```

#### TagSchema
```python
class TagSchema(BaseModel):
    """태그 스키마"""
    tag_id: int          # 태그 고유 ID
    name: str            # 태그 이름
```

### 에러 응답

#### 401 Unauthorized - 인증 실패
```json
{
    "detail": "Not authenticated"
}
```

#### 500 Internal Server Error - 서버 오류
```json
{
    "detail": "검색 중 오류가 발생했습니다."
}
```

### 사용 예시

#### cURL

**파일명 검색**:
```bash
curl -X GET "http://localhost:8000/api/v1/documents/search/filename?query=report" \
  -H "Cookie: session_id=YOUR_SESSION_ID"
```

**태그 검색 (단일)**:
```bash
curl -X GET "http://localhost:8000/api/v1/documents/search/tags?tags=python" \
  -H "Cookie: session_id=YOUR_SESSION_ID"
```

**태그 검색 (다중)**:
```bash
curl -X GET "http://localhost:8000/api/v1/documents/search/tags?tags=python,fastapi,웹개발" \
  -H "Cookie: session_id=YOUR_SESSION_ID"
```

#### Python (requests)

```python
import requests

# 세션 쿠키
cookies = {
    "session_id": "YOUR_SESSION_ID"
}

# 파일명 검색
response = requests.get(
    "http://localhost:8000/api/v1/documents/search/filename",
    params={"query": "report"},
    cookies=cookies
)
print(response.json())

# 태그 검색
response = requests.get(
    "http://localhost:8000/api/v1/documents/search/tags",
    params={"tags": "python,fastapi"},
    cookies=cookies
)
print(response.json())
```

#### JavaScript (Axios)

```javascript
const axios = require('axios');

const config = {
    headers: {
        'Cookie': 'session_id=YOUR_SESSION_ID'
    }
};

// 파일명 검색
axios.get('http://localhost:8000/api/v1/documents/search/filename', {
    params: { query: 'report' },
    ...config
})
.then(response => console.log(response.data))
.catch(error => console.error(error));

// 태그 검색
axios.get('http://localhost:8000/api/v1/documents/search/tags', {
    params: { tags: 'python,fastapi' },
    ...config
})
.then(response => console.log(response.data))
.catch(error => console.error(error));
```

### 검색 구현 상세

#### 파일명 검색 기술 스펙
- **검색 엔진**: Elasticsearch
- **검색 방식**: 하이브리드 (Wildcard + Fuzzy)
- **검색 필드**: `filename` (keyword 타입)
- **필터**: `user_id` (현재 로그인한 사용자의 문서만 검색)
- **인덱스**: `documents`
- **오타 보정**: 최대 1-2글자 차이 허용 (AUTO fuzziness)

**Elasticsearch 쿼리 예시**:
```json
{
  "query": {
    "bool": {
      "should": [
        {
          "wildcard": {
            "filename": {
              "value": "*report*",
              "case_insensitive": true,
              "boost": 2.0
            }
          }
        },
        {
          "fuzzy": {
            "filename": {
              "value": "report",
              "fuzziness": "AUTO",
              "boost": 1.0
            }
          }
        }
      ],
      "minimum_should_match": 1,
      "filter": [
        {"term": {"user_id": 1}}
      ]
    }
  }
}
```

**검색 예시**:
- `"report"` → "annual_report_2024.pdf" (부분 일치)
- `"reprot"` → "annual_report_2024.pdf" (오타 보정: 1글자 차이)
- `"annu"` → "annual_report_2024.pdf" (부분 일치)
- `"rprt"` → "report.pdf" (오타 보정: 2글자 차이)

#### 태그 검색 기술 스펙
- **검색 엔진**: PostgreSQL
- **검색 방식**: JOIN + IN 조건
- **검색 로직**:
  - 여러 태그 입력 시 OR 조건 (하나 이상의 태그가 일치하면 반환)
  - 쉼표로 구분된 태그를 파싱하여 리스트로 변환
- **필터**: `user_id` (현재 로그인한 사용자의 문서만 검색)
- **정렬**: 업로드 시간 내림차순

**SQL 쿼리 예시**:
```sql
SELECT DISTINCT d.*
FROM documents d
JOIN document_tags dt ON d.document_id = dt.document_id
JOIN tags t ON dt.tag_id = t.tag_id
WHERE d.user_id = 1
  AND t.name IN ('python', 'fastapi')
ORDER BY d.uploaded_at DESC;
```

### 주의사항

1. **인증 필수**: 모든 검색 API는 세션 인증이 필요합니다.
2. **사용자 격리**: 각 사용자는 자신이 업로드한 문서만 검색할 수 있습니다.
3. **대소문자**: 파일명 검색은 대소문자를 구분하지 않습니다.
4. **태그 OR 조건**: 여러 태그로 검색 시 하나 이상의 태그가 일치하면 결과에 포함됩니다.
5. **빈 결과**: 검색 결과가 없어도 200 OK를 반환하며, `documents` 배열이 비어있습니다.

---

## 🔄 문서 업로드 워크플로우 (9단계)

문서 업로드는 다음 9단계를 거쳐 처리됩니다:

```
[1] 사용자 파일 업로드 (Controller)
    ↓
[2] 파일 형식 검증 (Service)
    - MIME 타입 검증
    - 허용된 형식만 통과
    ↓
[3] 고유 경로 생성 (Service)
    - UUID 기반 파일명 생성: {user_id}/{uuid}.확장자
    - 예: 123/a1b2c3d4-e5f6-7890-abcd-ef1234567890.pdf
    ↓
[4] MinIO 업로드 (MinIO Client)
    - 버킷: user-documents
    - 객체 스토리지에 실제 파일 저장
    ↓
[5] PostgreSQL 메타데이터 저장 (Repository)
    - 테이블: documents
    - 컬럼: document_id, user_id, original_filename, storage_path, file_type, file_size_kb
    ↓
[6] 텍스트 추출 (TextExtractor)
    - PDF → pypdf
    - DOCX → python-docx
    - XLSX → openpyxl
    - PPTX → python-pptx
    - TXT → UTF-8/CP949 디코딩
    - HWP → olefile (OLE 구조 파싱)
    ↓
[7] Elasticsearch 색인 (Elasticsearch Client)
    - 인덱스: documents
    - 필드: document_id, user_id, content, filename, file_type, uploaded_at
    - 한국어 Nori 분석기 적용
    ↓
[8] 하이브리드 키워드 추출 (Keyword Extraction Service)
    ├─ 문서 수 확인: await elasticsearch_client.get_document_count()
    ├─ 문서 < 10: KeyBERT 사용 (Cold Start)
    └─ 문서 >= 10: Elasticsearch TF-IDF 사용 (Normal)
    ↓
[9] 태그 생성 및 문서 연결 (TagService)
    - tags 테이블: Get-or-Create 패턴 (중복 방지)
    - document_tags 테이블: Bulk Insert (N+1 방지)
```

---

## 💻 코드 구현 (계층별)

### Controller Layer (`controller.py:34-78`)

```python
@router.post("/upload")
async def upload_document(
    file: UploadFile,
    user_id: int = Depends(get_current_user_id),
    document_service: DocumentService = Depends()
):
    """
    문서 업로드 API

    - 파일 검증
    - MinIO 업로드
    - AI 자동 태깅
    """
    # Service 호출
    document, tags, extraction_method = await document_service.upload_document(
        user_id=user_id,
        file=file
    )

    # 응답 생성
    return DocumentUploadResponse(
        document_id=document.document_id,
        user_id=document.user_id,
        original_filename=document.original_filename,
        storage_path=document.storage_path,
        file_type=document.file_type,
        file_size_kb=document.file_size_kb,
        uploaded_at=document.uploaded_at,
        updated_at=document.updated_at,
        tags=[TagSchema(tag_id=tag.tag_id, name=tag.name) for tag in tags],
        extraction_method=extraction_method
    )
```

### Service Layer (`service.py:48-158`)

```python
class DocumentService:
    """문서 관리 비즈니스 로직"""

    ALLOWED_MIME_TYPES = {
        "application/pdf",
        "text/plain",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",        # XLSX
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",# PPTX
        "application/x-hwp",              # HWP (한글)
        "application/haansofthwp",        # HWP (한글, 일부 브라우저)
        "application/vnd.hancom.hwp"      # HWP (한글, 표준 MIME 타입)
    }

    async def upload_document(self, user_id: int, file: UploadFile):
        """
        문서 업로드 메인 로직

        Returns:
            (Document, List[Tag], str): 문서, 태그 리스트, 추출 방법
        """
        # Step 1: 파일 읽기
        file_data = await file.read()
        file_size = len(file_data)
        file_size_kb = file_size // 1024
        content_type = file.content_type
        filename = file.filename

        # Step 2: 파일 형식 검증
        if content_type not in self.ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"허용되지 않는 파일 형식입니다: {content_type}"
            )

        # Step 3: 고유 경로 생성
        file_extension = Path(filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        storage_path = f"{user_id}/{unique_filename}"

        # Step 4: MinIO 업로드
        minio_client.upload_file(
            file_path=storage_path,
            file_data=BytesIO(file_data),
            file_size=file_size,
            content_type=content_type
        )

        # Step 5: PostgreSQL 메타데이터 저장
        document = await self.repository.create(
            user_id=user_id,
            original_filename=filename,
            storage_path=storage_path,
            file_type=content_type,
            file_size_kb=file_size_kb
        )

        # Step 6: 텍스트 추출
        extracted_text = text_extractor.extract_text_from_bytes(
            file_data=file_data,
            file_type=content_type,
            filename=filename
        )

        # Step 7: Elasticsearch 색인
        await elasticsearch_client.index_document(
            document_id=document.document_id,
            user_id=user_id,
            content=extracted_text,
            filename=filename,
            file_type=content_type,
            uploaded_at=document.uploaded_at.isoformat()
        )

        # Step 8: 하이브리드 키워드 추출
        keywords, extraction_method = await keyword_extraction_service.extract_keywords(
            text=extracted_text,
            document_id=document.document_id
        )

        # Step 9: 태그 생성 및 연결
        tags = await self.tag_service.attach_tags_to_document(
            document_id=document.document_id,
            tag_names=keywords
        )

        return document, tags, extraction_method
```

### Repository Layer (`repository.py`)

#### 문서 생성 (`repository.py:37-59`)

```python
async def create(
    self,
    user_id: int,
    original_filename: str,
    storage_path: str,
    file_type: str,
    file_size_kb: int
) -> Document:
    """
    새 문서 메타데이터 생성

    Returns:
        Document: 생성된 문서 엔티티
    """
    document = Document(
        user_id=user_id,
        original_filename=original_filename,
        storage_path=storage_path,
        file_type=file_type,
        file_size_kb=file_size_kb
    )

    self.db.add(document)
    await self.db.commit()
    await self.db.refresh(document)

    return document
```

#### N+1 문제 방지 (`repository.py:61-101`)

```python
async def find_all_by_user_id(self, user_id: int) -> List[Document]:
    """
    사용자의 모든 문서 조회 (태그 포함, N+1 방지)

    - selectinload()를 사용하여 태그를 한 번에 로드
    - DocumentTag → Tag 관계도 Eager Loading
    """
    stmt = (
        select(Document)
        .where(Document.user_id == user_id)
        .options(
            selectinload(Document.document_tags).selectinload(DocumentTag.tag)
        )
        .order_by(Document.uploaded_at.desc())
    )

    result = await self.db.execute(stmt)
    return result.scalars().all()
```

**N+1 문제 설명**:
- **문제**: 문서 10개 조회 시 태그를 가져오기 위해 추가로 10번의 쿼리 발생 (총 11번)
- **해결**: `selectinload()`로 한 번에 모든 태그 로드 (총 2번 쿼리)

---

## 🤖 AI 자동 태깅 (Keyword Extraction)

문서 업로드 시 AI가 자동으로 키워드를 추출하고 태그를 생성합니다.

### 하이브리드 추출 전략 (Cold Start → Normal)

#### 1. Cold Start 모드 (문서 수 < 10개)

- **사용 조건**: Elasticsearch 색인 문서 수 < 10개
- **추출 방법**: KeyBERT (BERT 기반 임베딩)
- **장점**: 문서 간 비교 데이터 부족 시에도 단일 문서에서 의미 있는 키워드 추출

**추출 과정**:
```python
from keybert import KeyBERT

model = KeyBERT()
keywords = model.extract_keywords(
    text,
    keyphrase_ngram_range=(1, 2),  # 1~2 단어 구문까지
    stop_words='english',          # 불용어 제거
    top_n=3,                        # 상위 3개
    use_maxsum=True,                # 다양성 증가
    nr_candidates=20                # 후보 20개 생성
)
```

#### 2. Normal 모드 (문서 수 >= 10개)

- **사용 조건**: Elasticsearch 색인 문서 수 >= 10개
- **추출 방법**: Elasticsearch TF-IDF (Term Vectors API)
- **장점**: 전체 문서 컬렉션과 비교하여 상대적 중요도 계산

**추출 과정**:
```python
# Term Vectors API로 TF-IDF 계산
tv_response = await client.termvectors(
    index="documents",
    id=str(document_id),
    fields=["content"],
    term_statistics=True,
    field_statistics=True
)

# TF-IDF 점수 계산
for term, term_info in terms.items():
    tf = term_info["term_freq"]
    df = term_info["doc_freq"]
    idf = log((total_docs + 1) / (df + 1)) + 1
    tfidf = tf * idf

# 상위 N개 추출
keywords = sorted(scores, reverse=True)[:3]
```

### 한국어 키워드 품질 개선 (Nori 형태소 분석기)

**문제점**:
- 기본 분석기 사용 시 "을", "를", "과", "와", "것이" 같은 조사와 어미가 키워드로 추출됨

**해결책**:
- Elasticsearch Nori 플러그인 설치
- 39개 품사 태그 필터링 (조사, 어미, 접사, 기호 등)

**자세한 설정 가이드**: [`docs/NORI_SETUP.md`](../../../docs/NORI_SETUP.md)

---

## 🗂️ 파일 저장 구조

### MinIO 버킷 구조

```
user-documents/
  ├── 1/                          # user_id=1의 폴더
  │   ├── a1b2c3d4-uuid.pdf
  │   ├── e5f6g7h8-uuid.docx
  │   └── i9j0k1l2-uuid.xlsx
  ├── 2/                          # user_id=2의 폴더
  │   ├── m3n4o5p6-uuid.pdf
  │   └── q7r8s9t0-uuid.txt
```

- 각 사용자는 `user_id` 폴더로 격리
- 파일명은 UUID로 저장하여 충돌 방지
- 원본 파일명은 PostgreSQL `original_filename`에 저장

---

## 🔒 보안 및 권한

### 인증

- 모든 API는 `get_current_user_id` 의존성을 통해 로그인 검증
- Redis 기반 세션 관리

### 권한 검증

- 사용자는 자신이 업로드한 문서만 조회/삭제 가능
- Repository 레벨에서 `user_id` 필터링

**예시** (`repository.py:103-118`):
```python
async def find_by_id_and_user(self, document_id: int, user_id: int):
    """
    문서 ID와 사용자 ID로 조회 (권한 검증)
    """
    stmt = (
        select(Document)
        .where(
            Document.document_id == document_id,
            Document.user_id == user_id  # 권한 검증
        )
        .options(
            selectinload(Document.document_tags).selectinload(DocumentTag.tag)
        )
    )

    result = await self.db.execute(stmt)
    return result.scalar_one_or_none()
```

### 파일 형식 검증

- MIME 타입 기반 허용 목록 검증
- 악성 파일 업로드 방지

---

## 🧪 테스트

### 단위 테스트 (`tests/unit/domains/documents/`)

#### 1. Mock을 사용한 Service 테스트

```python
@pytest.mark.asyncio
async def test_upload_document():
    # Mock Repository
    mock_repository = AsyncMock()
    mock_document = MagicMock()
    mock_document.document_id = 1
    mock_repository.create.return_value = mock_document

    # Mock MinIO, Elasticsearch, KeywordExtraction
    mock_minio = MagicMock()
    mock_elasticsearch = AsyncMock()
    mock_keyword_service = AsyncMock()
    mock_keyword_service.extract_keywords.return_value = (
        ["machine learning", "deep learning"],
        "keybert"
    )

    # Service 테스트
    service = DocumentService(mock_repository, db=MagicMock())

    with patch('src.domains.documents.service.minio_client', mock_minio), \
         patch('src.domains.documents.service.elasticsearch_client', mock_elasticsearch), \
         patch('src.domains.documents.service.keyword_extraction_service', mock_keyword_service):

        document, tags, method = await service.upload_document(
            user_id=123,
            file=sample_file
        )

    assert document.document_id == 1
    assert mock_minio.upload_file.called
    assert mock_elasticsearch.index_document.called
```

#### 2. 실제 샘플 파일 테스트

```python
def test_extract_text_from_real_pdf(sample_pdf_path):
    """실제 PDF 파일에서 텍스트 추출 테스트"""
    from src.core.text_extractor import text_extractor

    with open(sample_pdf_path, "rb") as f:
        file_data = f.read()

    extracted_text = text_extractor.extract_text_from_bytes(
        file_data=file_data,
        file_type="application/pdf",
        filename="sample.pdf"
    )

    assert extracted_text is not None
    assert len(extracted_text) > 0
    assert "Machine Learning" in extracted_text
```

### 테스트 픽스처 (`tests/fixtures/`)

실제 샘플 파일들:
- `sample.pdf`: 머신러닝 관련 PDF
- `sample.docx`: 딥러닝 관련 Word 문서
- `sample.txt`: 일반 텍스트

---

## 📚 참고 자료

- [MinIO Python SDK](https://min.io/docs/minio/linux/developers/python/minio-py.html)
- [Elasticsearch Python Client](https://www.elastic.co/guide/en/elasticsearch/client/python-api/current/index.html)
- [KeyBERT 공식 문서](https://maartengr.github.io/KeyBERT/)
- [Nori 형태소 분석기 설정](../../../docs/NORI_SETUP.md)
- [Tags 도메인 가이드](../tags/README.md)
