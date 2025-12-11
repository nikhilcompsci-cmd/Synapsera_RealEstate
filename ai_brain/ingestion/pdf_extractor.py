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

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extract text and metadata from PDF files using pdfplumber."""
    
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
                if not full_text.strip() and OCR_AVAILABLE:
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
                        
                        full_text = "\n\n".join(ocr_text_parts)
                        logger.info(f"OCR extraction complete: {len(full_text)} chars from {len(ocr_text_parts)} pages")
                    except Exception as e:
                        logger.error(f"OCR processing failed: {e}")
                elif not full_text.strip() and not OCR_AVAILABLE:
                    logger.error("No text extracted and OCR not available. Install pytesseract and pdf2image for image-based PDFs.")
                
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
    def extract(file_path: Path) -> Dict:
        """
        Complete extraction: content hash + text + metadata.
        
        Returns:
            dict with keys: content_hash, text, page_count, metadata, error
        """
        content_hash = PDFExtractor.calculate_content_hash(file_path)
        extraction_result = PDFExtractor.extract_text_and_metadata(file_path)
        
        return {
            "content_hash": content_hash,
            **extraction_result
        }
