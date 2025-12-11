"""
Google Document AI integration for production-grade PDF processing.

This service is used in PRODUCTION ONLY for high-accuracy document extraction.
Development environment uses basic pytesseract (free, local).

Features (Production):
- 95-99% OCR accuracy
- Layout-aware text extraction
- Table extraction with structure
- Entity recognition (addresses, dates, amounts)
- Confidence scoring
- Automatic quality flagging

Cost: ~$1.50 per 1000 pages (first 1000 pages/month free)
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import structlog
import uuid
from pathlib import Path

logger = structlog.get_logger()


@dataclass
class DocumentAIResult:
    """Document AI processing result with quality metadata."""
    text: str
    confidence: float  # 0-100
    pages_count: int
    tables_count: int
    entities_count: int
    layout_preserved: bool
    requires_review: bool
    warnings: List[str]
    method: str  # "document_ai" or "fallback"
    
    # Detailed page information
    pages: List[Dict] = None
    tables: List[Dict] = None
    entities: List[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class DocumentAIService:
    """
    Google Document AI service with environment-aware configuration.
    
    Usage:
        # In production (with GCP credentials)
        service = DocumentAIService()
        result = service.process_pdf("document.pdf")
        
        # In development (automatically uses fallback)
        service = DocumentAIService()
        result = service.process_pdf("document.pdf")  # Uses pytesseract
    """
    
    def __init__(self, settings=None):
        """
        Initialize Document AI service.
        
        Args:
            settings: Settings object (auto-loaded if not provided)
        """
        if settings is None:
            from config.settings import get_settings
            settings = get_settings()
        
        self.settings = settings
        self.logger = structlog.get_logger()
        
        # Only initialize Document AI client in production with valid config
        self.client = None
        self.processor_name = None
        
        if self.settings.should_use_document_ai:
            try:
                self._initialize_document_ai()
            except Exception as e:
                self.logger.warning(
                    "documentai_init_failed",
                    error=str(e),
                    environment=self.settings.environment,
                    fallback="will_use_basic_ocr"
                )
    
    def _initialize_document_ai(self):
        """Initialize Google Document AI client."""
        from google.cloud import documentai_v1 as documentai
        from google.api_core.client_options import ClientOptions
        
        if not self.settings.gcp_project_id:
            raise ValueError("GCP_PROJECT_ID not configured")
        
        if not self.settings.documentai_processor_id:
            raise ValueError("DOCUMENTAI_PROCESSOR_ID not configured")
        
        # Initialize client with location
        opts = ClientOptions(
            api_endpoint=f"{self.settings.documentai_location}-documentai.googleapis.com"
        )
        self.client = documentai.DocumentProcessorServiceClient(client_options=opts)
        
        # Build processor resource name
        self.processor_name = self.client.processor_path(
            self.settings.gcp_project_id,
            self.settings.documentai_location,
            self.settings.documentai_processor_id
        )
        
        self.logger.info(
            "documentai_initialized",
            project_id=self.settings.gcp_project_id,
            location=self.settings.documentai_location,
            processor_id=self.settings.documentai_processor_id
        )
    
    def process_pdf(self, pdf_path: str) -> DocumentAIResult:
        """
        Process PDF with environment-appropriate method.
        
        Production: Uses Google Document AI (high accuracy, costs money)
        Development: Uses basic OCR fallback (lower accuracy, free)
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            DocumentAIResult with extracted content and metadata
        """
        correlation_id = str(uuid.uuid4())
        
        self.logger.info(
            "pdf_processing_started",
            correlation_id=correlation_id,
            pdf_path=pdf_path,
            environment=self.settings.environment,
            will_use_document_ai=self.settings.should_use_document_ai
        )
        
        # Production: Use Document AI
        if self.client and self.processor_name:
            try:
                result = self._process_with_document_ai(pdf_path, correlation_id)
                self.logger.info(
                    "documentai_processing_completed",
                    correlation_id=correlation_id,
                    confidence=result.confidence,
                    pages=result.pages_count,
                    tables=result.tables_count
                )
                return result
                
            except Exception as e:
                self.logger.error(
                    "documentai_processing_failed",
                    correlation_id=correlation_id,
                    error=str(e),
                    exc_info=True
                )
                # Fall through to basic OCR
        
        # Development or fallback: Use basic OCR
        self.logger.info(
            "using_basic_ocr_fallback",
            correlation_id=correlation_id,
            reason="development_environment" if self.settings.is_development else "document_ai_unavailable"
        )
        return self._process_with_basic_ocr(pdf_path, correlation_id)
    
    def _process_with_document_ai(
        self,
        pdf_path: str,
        correlation_id: str
    ) -> DocumentAIResult:
        """Process PDF using Google Document AI (production only)."""
        from google.cloud import documentai_v1 as documentai
        
        # Read PDF file
        with open(pdf_path, "rb") as pdf_file:
            pdf_content = pdf_file.read()
        
        # Prepare request
        raw_document = documentai.RawDocument(
            content=pdf_content,
            mime_type="application/pdf"
        )
        
        request = documentai.ProcessRequest(
            name=self.processor_name,
            raw_document=raw_document
        )
        
        # Process document
        response = self.client.process_document(request=request)
        document = response.document
        
        # Extract full text
        text = document.text
        
        # Calculate overall confidence
        confidences = []
        for page in document.pages:
            if page.tokens:
                for token in page.tokens:
                    if token.layout and token.layout.confidence:
                        confidences.append(token.layout.confidence)
        
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        avg_confidence_percent = avg_confidence * 100
        
        # Extract pages info
        pages_info = self._extract_pages_info(document)
        
        # Extract tables
        tables_info = self._extract_tables_info(document, text)
        
        # Extract entities
        entities_info = self._extract_entities_info(document, text)
        
        # Generate warnings
        warnings = []
        if avg_confidence < self.settings.documentai_min_confidence:
            warnings.append(f"Low confidence: {avg_confidence_percent:.1f}%")
            warnings.append("Manual review recommended")
        
        return DocumentAIResult(
            text=text,
            confidence=avg_confidence_percent,
            pages_count=len(pages_info),
            tables_count=len(tables_info),
            entities_count=len(entities_info),
            layout_preserved=True,
            requires_review=avg_confidence < self.settings.documentai_min_confidence,
            warnings=warnings,
            method="document_ai",
            pages=pages_info,
            tables=tables_info,
            entities=entities_info
        )
    
    def _process_with_basic_ocr(
        self,
        pdf_path: str,
        correlation_id: str
    ) -> DocumentAIResult:
        """
        Process PDF using basic OCR (development fallback).
        
        Uses pdfplumber for direct text extraction, falls back to pytesseract for scanned PDFs.
        """
        import pdfplumber
        from pdf2image import convert_from_path
        import pytesseract
        
        text = ""
        method = "pdfplumber"
        pages_count = 0
        
        try:
            # Try direct text extraction first
            with pdfplumber.open(pdf_path) as pdf:
                pages_count = len(pdf.pages)
                text_parts = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                
                text = "\n\n".join(text_parts)
            
            # If no text extracted, use OCR
            if not text.strip():
                self.logger.info(
                    "direct_extraction_empty_using_ocr",
                    correlation_id=correlation_id
                )
                method = "pytesseract"
                images = convert_from_path(pdf_path)
                pages_count = len(images)
                text_parts = []
                
                for img in images:
                    page_text = pytesseract.image_to_string(img)
                    text_parts.append(page_text)
                
                text = "\n\n".join(text_parts)
        
        except Exception as e:
            self.logger.error(
                "basic_ocr_failed",
                correlation_id=correlation_id,
                error=str(e),
                exc_info=True
            )
            raise
        
        # Basic OCR doesn't provide confidence scores
        # Estimate based on text length and method
        estimated_confidence = 85.0 if method == "pdfplumber" else 70.0
        
        return DocumentAIResult(
            text=text,
            confidence=estimated_confidence,
            pages_count=pages_count,
            tables_count=0,  # Basic OCR doesn't extract tables
            entities_count=0,  # Basic OCR doesn't extract entities
            layout_preserved=method == "pdfplumber",
            requires_review=method == "pytesseract",  # OCR'd docs may need review
            warnings=["Using basic OCR (development mode)"] if self.settings.is_development else [],
            method=method,
            pages=None,
            tables=None,
            entities=None
        )
    
    def _extract_pages_info(self, document) -> List[Dict]:
        """Extract page-level information from Document AI response."""
        pages_info = []
        
        for page_num, page in enumerate(document.pages, start=1):
            # Calculate page confidence
            page_confidences = []
            if page.tokens:
                for token in page.tokens:
                    if token.layout and token.layout.confidence:
                        page_confidences.append(token.layout.confidence)
            
            page_confidence = (
                sum(page_confidences) / len(page_confidences) * 100
                if page_confidences else 0.0
            )
            
            pages_info.append({
                'page_number': page_num,
                'confidence': page_confidence,
                'dimensions': {
                    'width': page.dimension.width if page.dimension else 0,
                    'height': page.dimension.height if page.dimension else 0,
                    'unit': page.dimension.unit if page.dimension else 'pixels'
                },
                'blocks': len(page.blocks) if page.blocks else 0,
                'paragraphs': len(page.paragraphs) if page.paragraphs else 0,
                'lines': len(page.lines) if page.lines else 0,
                'tokens': len(page.tokens) if page.tokens else 0
            })
        
        return pages_info
    
    def _extract_tables_info(self, document, full_text: str) -> List[Dict]:
        """Extract table structure from Document AI response."""
        tables = []
        
        for page_num, page in enumerate(document.pages, start=1):
            if not page.tables:
                continue
            
            for table_idx, table in enumerate(page.tables):
                # Extract table rows
                rows = []
                
                # Process header rows
                if hasattr(table, 'header_rows'):
                    for row in table.header_rows:
                        row_cells = []
                        for cell in row.cells:
                            cell_text = self._extract_text_from_layout(cell.layout, full_text)
                            row_cells.append(cell_text)
                        rows.append(row_cells)
                
                # Process body rows
                if hasattr(table, 'body_rows'):
                    for row in table.body_rows:
                        row_cells = []
                        for cell in row.cells:
                            cell_text = self._extract_text_from_layout(cell.layout, full_text)
                            row_cells.append(cell_text)
                        rows.append(row_cells)
                
                tables.append({
                    'page': page_num,
                    'table_index': table_idx,
                    'rows': rows,
                    'row_count': len(rows),
                    'column_count': max(len(row) for row in rows) if rows else 0,
                    'confidence': table.layout.confidence * 100 if table.layout and table.layout.confidence else 0.0
                })
        
        return tables
    
    def _extract_entities_info(self, document, full_text: str) -> List[Dict]:
        """Extract recognized entities from Document AI response."""
        entities = []
        
        if not document.entities:
            return entities
        
        for entity in document.entities:
            # Extract entity text
            entity_text = (
                self._extract_text_from_layout(entity.text_anchor, full_text)
                if entity.text_anchor
                else entity.mention_text
            )
            
            entities.append({
                'type': entity.type_,
                'text': entity_text,
                'confidence': entity.confidence * 100 if entity.confidence else 0.0,
                'mention_text': entity.mention_text,
                'normalized_value': (
                    entity.normalized_value.text
                    if entity.normalized_value
                    else None
                )
            })
        
        return entities
    
    def _extract_text_from_layout(self, layout, full_text: str) -> str:
        """Extract text from layout using text anchors."""
        if not layout or not hasattr(layout, 'text_anchor'):
            return ""
        
        if not layout.text_anchor or not layout.text_anchor.text_segments:
            return ""
        
        text_parts = []
        for segment in layout.text_anchor.text_segments:
            start = segment.start_index if hasattr(segment, 'start_index') else 0
            end = segment.end_index if hasattr(segment, 'end_index') else len(full_text)
            text_parts.append(full_text[start:end])
        
        return "".join(text_parts).strip()


# Convenience function for easy import
def process_pdf_with_environment_config(pdf_path: str) -> DocumentAIResult:
    """
    Process PDF using environment-appropriate method.
    
    Automatically uses Document AI in production, basic OCR in development.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        DocumentAIResult with extraction metadata
        
    Example:
        >>> result = process_pdf_with_environment_config("document.pdf")
        >>> print(f"Method: {result.method}, Confidence: {result.confidence}%")
    """
    service = DocumentAIService()
    return service.process_pdf(pdf_path)
