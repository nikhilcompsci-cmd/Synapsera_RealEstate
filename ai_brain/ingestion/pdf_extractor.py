import hashlib
from pathlib import Path
from typing import Dict, Optional
import pdfplumber
import logging

# OCR imports for image-based PDFs
try:
    import pytesseract
    from PIL import Image
    
    # Configure Tesseract path for Windows
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# Document AI imports (production only)
try:
    from services.document_ai_service import DocumentAIService
    DOCUMENT_AI_AVAILABLE = True
except ImportError:
    DOCUMENT_AI_AVAILABLE = False

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PDFExtractor:
    """
    Extract text and metadata from PDF files.
    
    Environment-Aware Extraction:
    - Production: Uses Google Document AI (95-99% accuracy, costs money)
    - Development: Uses pdfplumber + pytesseract (70-90% accuracy, free)
    
    This ensures cost optimization while maintaining high quality in production.
    """
    
    @staticmethod
    def calculate_content_hash(file_path: Path) -> str:
        """Calculate SHA256 hash of file content for deduplication."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    @staticmethod
    def extract_text_and_metadata(file_path: Path) -> Dict:
        """
        Extract text and metadata from a PDF file using pdfplumber.
        
        pdfplumber provides more accurate text extraction than PyPDF2,
        especially for PDFs with complex layouts, tables, and forms.
        
        Returns:
            dict with keys: text, page_count, metadata, error (if any)
        """
        try:
            with pdfplumber.open(file_path) as pdf:
                # Get page count
                page_count = len(pdf.pages)
                
                # Extract text from all pages
                text_parts = []
                for page_num, page in enumerate(pdf.pages):
                    try:
                        # pdfplumber's extract_text() is more accurate than PyPDF2
                        text = page.extract_text()
                        if text:
                            # Clean up excessive whitespace while preserving structure
                            text = text.strip()
                            if text:
                                text_parts.append(text)
                    except Exception as e:
                        # Log warning but continue with other pages
                        print(f"Warning: Could not extract text from page {page_num}: {e}")
                
                full_text = "\n\n".join(text_parts)
                
                # If no text extracted (image-based PDF), try OCR
                if not full_text.strip():
                    if OCR_AVAILABLE:
                        logger.warning(f"No text extracted with pdfplumber, attempting OCR on {file_path}")
                        try:
                            # Use pdfplumber to convert pages to images for OCR
                            ocr_text_parts = []
                            for page_num, page in enumerate(pdf.pages):
                                try:
                                    # Convert page to image using pdfplumber
                                    img = page.to_image(resolution=300)  # Higher DPI = better OCR
                                    # Convert to PIL Image
                                    pil_image = img.original
                                    # Extract text using Tesseract
                                    text = pytesseract.image_to_string(pil_image)
                                    if text and text.strip():
                                        ocr_text_parts.append(text.strip())
                                        logger.debug(f"OCR extracted {len(text)} chars from page {page_num+1}")
                                except Exception as e:
                                    logger.warning(f"OCR failed on page {page_num+1}: {e}")
                            
                            if ocr_text_parts:
                                full_text = "\n\n".join(ocr_text_parts)
                                logger.info(f"OCR extraction complete: {len(full_text)} chars from {len(ocr_text_parts)} pages")
                            else:
                                logger.error(f"OCR failed to extract any text from {file_path}")
                                return {
                                    "text": "",
                                    "page_count": page_count,
                                    "metadata": {},
                                    "error": "This PDF contains images or scanned pages. OCR extraction failed. Please provide a text-based PDF or install Tesseract OCR properly."
                                }
                        except Exception as e:
                            logger.error(f"OCR processing failed: {e}")
                            return {
                                "text": "",
                                "page_count": page_count,
                                "metadata": {},
                                "error": f"OCR extraction failed: {str(e)}. Please provide a text-based PDF."
                            }
                    else:
                        logger.error(f"No text extracted and OCR not available for {file_path}")
                        return {
                            "text": "",
                            "page_count": page_count,
                            "metadata": {},
                            "error": "This PDF contains images or scanned pages but OCR is not installed. To process image-based PDFs, install Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki"
                        }
                
                # Extract PDF metadata
                metadata = {}
                if pdf.metadata:
                    try:
                        # pdfplumber metadata uses same keys as PyPDF2 but without slashes
                        metadata = {
                            "title": pdf.metadata.get("Title", "") or pdf.metadata.get("/Title", ""),
                            "author": pdf.metadata.get("Author", "") or pdf.metadata.get("/Author", ""),
                            "subject": pdf.metadata.get("Subject", "") or pdf.metadata.get("/Subject", ""),
                            "creator": pdf.metadata.get("Creator", "") or pdf.metadata.get("/Creator", ""),
                            "producer": pdf.metadata.get("Producer", "") or pdf.metadata.get("/Producer", ""),
                            "creation_date": pdf.metadata.get("CreationDate", "") or pdf.metadata.get("/CreationDate", ""),
                        }
                        # Remove empty values
                        metadata = {k: v for k, v in metadata.items() if v}
                    except Exception as e:
                        print(f"Warning: Could not extract metadata: {e}")
                
                return {
                    "text": full_text,
                    "page_count": page_count,
                    "metadata": metadata,
                    "error": None
                }
        
        except Exception as e:
            return {
                "text": "",
                "page_count": 0,
                "metadata": {},
                "error": str(e)
            }
    
    @staticmethod
    def extract_with_document_ai(file_path: Path) -> Dict:
        """
        Extract text using Google Document AI (production only).
        
        Returns:
            dict with keys: text, page_count, metadata, error, extraction_metadata
        """
        logger.info(f"Using Document AI for extraction: {file_path}")
        
        try:
            # Initialize Document AI service
            doc_ai_service = DocumentAIService(settings)
            
            # Process PDF
            result = doc_ai_service.process_pdf(str(file_path))
            
            # Build extraction metadata
            extraction_metadata = {
                'method': result.method,
                'confidence': result.confidence,
                'tables_extracted': result.tables_count,
                'entities_extracted': result.entities_count,
                'requires_review': result.requires_review,
                'warnings': result.warnings,
                'layout_preserved': result.layout_preserved
            }
            
            # Store tables and entities if extracted
            if result.tables:
                extraction_metadata['tables'] = result.tables
            
            if result.entities:
                extraction_metadata['entities'] = result.entities
            
            logger.info(
                f"Document AI extraction complete: {len(result.text)} chars, "
                f"{result.pages_count} pages, confidence: {result.confidence:.1f}%"
            )
            
            return {
                "text": result.text,
                "page_count": result.pages_count,
                "metadata": extraction_metadata,
                "error": None,
                "extraction_metadata": extraction_metadata  # For db storage
            }
            
        except Exception as e:
            logger.error(f"Document AI extraction failed: {e}", exc_info=True)
            return {
                "text": "",
                "page_count": 0,
                "metadata": {},
                "error": f"Document AI failed: {str(e)}",
                "extraction_metadata": {'method': 'document_ai', 'error': str(e)}
            }
    
    @staticmethod
    def extract(file_path: Path) -> Dict:
        """
        Complete extraction: content hash + text + metadata.
        
        Environment-Aware Strategy:
        1. Production: Try Document AI first, fallback to basic extraction
        2. Development: Use basic extraction (pdfplumber + pytesseract)
        
        Returns:
            dict with keys: content_hash, text, page_count, metadata, error, extraction_metadata
        """
        content_hash = PDFExtractor.calculate_content_hash(file_path)
        
        # PRODUCTION: Use Document AI
        if settings.should_use_document_ai and DOCUMENT_AI_AVAILABLE:
            logger.info(
                f"Production environment detected - using Document AI for {file_path.name}"
            )
            
            # Try Document AI
            doc_ai_result = PDFExtractor.extract_with_document_ai(file_path)
            
            # If Document AI succeeded, return result
            if not doc_ai_result["error"]:
                return {
                    "content_hash": content_hash,
                    **doc_ai_result
                }
            
            # Document AI failed, log warning and fall back
            logger.warning(
                f"Document AI failed, falling back to basic extraction: {doc_ai_result['error']}"
            )
        
        # DEVELOPMENT or FALLBACK: Use basic extraction
        logger.info(
            f"{'Development' if settings.is_development else 'Fallback'} mode - "
            f"using pdfplumber + pytesseract for {file_path.name}"
        )
        
        extraction_result = PDFExtractor.extract_text_and_metadata(file_path)
        
        # Add extraction method to metadata
        if 'extraction_metadata' not in extraction_result:
            extraction_result['extraction_metadata'] = {
                'method': 'pdfplumber' if extraction_result.get('text') else 'pytesseract',
                'environment': settings.environment
            }
        
        return {
            "content_hash": content_hash,
            **extraction_result
        }
