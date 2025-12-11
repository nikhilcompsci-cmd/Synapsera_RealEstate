"""Unit tests for PDFExtractor Document AI integration."""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingestion.pdf_extractor import PDFExtractor
from services.document_ai_service import DocumentAIResult


class TestPDFExtractorDocumentAI:
    """Test PDFExtractor integration with Document AI."""
    
    @pytest.fixture
    def pdf_extractor(self):
        """Create PDFExtractor instance."""
        return PDFExtractor()
    
    @pytest.mark.asyncio
    async def test_extract_development_mode(self, pdf_extractor, sample_pdf_bytes, mock_settings):
        """Test extraction in development mode uses basic OCR."""
        with patch('ingestion.pdf_extractor.settings', mock_settings), \
             patch('ingestion.pdf_extractor.pdfplumber') as mock_pdfplumber:
            
            # Mock pdfplumber
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Development mode content"
            mock_pdf.pages = [mock_page]
            mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
            
            result = await pdf_extractor.extract(sample_pdf_bytes, "test.pdf")
            
            assert result["text"] == "Development mode content"
            assert result["page_count"] == 1
            assert "content_hash" in result
            assert result["metadata"]["extraction_method"] == "pdfplumber"
    
    @pytest.mark.asyncio
    async def test_extract_production_mode_with_document_ai(
        self, pdf_extractor, sample_pdf_bytes, mock_production_settings
    ):
        """Test extraction in production mode uses Document AI."""
        with patch('ingestion.pdf_extractor.settings', mock_production_settings), \
             patch('ingestion.pdf_extractor.DocumentAIService') as MockDocAIService:
            
            # Mock Document AI service
            mock_service = MagicMock()
            mock_result = DocumentAIResult(
                text="Production Document AI content",
                confidence=0.95,
                pages=[{"page_number": 1, "blocks": [], "paragraphs": []}],
                tables=[{"confidence": 0.92, "header_rows": [], "body_rows": []}],
                entities=[{"type": "date", "text": "2024-01-15", "confidence": 0.98}],
                metadata={"extraction_method": "google_document_ai", "environment": "production"}
            )
            mock_service.process_pdf = AsyncMock(return_value=mock_result)
            MockDocAIService.return_value = mock_service
            
            result = await pdf_extractor.extract(sample_pdf_bytes, "test.pdf")
            
            assert result["text"] == "Production Document AI content"
            assert result["page_count"] == 1
            assert "content_hash" in result
            assert result["extraction_metadata"]["extraction_method"] == "google_document_ai"
            assert result["extraction_metadata"]["confidence"] == 0.95
            assert len(result["extraction_metadata"]["tables"]) == 1
            assert len(result["extraction_metadata"]["entities"]) == 1
    
    @pytest.mark.asyncio
    async def test_extract_with_document_ai_method(
        self, pdf_extractor, sample_pdf_bytes, mock_production_settings
    ):
        """Test extract_with_document_ai method directly."""
        with patch('ingestion.pdf_extractor.settings', mock_production_settings), \
             patch('ingestion.pdf_extractor.DocumentAIService') as MockDocAIService:
            
            # Mock Document AI service
            mock_service = MagicMock()
            mock_result = DocumentAIResult(
                text="Direct Document AI call",
                confidence=0.97,
                pages=[],
                tables=[],
                entities=[],
                metadata={"extraction_method": "google_document_ai"}
            )
            mock_service.process_pdf = AsyncMock(return_value=mock_result)
            MockDocAIService.return_value = mock_service
            
            result = await pdf_extractor.extract_with_document_ai(sample_pdf_bytes, "test.pdf")
            
            assert result["text"] == "Direct Document AI call"
            assert result["extraction_metadata"]["confidence"] == 0.97
            assert result["extraction_metadata"]["extraction_method"] == "google_document_ai"
    
    @pytest.mark.asyncio
    async def test_extract_fallback_on_document_ai_error(
        self, pdf_extractor, sample_pdf_bytes, mock_production_settings
    ):
        """Test fallback to basic extraction when Document AI fails."""
        with patch('ingestion.pdf_extractor.settings', mock_production_settings), \
             patch('ingestion.pdf_extractor.DocumentAIService') as MockDocAIService, \
             patch('ingestion.pdf_extractor.pdfplumber') as mock_pdfplumber:
            
            # Mock Document AI failure
            mock_service = MagicMock()
            mock_service.process_pdf = AsyncMock(side_effect=Exception("Document AI API error"))
            MockDocAIService.return_value = mock_service
            
            # Mock pdfplumber success
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Fallback extraction"
            mock_pdf.pages = [mock_page]
            mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
            
            result = await pdf_extractor.extract(sample_pdf_bytes, "test.pdf")
            
            assert result["text"] == "Fallback extraction"
            assert result["metadata"]["extraction_method"] == "pdfplumber"
    
    @pytest.mark.asyncio
    async def test_extract_with_tables_and_entities(
        self, pdf_extractor, sample_pdf_bytes, mock_production_settings
    ):
        """Test extraction preserves tables and entities from Document AI."""
        with patch('ingestion.pdf_extractor.settings', mock_production_settings), \
             patch('ingestion.pdf_extractor.DocumentAIService') as MockDocAIService:
            
            # Mock Document AI with rich metadata
            mock_service = MagicMock()
            mock_result = DocumentAIResult(
                text="Document with tables and entities",
                confidence=0.96,
                pages=[{"page_number": 1}],
                tables=[
                    {
                        "confidence": 0.94,
                        "header_rows": [["Name", "Age"]],
                        "body_rows": [["John", "30"], ["Jane", "25"]]
                    }
                ],
                entities=[
                    {"type": "person_name", "text": "John", "confidence": 0.98},
                    {"type": "age", "text": "30", "confidence": 0.95}
                ],
                metadata={"extraction_method": "google_document_ai"}
            )
            mock_service.process_pdf = AsyncMock(return_value=mock_result)
            MockDocAIService.return_value = mock_service
            
            result = await pdf_extractor.extract(sample_pdf_bytes, "test.pdf")
            
            # Verify tables are preserved
            assert len(result["extraction_metadata"]["tables"]) == 1
            table = result["extraction_metadata"]["tables"][0]
            assert table["confidence"] == 0.94
            assert len(table["header_rows"]) == 1
            assert len(table["body_rows"]) == 2
            
            # Verify entities are preserved
            assert len(result["extraction_metadata"]["entities"]) == 2
            entity = result["extraction_metadata"]["entities"][0]
            assert entity["type"] == "person_name"
            assert entity["confidence"] == 0.98
    
    @pytest.mark.asyncio
    async def test_extract_with_low_confidence_warning(
        self, pdf_extractor, sample_pdf_bytes, mock_production_settings
    ):
        """Test that low confidence extraction adds warning metadata."""
        with patch('ingestion.pdf_extractor.settings', mock_production_settings), \
             patch('ingestion.pdf_extractor.DocumentAIService') as MockDocAIService:
            
            # Mock low confidence result
            mock_service = MagicMock()
            mock_result = DocumentAIResult(
                text="Low quality extraction",
                confidence=0.65,  # Below threshold
                pages=[],
                tables=[],
                entities=[],
                metadata={
                    "extraction_method": "google_document_ai",
                    "requires_review": True,
                    "warnings": ["Low confidence score"]
                }
            )
            mock_service.process_pdf = AsyncMock(return_value=mock_result)
            MockDocAIService.return_value = mock_service
            
            result = await pdf_extractor.extract(sample_pdf_bytes, "test.pdf")
            
            assert result["extraction_metadata"]["confidence"] == 0.65
            assert result["extraction_metadata"]["requires_review"] is True
            assert len(result["extraction_metadata"]["warnings"]) > 0
    
    def test_calculate_content_hash(self, pdf_extractor, sample_pdf_bytes):
        """Test content hash calculation is consistent."""
        hash1 = pdf_extractor.calculate_content_hash(sample_pdf_bytes)
        hash2 = pdf_extractor.calculate_content_hash(sample_pdf_bytes)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest length
    
    def test_calculate_content_hash_different_content(self, pdf_extractor):
        """Test different content produces different hashes."""
        content1 = b"PDF content 1"
        content2 = b"PDF content 2"
        
        hash1 = pdf_extractor.calculate_content_hash(content1)
        hash2 = pdf_extractor.calculate_content_hash(content2)
        
        assert hash1 != hash2
    
    @pytest.mark.asyncio
    async def test_extract_handles_unicode_content(
        self, pdf_extractor, mock_production_settings
    ):
        """Test extraction handles unicode characters correctly."""
        with patch('ingestion.pdf_extractor.settings', mock_production_settings), \
             patch('ingestion.pdf_extractor.DocumentAIService') as MockDocAIService:
            
            # Mock result with unicode
            mock_service = MagicMock()
            mock_result = DocumentAIResult(
                text="Document with unicode: café, naïve, 日本語",
                confidence=0.95,
                pages=[],
                tables=[],
                entities=[],
                metadata={"extraction_method": "google_document_ai"}
            )
            mock_service.process_pdf = AsyncMock(return_value=mock_result)
            MockDocAIService.return_value = mock_service
            
            result = await pdf_extractor.extract(b"%PDF-1.4", "test.pdf")
            
            assert "café" in result["text"]
            assert "naïve" in result["text"]
            assert "日本語" in result["text"]
