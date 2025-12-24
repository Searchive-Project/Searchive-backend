# AIChat 도메인

AIChat 도메인은 RAG(Retrieval-Augmented Generation) 방식의 AI 채팅 기능을 제공합니다. 사용자는 문서를 선택하여 채팅방을 생성하고, 해당 문서의 내용을 기반으로 AI와 대화할 수 있습니다.

---

## 아키텍처

```
src/domains/aichat/
├── models.py       # Conversation, Message, ConversationDocument 엔티티
├── schema.py       # Pydantic 스키마
├── repository.py   # 데이터 접근 계층
├── service.py      # 비즈니스 로직 (RAG 파이프라인)
└── controller.py   # API 엔드포인트
```

---

## 데이터 모델

### Conversation 모델

채팅방 정보를 저장하는 엔티티입니다.

```python
class Conversation(Base):
    conversation_id: int      # Primary Key
    user_id: int              # Foreign Key → User
    title: str                # 채팅방 제목
    created_at: datetime      # 생성 일시
    updated_at: datetime      # 수정 일시
```

### Message 모델

채팅 메시지를 저장하는 엔티티입니다.

```python
class Message(Base):
    message_id: int           # Primary Key
    conversation_id: int      # Foreign Key → Conversation
    role: str                 # 메시지 역할 (user/assistant)
    content: str              # 메시지 내용
    created_at: datetime      # 생성 일시
```

**역할 (role):**
- `user`: 사용자 메시지
- `assistant`: AI 응답

### ConversationDocument 모델

채팅방과 문서의 다대다(Many-to-Many) 관계를 저장하는 연결 테이블입니다.

```python
class ConversationDocument(Base):
    conversation_id: int      # Foreign Key → Conversation
    document_id: int          # Foreign Key → Document
```

---

## 핵심 기술

### 1. RAG (Retrieval-Augmented Generation)
- **검색 엔진**: Elasticsearch를 통한 문서 내용 검색
- **벡터 검색**: 사용자 질문과 관련된 문서 내용을 시맨틱 검색
- **컨텍스트 구성**: 검색 결과를 AI 프롬프트에 포함
- **응답 생성**: Ollama 로컬 LLM을 통한 답변 생성

### 2. 로컬 LLM (Ollama)
- **모델**: qwen2.5:7b (7B 파라미터)
- **장점**: 데이터 외부 유출 없음, 비용 절감
- **성능**: 로컬 GPU 사용 시 빠른 응답 속도

### 3. 대화 히스토리 관리
- **메모리**: 최근 10개 메시지 유지
- **컨텍스트 윈도우**: 질문 + 히스토리 + 문서 내용
- **연속성**: 이전 대화 맥락을 이해한 응답 생성

### 4. 문서 연결
- **다대다 관계**: 하나의 채팅방에 여러 문서 연결 가능
- **통합 검색**: 연결된 모든 문서에서 관련 내용 검색
- **권한 검증**: 사용자가 소유한 문서만 연결 가능

---

## API 엔드포인트

### 1. 채팅방 생성 (POST /api/v1/aichat/conversations)

문서를 선택하여 새로운 채팅방을 생성합니다.

**요청:**
```http
POST /api/v1/aichat/conversations
Content-Type: application/json
Cookie: session_id=YOUR_SESSION_ID

{
  "title": "프로젝트 기획서 관련 질문",
  "document_ids": [1, 2, 3]
}
```

**요청 필드:**
- `title`: 채팅방 제목 (필수)
- `document_ids`: 연결할 문서 ID 배열 (필수, 최소 1개)

**응답 (201 Created):**
```json
{
  "conversation_id": 1,
  "title": "프로젝트 기획서 관련 질문",
  "created_at": "2025-12-21T10:30:00Z"
}
```

**유효성 검증:**
- 모든 문서는 현재 사용자가 소유한 문서여야 함
- 문서가 존재하지 않으면 404 에러
- 다른 사용자의 문서를 연결하려 하면 403 에러

---

### 2. 채팅방 목록 조회 (GET /api/v1/aichat/conversations)

사용자의 모든 채팅방 목록을 페이징하여 조회합니다.

**요청:**
```http
GET /api/v1/aichat/conversations?page=1&page_size=20
Cookie: session_id=YOUR_SESSION_ID
```

**Query Parameters:**
- `page`: 페이지 번호 (기본값: 1)
- `page_size`: 페이지당 항목 수 (기본값: 20)

