"""Pytest configuration and fixtures for AI Brain tests."""
import os
import sys
from pathlib import Path
import pytest
from unittest.mock import Mock, MagicMock
from io import BytesIO

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import Settings


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock(spec=Settings)
    settings.environment = "development"
    settings.is_development = True
    settings.is_production = False
    settings.gcp_project_id = ""
    settings.documentai_location = "us"
    settings.documentai_processor_id = ""
    settings.documentai_min_confidence = 0.8
    settings.use_document_ai_in_production = True
    settings.use_document_ai_in_development = False
    settings.should_use_document_ai = False
    settings.sentry_enabled = False
    return settings


@pytest.fixture
def mock_production_settings():
    """Mock production settings with Document AI enabled."""
    settings = Mock(spec=Settings)
    settings.environment = "production"
    settings.is_development = False
    settings.is_production = True
    settings.gcp_project_id = "test-project-123"
    settings.documentai_location = "us"
    settings.documentai_processor_id = "test-processor-456"
    settings.documentai_min_confidence = 0.8
    settings.use_document_ai_in_production = True
    settings.use_document_ai_in_development = False
    settings.should_use_document_ai = True
    settings.sentry_enabled = False
    return settings


@pytest.fixture
def sample_pdf_bytes():
    """Sample PDF file bytes for testing."""
    # Minimal valid PDF structure
    pdf_header = b"%PDF-1.4\n"
    pdf_body = (
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
    )
    pdf_footer = b"xref\n0 4\ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n200\n%%EOF"
    return pdf_header + pdf_body + pdf_footer


@pytest.fixture
def sample_pdf_file(sample_pdf_bytes):
    """Sample PDF file-like object for testing."""
    return BytesIO(sample_pdf_bytes)


@pytest.fixture
def mock_document_ai_response():
    """Mock Document AI API response."""
    mock_response = MagicMock()
    mock_response.document.text = "Test Document\nThis is a sample document for testing.\nPage 1 content here."
    
    # Mock pages
    mock_page = MagicMock()
    mock_page.page_number = 1
    mock_page.dimension.width = 8.5
    mock_page.dimension.height = 11.0
    
    # Mock blocks
    mock_block = MagicMock()
    mock_block.layout.text_anchor.text_segments = [MagicMock(start_index=0, end_index=50)]
    mock_block.layout.confidence = 0.95
    mock_page.blocks = [mock_block]
    
    # Mock paragraphs
    mock_paragraph = MagicMock()
    mock_paragraph.layout.text_anchor.text_segments = [MagicMock(start_index=0, end_index=25)]
    mock_paragraph.layout.confidence = 0.97
    mock_page.paragraphs = [mock_paragraph]
    
    # Mock lines
    mock_line = MagicMock()
    mock_line.layout.text_anchor.text_segments = [MagicMock(start_index=0, end_index=13)]
    mock_line.layout.confidence = 0.99
    mock_page.lines = [mock_line]
    
    # Mock tokens
    mock_token = MagicMock()
    mock_token.layout.text_anchor.text_segments = [MagicMock(start_index=0, end_index=4)]
    mock_token.layout.confidence = 0.99
    mock_page.tokens = [mock_token]
    
    mock_response.document.pages = [mock_page]
    
    # Mock tables
    mock_table = MagicMock()
    mock_table.layout.confidence = 0.92
    
    # Mock table header row
    mock_header_row = MagicMock()
    mock_header_cell = MagicMock()
    mock_header_cell.layout.text_anchor.text_segments = [MagicMock(start_index=100, end_index=110)]
    mock_header_row.cells = [mock_header_cell]
    
    # Mock table body row
    mock_body_row = MagicMock()
    mock_body_cell = MagicMock()
    mock_body_cell.layout.text_anchor.text_segments = [MagicMock(start_index=111, end_index=120)]
    mock_body_row.cells = [mock_body_cell]
    
    mock_table.header_rows = [mock_header_row]
    mock_table.body_rows = [mock_body_row]
    
    mock_response.document.pages[0].tables = [mock_table]
    
    # Mock entities
    mock_entity = MagicMock()
    mock_entity.type_ = "date"
    mock_entity.mention_text = "2024-01-15"
    mock_entity.confidence = 0.98
    mock_entity.normalized_value.text = "2024-01-15"
    
    mock_response.document.entities = [mock_entity]
    
    return mock_response


@pytest.fixture
def mock_documentai_client(mock_document_ai_response):
    """Mock Google Document AI client."""
    mock_client = MagicMock()
    mock_client.process_document.return_value = mock_document_ai_response
    return mock_client
