"""Unit tests for DocumentAIService."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.document_ai_service import DocumentAIService, DocumentAIResult


class TestDocumentAIService:
    """Test suite for DocumentAIService."""
    
    def test_initialization_development(self, mock_settings):
        """Test service initialization in development mode."""
        service = DocumentAIService(mock_settings)
        assert service.settings == mock_settings
        assert service.documentai_client is None
        assert service.processor_name is None
    
    def test_initialization_production(self, mock_production_settings):
        """Test service initialization in production mode."""
        with patch('services.document_ai_service.documentai') as mock_documentai:
            mock_client = MagicMock()
            mock_documentai.DocumentProcessorServiceClient.return_value = mock_client
            
            service = DocumentAIService(mock_production_settings)
            assert service.settings == mock_production_settings
            # Client should be initialized lazily
            assert service.documentai_client is None
    
    def test_should_use_document_ai_development(self, mock_settings):
        """Test Document AI should not be used in development."""
        service = DocumentAIService(mock_settings)
        assert not service.settings.should_use_document_ai
    
    def test_should_use_document_ai_production(self, mock_production_settings):
        """Test Document AI should be used in production with valid config."""
        service = DocumentAIService(mock_production_settings)
        assert service.settings.should_use_document_ai
    
    @pytest.mark.asyncio
    async def test_process_pdf_development_mode(self, mock_settings, sample_pdf_bytes):
        """Test PDF processing in development mode uses basic OCR."""
        with patch('services.document_ai_service.pdfplumber') as mock_pdfplumber:
            # Mock pdfplumber extraction
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Test document content"
            mock_pdf.pages = [mock_page]
            mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
            
            service = DocumentAIService(mock_settings)
            result = await service.process_pdf(sample_pdf_bytes, "test.pdf")
            
            assert isinstance(result, DocumentAIResult)
            assert result.text == "Test document content"
            assert result.metadata["extraction_method"] == "basic_ocr"
            assert result.metadata["environment"] == "development"
    
    @pytest.mark.asyncio
    async def test_process_pdf_production_mode(
        self, mock_production_settings, sample_pdf_bytes, mock_documentai_client, mock_document_ai_response
    ):
        """Test PDF processing in production mode uses Document AI."""
        with patch('services.document_ai_service.documentai') as mock_documentai_module:
            mock_documentai_module.DocumentProcessorServiceClient.return_value = mock_documentai_client
            
            service = DocumentAIService(mock_production_settings)
            service.documentai_client = mock_documentai_client
            service.processor_name = "projects/test-project-123/locations/us/processors/test-processor-456"
            
            result = await service.process_pdf(sample_pdf_bytes, "test.pdf")
            
            assert isinstance(result, DocumentAIResult)
            assert "Test Document" in result.text
            assert result.metadata["extraction_method"] == "google_document_ai"
            assert result.metadata["environment"] == "production"
            assert result.confidence > 0
    
    @pytest.mark.asyncio
    async def test_process_pdf_fallback_on_error(
        self, mock_production_settings, sample_pdf_bytes
    ):
        """Test fallback to basic OCR when Document AI fails."""
        with patch('services.document_ai_service.documentai') as mock_documentai_module, \
             patch('services.document_ai_service.pdfplumber') as mock_pdfplumber:
            
            # Mock Document AI failure
            mock_client = MagicMock()
            mock_client.process_document.side_effect = Exception("API Error")
            mock_documentai_module.DocumentProcessorServiceClient.return_value = mock_client
            
            # Mock pdfplumber success
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Fallback content"
            mock_pdf.pages = [mock_page]
            mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
            
            service = DocumentAIService(mock_production_settings)
            service.documentai_client = mock_client
            service.processor_name = "projects/test-project-123/locations/us/processors/test-processor-456"
            
            result = await service.process_pdf(sample_pdf_bytes, "test.pdf")
            
            assert isinstance(result, DocumentAIResult)
            assert result.text == "Fallback content"
            assert result.metadata["extraction_method"] == "basic_ocr"
            assert "fallback" in result.metadata.get("notes", "").lower()
    
    def test_extract_pages_info(self, mock_document_ai_response):
        """Test page information extraction."""
        service = DocumentAIService(Mock())
        pages_info = service._extract_pages_info(
            mock_document_ai_response.document,
            mock_document_ai_response.document.text
        )
        
        assert len(pages_info) == 1
        page_info = pages_info[0]
        assert page_info["page_number"] == 1
        assert page_info["width"] == 8.5
        assert page_info["height"] == 11.0
        assert len(page_info["blocks"]) > 0
        assert len(page_info["paragraphs"]) > 0
        assert len(page_info["lines"]) > 0
        assert len(page_info["tokens"]) > 0
    
    def test_extract_tables_info(self, mock_document_ai_response):
        """Test table information extraction."""
        service = DocumentAIService(Mock())
        tables_info = service._extract_tables_info(
            mock_document_ai_response.document,
            mock_document_ai_response.document.text
        )
        
        assert len(tables_info) > 0
        table_info = tables_info[0]
        assert table_info["confidence"] == 0.92
        assert "header_rows" in table_info
        assert "body_rows" in table_info
        assert len(table_info["header_rows"]) > 0
        assert len(table_info["body_rows"]) > 0
    
    def test_extract_entities_info(self, mock_document_ai_response):
        """Test entity information extraction."""
        service = DocumentAIService(Mock())
        entities_info = service._extract_entities_info(mock_document_ai_response.document)
        
        assert len(entities_info) > 0
        entity_info = entities_info[0]
        assert entity_info["type"] == "date"
        assert entity_info["text"] == "2024-01-15"
        assert entity_info["confidence"] == 0.98
        assert entity_info["normalized_value"] == "2024-01-15"
    
    def test_calculate_overall_confidence(self, mock_document_ai_response):
        """Test overall confidence calculation."""
        service = DocumentAIService(Mock())
        pages_info = service._extract_pages_info(
            mock_document_ai_response.document,
            mock_document_ai_response.document.text
        )
        
        confidence = service._calculate_overall_confidence(pages_info)
        assert 0 <= confidence <= 1.0
        assert confidence > 0  # Should have some confidence from mock data
    
    @pytest.mark.asyncio
    async def test_process_pdf_with_empty_document(self, mock_settings):
        """Test handling of empty PDF document."""
        with patch('services.document_ai_service.pdfplumber') as mock_pdfplumber:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = ""
            mock_pdf.pages = [mock_page]
            mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
            
            # Mock pytesseract for fallback
            with patch('services.document_ai_service.pytesseract') as mock_pytesseract:
                mock_pytesseract.image_to_string.return_value = "OCR extracted text"
                
                service = DocumentAIService(mock_settings)
                result = await service.process_pdf(b"%PDF-1.4", "empty.pdf")
                
                assert isinstance(result, DocumentAIResult)
                # Should attempt OCR fallback
    
    @pytest.mark.asyncio
    async def test_process_pdf_low_confidence_flagging(
        self, mock_production_settings, sample_pdf_bytes, mock_documentai_client
    ):
        """Test that low confidence documents are flagged for review."""
        with patch('services.document_ai_service.documentai') as mock_documentai_module:
            # Create response with low confidence
            mock_response = MagicMock()
            mock_response.document.text = "Low quality text"
            mock_page = MagicMock()
            mock_page.page_number = 1
            mock_block = MagicMock()
            mock_block.layout.confidence = 0.5  # Low confidence
            mock_block.layout.text_anchor.text_segments = [MagicMock(start_index=0, end_index=10)]
            mock_page.blocks = [mock_block]
            mock_page.paragraphs = []
            mock_page.lines = []
            mock_page.tokens = []
            mock_page.tables = []
            mock_response.document.pages = [mock_page]
            mock_response.document.entities = []
            
            mock_client = MagicMock()
            mock_client.process_document.return_value = mock_response
            mock_documentai_module.DocumentProcessorServiceClient.return_value = mock_client
            
            service = DocumentAIService(mock_production_settings)
            service.documentai_client = mock_client
            service.processor_name = "projects/test/locations/us/processors/test"
            
            result = await service.process_pdf(sample_pdf_bytes, "low_quality.pdf")
            
            # Check if flagged for review
            assert result.confidence < 0.8
            assert result.metadata.get("requires_review") is True


class TestDocumentAIResult:
    """Test DocumentAIResult dataclass."""
    
    def test_document_ai_result_creation(self):
        """Test creating DocumentAIResult instance."""
        result = DocumentAIResult(
            text="Test content",
            confidence=0.95,
            pages=[{"page_number": 1}],
            tables=[{"confidence": 0.9}],
            entities=[{"type": "date", "text": "2024-01-15"}],
            metadata={"extraction_method": "google_document_ai"}
        )
        
        assert result.text == "Test content"
        assert result.confidence == 0.95
        assert len(result.pages) == 1
        assert len(result.tables) == 1
        assert len(result.entities) == 1
        assert result.metadata["extraction_method"] == "google_document_ai"
    
    def test_document_ai_result_defaults(self):
        """Test DocumentAIResult with default values."""
        result = DocumentAIResult(
            text="Minimal content",
            confidence=0.8,
            pages=[],
            tables=[],
            entities=[],
            metadata={}
        )
        
        assert result.text == "Minimal content"
        assert result.confidence == 0.8
        assert result.pages == []
        assert result.tables == []
        assert result.entities == []