**응답 (200 OK):**
```json
{
  "items": [
    {
      "conversation_id": 1,
      "title": "프로젝트 기획서 관련 질문",
      "created_at": "2025-12-21T10:30:00Z",
      "updated_at": "2025-12-21T10:35:00Z"
    },
    {
      "conversation_id": 2,
      "title": "연구 논문 요약",
      "created_at": "2025-12-20T14:20:00Z",
      "updated_at": "2025-12-20T15:10:00Z"
    }
  ],
  "total": 10,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

**응답 필드:**
- `items`: 채팅방 목록
- `total`: 전체 채팅방 개수
- `page`: 현재 페이지 번호
- `page_size`: 페이지당 항목 수
- `total_pages`: 전체 페이지 수

---

### 3. 채팅방 상세 조회 (GET /api/v1/aichat/conversations/{conversation_id})

특정 채팅방의 상세 정보와 메시지 히스토리를 조회합니다.

**요청:**
```http
GET /api/v1/aichat/conversations/1
Cookie: session_id=YOUR_SESSION_ID
```

**응답 (200 OK):**
```json
{
  "conversation_id": 1,
  "user_id": 1,
  "title": "프로젝트 기획서 관련 질문",
  "created_at": "2025-12-21T10:30:00Z",
  "updated_at": "2025-12-21T10:35:00Z",
  "messages": [
    {
      "message_id": 1,
      "role": "user",
      "content": "프로젝트 일정은 어떻게 되나요?",
      "created_at": "2025-12-21T10:31:00Z"
    },
    {
      "message_id": 2,
      "role": "assistant",
      "content": "기획서에 따르면, 프로젝트는 2025년 1월부터 시작하여...",
      "created_at": "2025-12-21T10:31:05Z"
    }
  ]
}
```

**에러 응답:**
- `404 Not Found`: 채팅방을 찾을 수 없음
- `403 Forbidden`: 다른 사용자의 채팅방에 접근 시도

---

### 4. 메시지 전송 및 AI 응답 받기 (POST /api/v1/aichat/conversations/{conversation_id}/messages)

사용자 질문을 전송하고 AI 응답을 받습니다. RAG 방식으로 연결된 문서에서 관련 내용을 검색하여 응답합니다.

**요청:**
```http
POST /api/v1/aichat/conversations/1/messages
Content-Type: application/json
Cookie: session_id=YOUR_SESSION_ID

{
  "content": "프로젝트의 주요 목표는 무엇인가요?"
}
```

**요청 필드:**
- `content`: 사용자 질문 (필수, 최대 5000자)

**응답 (201 Created):**
```json
{
  "user_message": {
    "message_id": 3,
    "role": "user",
    "content": "프로젝트의 주요 목표는 무엇인가요?",
    "created_at": "2025-12-21T10:32:00Z"
  },
  "assistant_message": {
    "message_id": 4,
    "role": "assistant",
    "content": "기획서에 명시된 주요 목표는 다음과 같습니다:\n1. 사용자 경험 개선\n2. 시스템 성능 향상\n3. ...",
    "created_at": "2025-12-21T10:32:05Z"
  }
}
```

**RAG 워크플로우:**
1. 채팅방에 연결된 문서 ID 조회
2. Elasticsearch로 사용자 질문과 관련된 문서 내용 검색
3. 검색 결과를 컨텍스트로 구성 (최대 5개 문서 청크)
4. 최근 대화 히스토리 10개 조회
5. Ollama에 질문 + 컨텍스트 + 히스토리 전송
6. AI 응답 생성 및 PostgreSQL에 저장
7. 사용자 메시지와 AI 응답 모두 반환

**프롬프트 구조:**
```
다음 문서 내용을 참고하여 사용자의 질문에 답변해주세요.

[문서 내용]
{검색된 문서 내용 1}
{검색된 문서 내용 2}
...

[대화 히스토리]
User: {이전 질문 1}
Assistant: {이전 응답 1}
...

