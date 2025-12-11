"""Integration tests for Document AI workflow."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingestion.pdf_extractor import PDFExtractor
from services.document_ai_service import DocumentAIService, DocumentAIResult


class TestDocumentAIIntegration:
    """Integration tests for complete Document AI workflow."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_document_ai_extraction(
        self, sample_pdf_bytes, mock_production_settings, mock_documentai_client, mock_document_ai_response
    ):
        """Test complete workflow from PDF upload to Document AI extraction."""
        with patch('services.document_ai_service.documentai') as mock_documentai_module, \
             patch('ingestion.pdf_extractor.settings', mock_production_settings), \
             patch('services.document_ai_service.settings', mock_production_settings):
            
            # Setup Document AI mock
            mock_documentai_module.DocumentProcessorServiceClient.return_value = mock_documentai_client
            
            # Create service and extractor
            pdf_extractor = PDFExtractor()
            
            # Extract document
            result = await pdf_extractor.extract(sample_pdf_bytes, "integration_test.pdf")
            
            # Verify extraction results
            assert "text" in result
            assert "content_hash" in result
            assert "page_count" in result
            assert "metadata" in result
            assert "extraction_metadata" in result
            
            # Verify Document AI was used
            extraction_meta = result["extraction_metadata"]
            assert extraction_meta["extraction_method"] == "google_document_ai"
            assert extraction_meta["confidence"] > 0
            assert "pages" in extraction_meta
            assert "tables" in extraction_meta
            assert "entities" in extraction_meta
    
    @pytest.mark.asyncio
    async def test_environment_based_routing(self, sample_pdf_bytes):
        """Test that extraction method changes based on environment."""
        # Test development environment
        with patch('ingestion.pdf_extractor.settings') as mock_settings, \
             patch('ingestion.pdf_extractor.pdfplumber') as mock_pdfplumber:
            
            mock_settings.should_use_document_ai = False
            mock_settings.is_development = True
            
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Dev content"
            mock_pdf.pages = [mock_page]
            mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
            
            extractor = PDFExtractor()
            result = await extractor.extract(sample_pdf_bytes, "test.pdf")
            
            assert result["metadata"]["extraction_method"] == "pdfplumber"
        
        # Test production environment
        with patch('ingestion.pdf_extractor.settings') as mock_settings, \
             patch('ingestion.pdf_extractor.DocumentAIService') as MockDocAIService:
            
            mock_settings.should_use_document_ai = True
            mock_settings.is_production = True
            
            mock_service = MagicMock()
            mock_result = DocumentAIResult(
                text="Prod content",
                confidence=0.95,
                pages=[],
                tables=[],
                entities=[],
                metadata={"extraction_method": "google_document_ai"}
            )
            mock_service.process_pdf = AsyncMock(return_value=mock_result)
            MockDocAIService.return_value = mock_service
            
            extractor = PDFExtractor()
            result = await extractor.extract(sample_pdf_bytes, "test.pdf")
            
            assert result["extraction_metadata"]["extraction_method"] == "google_document_ai"
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self, sample_pdf_bytes, mock_production_settings):
        """Test graceful degradation from Document AI to basic OCR."""
        with patch('ingestion.pdf_extractor.settings', mock_production_settings), \
             patch('ingestion.pdf_extractor.DocumentAIService') as MockDocAIService, \
             patch('ingestion.pdf_extractor.pdfplumber') as mock_pdfplumber:
            
            # Mock Document AI failure
            mock_service = MagicMock()
            mock_service.process_pdf = AsyncMock(side_effect=Exception("API timeout"))
            MockDocAIService.return_value = mock_service
            
            # Mock pdfplumber success
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Fallback content"
            mock_pdf.pages = [mock_page]
            mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
            
            extractor = PDFExtractor()
            result = await extractor.extract(sample_pdf_bytes, "test.pdf")
            
            # Should successfully extract using fallback
            assert result["text"] == "Fallback content"
            assert result["metadata"]["extraction_method"] == "pdfplumber"
    
    @pytest.mark.asyncio
    async def test_table_extraction_workflow(self, sample_pdf_bytes, mock_production_settings):
        """Test complete workflow for documents with tables."""
        with patch('ingestion.pdf_extractor.settings', mock_production_settings), \
             patch('ingestion.pdf_extractor.DocumentAIService') as MockDocAIService:
            
            # Mock Document AI with table data
            mock_service = MagicMock()
            mock_result = DocumentAIResult(
                text="Document with property listings\n\nProperty | Price | Bedrooms\nHouse A | $500,000 | 3\nHouse B | $750,000 | 4",
                confidence=0.96,
                pages=[{"page_number": 1}],
                tables=[
                    {
                        "page": 1,
                        "confidence": 0.94,
                        "header_rows": [["Property", "Price", "Bedrooms"]],
                        "body_rows": [
                            ["House A", "$500,000", "3"],
                            ["House B", "$750,000", "4"]
                        ]
                    }
                ],
                entities=[
                    {"type": "money", "text": "$500,000", "confidence": 0.99, "normalized_value": "500000"},
                    {"type": "money", "text": "$750,000", "confidence": 0.99, "normalized_value": "750000"}
                ],
                metadata={"extraction_method": "google_document_ai"}
            )
            mock_service.process_pdf = AsyncMock(return_value=mock_result)
            MockDocAIService.return_value = mock_service
            
            extractor = PDFExtractor()
            result = await extractor.extract(sample_pdf_bytes, "property_listing.pdf")
            
            # Verify table extraction
            assert len(result["extraction_metadata"]["tables"]) == 1
            table = result["extraction_metadata"]["tables"][0]
            assert table["confidence"] == 0.94
            assert len(table["body_rows"]) == 2
            
            # Verify entity extraction
            assert len(result["extraction_metadata"]["entities"]) == 2
            money_entities = [e for e in result["extraction_metadata"]["entities"] if e["type"] == "money"]
            assert len(money_entities) == 2
    
    @pytest.mark.asyncio
    async def test_quality_metrics_tracking(self, sample_pdf_bytes, mock_production_settings):
        """Test that quality metrics are properly tracked."""
        with patch('ingestion.pdf_extractor.settings', mock_production_settings), \
             patch('ingestion.pdf_extractor.DocumentAIService') as MockDocAIService:
            
            # Mock high-quality extraction
            mock_service = MagicMock()
            mock_result = DocumentAIResult(
                text="High quality document",
                confidence=0.98,
                pages=[
                    {
                        "page_number": 1,
                        "blocks": [{"confidence": 0.99}],
                        "paragraphs": [{"confidence": 0.98}]
                    }
                ],
                tables=[],
                entities=[],
                metadata={
                    "extraction_method": "google_document_ai",
                    "requires_review": False,
                    "warnings": []
                }
            )
            mock_service.process_pdf = AsyncMock(return_value=mock_result)
            MockDocAIService.return_value = mock_service
            
            extractor = PDFExtractor()
            result = await extractor.extract(sample_pdf_bytes, "high_quality.pdf")
            
            # Verify quality metrics
            assert result["extraction_metadata"]["confidence"] == 0.98
            assert result["extraction_metadata"]["requires_review"] is False
            assert len(result["extraction_metadata"]["warnings"]) == 0
    
    @pytest.mark.asyncio
    async def test_metadata_preservation(self, sample_pdf_bytes, mock_production_settings):
        """Test that all metadata is preserved through the extraction pipeline."""
        with patch('ingestion.pdf_extractor.settings', mock_production_settings), \
             patch('ingestion.pdf_extractor.DocumentAIService') as MockDocAIService:
            
            mock_service = MagicMock()
            mock_result = DocumentAIResult(
                text="Test document",
                confidence=0.95,
                pages=[
                    {
                        "page_number": 1,
                        "width": 8.5,
                        "height": 11.0,
                        "blocks": [],
                        "paragraphs": [],
                        "lines": [],
                        "tokens": []
                    }
                ],
                tables=[],
                entities=[],
                metadata={
                    "extraction_method": "google_document_ai",
                    "environment": "production",
                    "processor_id": "test-processor-456"
                }
            )
            mock_service.process_pdf = AsyncMock(return_value=mock_result)
            MockDocAIService.return_value = mock_service
            
            extractor = PDFExtractor()
            result = await extractor.extract(sample_pdf_bytes, "metadata_test.pdf")
            
            # Verify all metadata fields are present
            assert "extraction_metadata" in result
            extraction_meta = result["extraction_metadata"]
            assert extraction_meta["extraction_method"] == "google_document_ai"
            assert extraction_meta["environment"] == "production"
            assert "processor_id" in extraction_meta
            
            # Verify page metadata
            assert len(extraction_meta["pages"]) == 1
            page = extraction_meta["pages"][0]
            assert page["page_number"] == 1
            assert page["width"] == 8.5
            assert page["height"] == 11.0
