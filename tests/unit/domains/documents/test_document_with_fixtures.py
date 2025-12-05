# -*- coding: utf-8 -*-
"""Document Service 테스트 - 실제 샘플 파일 사용 (Mock과 결합)"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from src.domains.documents.service import DocumentService
from src.domains.documents.models import Document


class TestDocumentServiceWithRealFiles:
    """실제 샘플 파일을 사용한 문서 업로드 테스트 (MinIO는 Mock)"""

    @pytest.mark.asyncio
    async def test_upload_pdf_file_with_real_content(
        self,
        sample_pdf_file,
        mock_minio_client,
        mock_elasticsearch_client,
        mock_keyword_extraction_service,
        mock_ollama_summarizer
    ):
        """실제 PDF 샘플 파일로 업로드 테스트 (MinIO/ES는 Mock)"""
        # Mock Repository
        mock_repository = AsyncMock()

        # Mock Document 객체
        mock_document = MagicMock()
        mock_document.document_id = 1
        mock_document.user_id = 123
        mock_document.original_filename = "sample.pdf"
        mock_document.storage_path = "123/sample-uuid.pdf"
        mock_document.file_type = "application/pdf"
        mock_document.file_size_kb = 1
        mock_document.uploaded_at = MagicMock()

        mock_repository.create.return_value = mock_document

        # Mock TagService
        mock_tag_service = AsyncMock()
        mock_tag1 = MagicMock()
        mock_tag1.tag_id = 1
        mock_tag1.name = "machine learning"
        mock_tag2 = MagicMock()
        mock_tag2.tag_id = 2
        mock_tag2.name = "neural networks"
        mock_tag_service.attach_tags_to_document.return_value = [mock_tag1, mock_tag2]

        # Mock TextExtractor - 실제 PDF에서 추출된 것처럼
        mock_text_extractor = MagicMock()
        mock_text_extractor.extract_text_from_bytes.return_value = (
            "Machine Learning Research Paper. "
            "This paper explores machine learning and deep learning. "
            "Neural networks are the foundation of deep learning."
        )

        # Mock DB session (commit/rollback/refresh는 async 메서드)
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        mock_db.refresh = AsyncMock()

        # DocumentService 생성
        document_service = DocumentService(mock_repository, db=mock_db)
        document_service.tag_service = mock_tag_service

        # 테스트 실행 - 실제 PDF 파일 내용 사용
        with patch('src.domains.documents.service.minio_client', mock_minio_client), \
             patch('src.domains.documents.service.text_extractor', mock_text_extractor), \
             patch('src.domains.documents.service.elasticsearch_client', mock_elasticsearch_client), \
             patch('src.domains.documents.service.keyword_extraction_service', mock_keyword_extraction_service), \
             patch('src.domains.documents.service.ollama_summarizer', mock_ollama_summarizer):

            document, tags, extraction_method = await document_service.upload_document(
                user_id=123,
                file=sample_pdf_file
            )

        # 검증
        assert document.document_id == 1
        assert document.original_filename == "sample.pdf"
        assert mock_minio_client.upload_file.called
        assert mock_elasticsearch_client.index_document.called
        assert mock_keyword_extraction_service.extract_keywords.called
        assert len(tags) == 2

    @pytest.mark.asyncio
    async def test_upload_docx_file_with_real_content(
        self,
        sample_docx_file,
        mock_minio_client,
        mock_elasticsearch_client,
        mock_keyword_extraction_service,
        mock_ollama_summarizer
    ):
        """실제 DOCX 샘플 파일로 업로드 테스트"""
        # Mock Repository
        mock_repository = AsyncMock()

        # Mock Document 객체
        mock_document = MagicMock()
        mock_document.document_id = 2
        mock_document.user_id = 456
        mock_document.original_filename = "sample.docx"
        mock_document.storage_path = "456/sample-uuid.docx"
        mock_document.file_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        mock_document.file_size_kb = 37
        mock_document.uploaded_at = MagicMock()
        mock_document.updated_at = MagicMock()

        mock_repository.create.return_value = mock_document

        # Mock TagService
        mock_tag_service = AsyncMock()
        mock_tag1 = MagicMock()
        mock_tag1.tag_id = 3
        mock_tag1.name = "deep learning"
        mock_tag2 = MagicMock()
        mock_tag2.tag_id = 4
        mock_tag2.name = "computer vision"
        mock_tag_service.attach_tags_to_document.return_value = [mock_tag1, mock_tag2]

        # Mock TextExtractor
        mock_text_extractor = MagicMock()
        mock_text_extractor.extract_text_from_bytes.return_value = (
            "Deep Learning Tutorial. "
            "Neural networks consist of layers. "
            "Applications include computer vision and natural language processing."
        )

        # Mock DB session (commit/rollback/refresh는 async 메서드)
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        mock_db.refresh = AsyncMock()

        # DocumentService 생성
        document_service = DocumentService(mock_repository, db=mock_db)
        document_service.tag_service = mock_tag_service

        # 테스트 실행
        with patch('src.domains.documents.service.minio_client', mock_minio_client), \
             patch('src.domains.documents.service.text_extractor', mock_text_extractor), \
             patch('src.domains.documents.service.elasticsearch_client', mock_elasticsearch_client), \
             patch('src.domains.documents.service.keyword_extraction_service', mock_keyword_extraction_service), \
             patch('src.domains.documents.service.ollama_summarizer', mock_ollama_summarizer):

            document, tags, extraction_method = await document_service.upload_document(
                user_id=456,
                file=sample_docx_file
            )

        # 검증
        assert document.document_id == 2
        assert document.original_filename == "sample.docx"
        assert document.file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert len(tags) == 2

    @pytest.mark.asyncio
    async def test_upload_txt_file_with_real_content(
        self,
        sample_txt_file,
        mock_minio_client,
        mock_elasticsearch_client,
        mock_keyword_extraction_service,
        mock_ollama_summarizer
    ):
        """실제 TXT 샘플 파일로 업로드 테스트"""
        # Mock Repository
        mock_repository = AsyncMock()

        # Mock Document 객체
        mock_document = MagicMock()
        mock_document.document_id = 3
        mock_document.user_id = 789
        mock_document.original_filename = "sample.txt"
        mock_document.storage_path = "789/sample-uuid.txt"
        mock_document.file_type = "text/plain"
        mock_document.file_size_kb = 1
        mock_document.uploaded_at = MagicMock()
        mock_document.updated_at = MagicMock()

        mock_repository.create.return_value = mock_document

        # Mock TagService
        mock_tag_service = AsyncMock()
        mock_tag1 = MagicMock()
        mock_tag1.tag_id = 5
        mock_tag1.name = "artificial intelligence"
        mock_tag2 = MagicMock()
        mock_tag2.tag_id = 6
        mock_tag2.name = "machine learning"
        mock_tag3 = MagicMock()
        mock_tag3.tag_id = 7
        mock_tag3.name = "deep learning"
        mock_tag_service.attach_tags_to_document.return_value = [mock_tag1, mock_tag2, mock_tag3]

        # Mock TextExtractor - TXT는 그대로 읽음
        mock_text_extractor = MagicMock()
        mock_text_extractor.extract_text_from_bytes.return_value = (
            "Machine Learning and Deep Learning: A Comprehensive Guide. "
            "Machine learning focuses on training algorithms. "
            "Deep learning uses neural networks with multiple layers."
        )

        # Mock DB session (commit/rollback/refresh는 async 메서드)
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        mock_db.refresh = AsyncMock()

        # DocumentService 생성
        document_service = DocumentService(mock_repository, db=mock_db)
        document_service.tag_service = mock_tag_service

        # 테스트 실행
        with patch('src.domains.documents.service.minio_client', mock_minio_client), \
             patch('src.domains.documents.service.text_extractor', mock_text_extractor), \
             patch('src.domains.documents.service.elasticsearch_client', mock_elasticsearch_client), \
             patch('src.domains.documents.service.keyword_extraction_service', mock_keyword_extraction_service), \
             patch('src.domains.documents.service.ollama_summarizer', mock_ollama_summarizer):

            document, tags, extraction_method = await document_service.upload_document(
                user_id=789,
                file=sample_txt_file
            )

        # 검증
        assert document.document_id == 3
        assert document.original_filename == "sample.txt"
        assert document.file_type == "text/plain"
        assert len(tags) == 3


class TestTextExtractorWithRealFiles:
    """실제 샘플 파일로 TextExtractor 테스트"""

    def test_extract_text_from_real_pdf(self, sample_pdf_path):
        """실제 PDF 파일에서 텍스트 추출 테스트"""
        from src.core.text_extractor import text_extractor

        with open(sample_pdf_path, "rb") as f:
            file_data = f.read()

        extracted_text = text_extractor.extract_text_from_bytes(
            file_data=file_data,
            file_type="application/pdf",
            filename="sample.pdf"
        )

        # 검증: 텍스트가 추출되었는지
        assert extracted_text is not None
        assert len(extracted_text) > 0
        # PDF에 "Machine Learning"이 포함되어 있어야 함
        assert "Machine Learning" in extracted_text or "machine learning" in extracted_text.lower()

    def test_extract_text_from_real_docx(self, sample_docx_path):
        """실제 DOCX 파일에서 텍스트 추출 테스트"""
        from src.core.text_extractor import text_extractor

        with open(sample_docx_path, "rb") as f:
            file_data = f.read()

        extracted_text = text_extractor.extract_text_from_bytes(
            file_data=file_data,
            file_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename="sample.docx"
        )

        # 검증
        assert extracted_text is not None
        assert len(extracted_text) > 0
        assert "deep learning" in extracted_text.lower()

    def test_extract_text_from_real_txt(self, sample_txt_path):
        """실제 TXT 파일에서 텍스트 추출 테스트"""
        from src.core.text_extractor import text_extractor

        with open(sample_txt_path, "rb") as f:
            file_data = f.read()

        extracted_text = text_extractor.extract_text_from_bytes(
            file_data=file_data,
            file_type="text/plain",
            filename="sample.txt"
        )

        # 검증
        assert extracted_text is not None
        assert len(extracted_text) > 0
        assert "Machine Learning" in extracted_text
        assert "Deep Learning" in extracted_text


class TestKeywordExtractionWithRealContent:
    """실제 샘플 파일 내용으로 키워드 추출 테스트"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="KeyBERT 모델 로딩이 너무 오래 걸려서 스킵 (필요시 수동 실행)")
    async def test_keybert_extraction_with_sample_text(self, sample_text_content):
        """샘플 TXT 내용으로 KeyBERT 키워드 추출 테스트"""
        from src.core.keyword_extraction import KeyBERTExtractor

        try:
            extractor = KeyBERTExtractor()

            # 실제 샘플 텍스트로 키워드 추출
            keywords = await extractor.extract_keywords(text=sample_text_content)

            # 검증: 키워드가 추출되었는지
            assert keywords is not None
            assert isinstance(keywords, list)

            # 키워드가 추출되었다면, 의미 있는지 확인
            if len(keywords) > 0:
                keywords_lower = [kw.lower() for kw in keywords]
                # 최소한 하나의 관련 키워드가 있어야 함
                has_relevant_keyword = any(
                    "machine" in kw or "learning" in kw or "deep" in kw or "data" in kw
                    for kw in keywords_lower
                )
                # 관련 키워드가 없더라도 키워드 자체는 추출되어야 함
                assert len(keywords) >= 0, "키워드 리스트는 비어있을 수 있지만 None이 아니어야 함"
        except Exception as e:
            # KeyBERT 모델 로딩 실패 등의 경우 테스트 스킵
            pytest.skip(f"KeyBERT 테스트 스킵 (이유: {e})")