[현재 질문]
User: {현재 질문}
```

---

### 5. 메시지 목록 조회 (GET /api/v1/aichat/conversations/{conversation_id}/messages)

특정 채팅방의 모든 메시지를 조회합니다.

**요청:**
```http
GET /api/v1/aichat/conversations/1/messages
Cookie: session_id=YOUR_SESSION_ID
```

**응답 (200 OK):**
```json
[
  {
    "message_id": 1,
    "role": "user",
    "content": "프로젝트 일정은?",
    "created_at": "2025-12-21T10:31:00Z"
  },
  {
    "message_id": 2,
    "role": "assistant",
    "content": "일정은...",
    "created_at": "2025-12-21T10:31:05Z"
  }
]
```

**정렬:**
- 생성 시간 기준 오름차순 (시간순)

---

### 6. 연결된 문서 목록 조회 (GET /api/v1/aichat/conversations/{conversation_id}/documents)

채팅방에 연결된 문서 목록을 조회합니다.

**요청:**
```http
GET /api/v1/aichat/conversations/1/documents
Cookie: session_id=YOUR_SESSION_ID
```

**응답 (200 OK):**
```json
{
  "conversation_id": 1,
  "documents": [
    {
      "document_id": 1,
      "original_filename": "project_plan.pdf",
      "file_type": "application/pdf",
      "uploaded_at": "2025-12-20T15:00:00Z"
    },
    {
      "document_id": 2,
      "original_filename": "requirements.docx",
      "file_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "uploaded_at": "2025-12-19T10:30:00Z"
    }
  ]
}
```

---

### 7. 채팅방 제목 수정 (PATCH /api/v1/aichat/conversations/{conversation_id})

채팅방 제목을 수정합니다.

**요청:**
```http
PATCH /api/v1/aichat/conversations/1
Content-Type: application/json
Cookie: session_id=YOUR_SESSION_ID

{
  "title": "프로젝트 기획 문의"
}
```

**요청 필드:**
- `title`: 새로운 채팅방 제목 (필수)

**응답 (200 OK):**
```json
{
  "conversation_id": 1,
  "title": "프로젝트 기획 문의",
  "created_at": "2025-12-21T10:30:00Z",
  "updated_at": "2025-12-21T11:00:00Z"
}
```

---

### 8. 채팅방 삭제 (DELETE /api/v1/aichat/conversations/{conversation_id})

채팅방과 관련된 모든 메시지 및 문서 연결을 삭제합니다.

**요청:**
```http
DELETE /api/v1/aichat/conversations/1
Cookie: session_id=YOUR_SESSION_ID
```

**응답 (200 OK):**
```json
{
  "message": "채팅방이 성공적으로 삭제되었습니다.",
  "conversation_id": 1
}
```

**CASCADE 삭제:**
- Conversation 삭제 시 연결된 Message도 자동 삭제
- ConversationDocument 연결도 자동 삭제
- Document 자체는 삭제되지 않음 (연결만 해제)

---

## 사용 예시

### cURL 예시

```bash
# 1. 채팅방 생성
curl -X POST "http://localhost:8000/api/v1/aichat/conversations" \
  -H "Content-Type: application/json" \
  -H "Cookie: session_id=YOUR_SESSION_ID" \
  -d '{"title": "프로젝트 기획서 관련 질문", "document_ids": [1, 2, 3]}'

# 2. 메시지 전송
curl -X POST "http://localhost:8000/api/v1/aichat/conversations/1/messages" \
  -H "Content-Type: application/json" \
  -H "Cookie: session_id=YOUR_SESSION_ID" \
  -d '{"content": "프로젝트 일정은?"}'

# 3. 채팅방 목록 조회
curl -X GET "http://localhost:8000/api/v1/aichat/conversations?page=1&page_size=20" \
  -H "Cookie: session_id=YOUR_SESSION_ID"

# 4. 채팅방 상세 조회
curl -X GET "http://localhost:8000/api/v1/aichat/conversations/1" \
  -H "Cookie: session_id=YOUR_SESSION_ID"

# 5. 연결된 문서 조회
curl -X GET "http://localhost:8000/api/v1/aichat/conversations/1/documents" \
  -H "Cookie: session_id=YOUR_SESSION_ID"
```

### Python 예시

```python
import requests

cookies = {"session_id": "YOUR_SESSION_ID"}

# 1. 채팅방 생성
response = requests.post(
    "http://localhost:8000/api/v1/aichat/conversations",
    json={
        "title": "프로젝트 기획서 관련 질문",
        "document_ids": [1, 2, 3]
    },
    cookies=cookies
)
conversation = response.json()
conversation_id = conversation["conversation_id"]
print(f"채팅방 생성: {conversation_id}")

# 2. 질문하기
response = requests.post(
    f"http://localhost:8000/api/v1/aichat/conversations/{conversation_id}/messages",
    json={"content": "프로젝트 일정은?"},
    cookies=cookies
)
result = response.json()
print(f"AI 응답: {result['assistant_message']['content']}")

