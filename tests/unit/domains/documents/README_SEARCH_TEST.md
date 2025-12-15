# 문서 검색 API 테스트 가이드

## 테스트 파일 위치

### 단위 테스트
- **파일**: `tests/unit/domains/documents/test_document_search.py`
- **목적**: Service, Repository, Elasticsearch 클라이언트 레벨 테스트
- **상태**: ✅ **모두 통과 (8/8)**

### 통합 테스트
- **파일**: `tests/integration/domains/documents/test_document_search_api.py`
- **목적**: API 엔드포인트 레벨 테스트
- **참고**: 실제 인증이 필요한 환경에서 실행

## 단위 테스트 실행

```bash
# 전체 검색 테스트 실행
./venv/Scripts/python.exe -m pytest tests/unit/domains/documents/test_document_search.py -v

# 특정 테스트 클래스만 실행
./venv/Scripts/python.exe -m pytest tests/unit/domains/documents/test_document_search.py::TestDocumentSearchByFilename -v
./venv/Scripts/python.exe -m pytest tests/unit/domains/documents/test_document_search.py::TestDocumentSearchByTags -v
```

## 테스트 커버리지

### 파일명 검색 (3개 테스트)
- ✅ `test_search_by_filename_success` - 검색 성공
- ✅ `test_search_by_filename_no_results` - 결과 없음
- ✅ `test_search_by_filename_multiple_results` - 다중 결과

### 태그 검색 (3개 테스트)
- ✅ `test_search_by_tags_single_tag` - 단일 태그 검색
- ✅ `test_search_by_tags_multiple_tags` - 다중 태그 검색 (OR 조건)
- ✅ `test_search_by_tags_no_results` - 결과 없음

### Elasticsearch 클라이언트 (1개 테스트)
- ✅ `test_elasticsearch_search_documents_by_filename` - 파일명 검색 기능

### Repository (1개 테스트)
- ✅ `test_repository_find_by_tag_names` - 태그 이름으로 문서 검색

## 테스트 결과

```
tests/unit/domains/documents/test_document_search.py::TestDocumentSearchByFilename::test_search_by_filename_success PASSED [ 12%]
tests/unit/domains/documents/test_document_search.py::TestDocumentSearchByFilename::test_search_by_filename_no_results PASSED [ 25%]
tests/unit/domains/documents/test_document_search.py::TestDocumentSearchByFilename::test_search_by_filename_multiple_results PASSED [ 37%]
tests/unit/domains/documents/test_document_search.py::TestDocumentSearchByTags::test_search_by_tags_single_tag PASSED [ 50%]
tests/unit/domains/documents/test_document_search.py::TestDocumentSearchByTags::test_search_by_tags_multiple_tags PASSED [ 62%]
tests/unit/domains/documents/test_document_search.py::TestDocumentSearchByTags::test_search_by_tags_no_results PASSED [ 75%]
tests/unit/domains/documents/test_document_search.py::TestElasticsearchFilenameSearch::test_elasticsearch_search_documents_by_filename PASSED [ 87%]
tests/unit/domains/documents/test_document_search.py::TestRepositoryTagSearch::test_repository_find_by_tag_names PASSED [100%]

======================= 8 passed, 3 warnings in 28.75s ========================
```

## 테스트 구조

### Mock 객체 사용
- `AsyncMock`: 비동기 함수 Mock
- `MagicMock`: 일반 객체 Mock
- `patch`: 모듈 레벨 Mock

### 테스트 패턴
```python
# 1. Mock 데이터 준비
mock_repository = AsyncMock()
mock_document = MagicMock()

# 2. Mock 반환값 설정
mock_repository.find_by_id_and_user_id.return_value = mock_document

# 3. Service 생성 및 테스트 실행
service = DocumentService(mock_repository, db=MagicMock())
documents = await service.search_documents_by_filename(user_id=123, query="report")

# 4. 검증
assert len(documents) == 1
assert documents[0].document_id == 1
```

## 주요 테스트 시나리오

### 파일명 검색
1. **성공 케이스**: Elasticsearch에서 1개 문서 찾기
2. **빈 결과**: 검색 결과 없음
3. **다중 결과**: 여러 문서 찾기

### 태그 검색
1. **단일 태그**: 1개 태그로 검색
2. **다중 태그**: 여러 태그로 OR 검색
3. **빈 결과**: 태그가 없는 경우

## 코드 커버리지

검색 기능 관련 코드 커버리지:
- `src/domains/documents/service.py`: 31% → 검색 메서드 추가로 향상
- `src/domains/documents/repository.py`: 35% → 태그 검색 메서드 커버
- `src/core/elasticsearch_client.py`: 15% → 파일명 검색 메서드 커버

## 향후 개선 사항

1. **통합 테스트 개선**
   - 실제 인증 처리 Mock 개선
   - FastAPI TestClient 의존성 주입 개선

2. **추가 테스트 케이스**
   - 대용량 검색 결과 페이징
   - 특수 문자 포함 파일명 검색
   - 한글 태그 검색
   - 권한 검증 (다른 사용자 문서 접근 불가)

3. **성능 테스트**
   - Elasticsearch 쿼리 성능
   - PostgreSQL JOIN 성능