# 3. 대화 히스토리 조회
response = requests.get(
    f"http://localhost:8000/api/v1/aichat/conversations/{conversation_id}",
    cookies=cookies
)
conversation = response.json()
for msg in conversation["messages"]:
    print(f"{msg['role']}: {msg['content']}")
```

### JavaScript (Fetch API) 예시

```javascript
const cookies = 'session_id=YOUR_SESSION_ID';

// 1. 채팅방 생성
const createResponse = await fetch('http://localhost:8000/api/v1/aichat/conversations', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Cookie': cookies
  },
  credentials: 'include',
  body: JSON.stringify({
    title: '프로젝트 기획서 관련 질문',
    document_ids: [1, 2, 3]
  })
});
const conversation = await createResponse.json();
const conversationId = conversation.conversation_id;

// 2. 질문하기
const messageResponse = await fetch(
  `http://localhost:8000/api/v1/aichat/conversations/${conversationId}/messages`,
  {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Cookie': cookies
    },
    credentials: 'include',
    body: JSON.stringify({ content: '프로젝트 일정은?' })
  }
);
const { assistant_message } = await messageResponse.json();
console.log('AI 응답:', assistant_message.content);
```

---

## 프론트엔드 연동 예시

### React Chat UI 컴포넌트

```jsx
import { useState, useEffect } from 'react';

function ChatRoom({ conversationId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  // 메시지 목록 로드
  useEffect(() => {
    fetch(`/api/v1/aichat/conversations/${conversationId}`, {
      credentials: 'include'
    })
      .then(res => res.json())
      .then(data => setMessages(data.messages));
  }, [conversationId]);

  // 메시지 전송
  const sendMessage = async () => {
    if (!input.trim()) return;

    setLoading(true);
    const response = await fetch(
      `/api/v1/aichat/conversations/${conversationId}/messages`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ content: input })
      }
    );

    const { user_message, assistant_message } = await response.json();
    setMessages([...messages, user_message, assistant_message]);
    setInput('');
    setLoading(false);
  };

  return (
    <div className="chat-room">
      <div className="messages">
        {messages.map(msg => (
          <div key={msg.message_id} className={`message ${msg.role}`}>
            <strong>{msg.role === 'user' ? '나' : 'AI'}:</strong>
            <p>{msg.content}</p>
          </div>
        ))}
      </div>
      <div className="input-area">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && sendMessage()}
          placeholder="질문을 입력하세요..."
          disabled={loading}
        />
        <button onClick={sendMessage} disabled={loading}>
          {loading ? '전송 중...' : '전송'}
        </button>
      </div>
    </div>
  );
}
```

---

## RAG 파이프라인 상세

### 1. 문서 검색 단계

```python
# Elasticsearch로 관련 문서 내용 검색
query = user_question
document_ids = [1, 2, 3]  # 채팅방에 연결된 문서들

search_results = await elasticsearch_client.search(
    index="documents",
    query={
        "bool": {
            "must": [
                {"match": {"content": query}},
                {"terms": {"document_id": document_ids}}
            ]
        }
    },
    size=5  # 상위 5개 결과만
)

contexts = [hit["_source"]["content"] for hit in search_results["hits"]["hits"]]
```

### 2. 프롬프트 구성 단계

```python
# 시스템 프롬프트
system_prompt = """당신은 사용자의 문서를 분석하여 질문에 답변하는 AI 어시스턴트입니다.
제공된 문서 내용을 바탕으로 정확하고 유용한 답변을 제공하세요.
문서에 없는 내용은 추측하지 말고, 없다고 명시하세요."""

# 컨텍스트 구성
context_text = "\n\n".join([f"[문서 {i+1}]\n{ctx}" for i, ctx in enumerate(contexts)])

# 대화 히스토리
history_text = "\n".join([
    f"{msg.role}: {msg.content}"
    for msg in recent_messages[-10:]  # 최근 10개만
])

# 최종 프롬프트
full_prompt = f"""{system_prompt}

[참고 문서]
{context_text}

[대화 히스토리]
{history_text}

[현재 질문]
user: {user_question}
"""
```

### 3. LLM 호출 단계

```python
from langchain_community.llms import Ollama

llm = Ollama(model="qwen2.5:7b", base_url=settings.OLLAMA_HOST)
response = llm.invoke(full_prompt)

# 응답 저장
assistant_message = Message(
    conversation_id=conversation_id,
    role="assistant",
    content=response
)
await db.add(assistant_message)
await db.commit()
```

---

## 환경 변수

AIChat 도메인에서 사용하는 환경 변수:

```bash
# Ollama LLM 서버
OLLAMA_HOST=http://localhost:11434

# Elasticsearch 설정
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200

# PostgreSQL 설정
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=password
DB_NAME=searchive
```

---

## 성능 최적화

### 1. 대화 히스토리 제한
- 최근 10개 메시지만 유지하여 프롬프트 길이 제한
- 오래된 메시지는 DB에 저장하되 LLM에 전달하지 않음

### 2. 검색 결과 제한
- 상위 5개 문서 청크만 컨텍스트로 사용
- 너무 많은 컨텍스트는 LLM 성능 저하 유발

### 3. 스트리밍 응답 (향후 개선)
```python
# 현재는 전체 응답 대기
# 향후 스트리밍으로 개선 가능
async for chunk in llm.astream(prompt):
    yield chunk
```

### 4. 캐싱 전략
- 동일한 질문에 대한 응답 캐싱 (Redis)
- 문서 임베딩 캐싱으로 검색 속도 향상

---

## 에러 처리

### 일반적인 에러 응답

| Status Code | 설명 | 발생 시점 |
|------------|------|----------|
| 400 Bad Request | 잘못된 요청 | 필수 필드 누락, 유효성 검증 실패 |
| 401 Unauthorized | 인증되지 않은 사용자 | 유효하지 않은 세션 |
| 403 Forbidden | 권한 없음 | 다른 사용자의 채팅방/문서 접근 |
| 404 Not Found | 리소스를 찾을 수 없음 | 채팅방/문서가 존재하지 않음 |
| 500 Internal Server Error | 서버 오류 | Ollama 연결 실패, Elasticsearch 오류 |

### 에러 응답 예시

```json
{
  "detail": "채팅방을 찾을 수 없습니다"
}
```

---

## 트러블슈팅

### 문제: "Ollama 서버에 연결할 수 없습니다"

**원인:**
- Ollama 서버가 실행되지 않음
- OLLAMA_HOST 설정이 잘못됨

**해결:**
```bash
# Ollama 서버 실행
ollama serve

# qwen2.5:7b 모델 다운로드
ollama pull qwen2.5:7b

# .env 파일 확인
OLLAMA_HOST=http://localhost:11434
```

### 문제: AI 응답이 느림

**원인:**
- CPU 모드로 실행 중 (GPU 미사용)
- 문서가 너무 많아 검색 시간 증가

**해결:**
- GPU 드라이버 및 CUDA 설치
- 채팅방당 연결 문서 수 제한 (5개 이하 권장)
- Elasticsearch 인덱싱 최적화

### 문제: AI가 문서 내용과 다른 답변 제공

**원인:**
- 검색 결과에 관련 내용이 없음
- LLM이 할루시네이션 (환각) 발생

**해결:**
- 프롬프트에 "문서에 없는 내용은 추측하지 말 것" 명시
- 검색 쿼리 개선 (키워드 추출, 쿼리 확장)
- 더 정확한 LLM 모델 사용 (GPT-4 등)

---

## 향후 개선 방향

### 1. 스트리밍 응답
- Server-Sent Events (SSE)로 실시간 스트리밍
- 사용자 경험 개선 (타이핑 효과)

### 2. 고급 RAG 기법
- **Reranking**: 검색 결과를 재순위화하여 정확도 향상
- **Query Expansion**: 사용자 질문을 확장하여 검색 정확도 향상
- **Hybrid Search**: BM25 + 벡터 검색 결합

### 3. 다중 문서 요약
- 여러 문서를 한 번에 요약하는 기능
- 문서 간 비교 분석 기능

### 4. 대화 분석
- 자주 묻는 질문 (FAQ) 자동 추출
- 사용자 의도 분석 및 추천

### 5. 음성 인터페이스
- Speech-to-Text: 음성 질문 입력
- Text-to-Speech: AI 응답 음성 출력

---

## 관련 문서

- [Documents 도메인](../documents/README.md) - 문서 업로드 및 Elasticsearch 인덱싱
- [Auth 도메인](../auth/README.md) - 사용자 인증 및 권한 검증
- [Core 모듈](../../core/README.md) - Elasticsearch, MinIO 클라이언트
- [LangChain 공식 문서](https://python.langchain.com/) - RAG 파이프라인 구축
- [Ollama 공식 문서](https://ollama.ai/) - 로컬 LLM 실행
