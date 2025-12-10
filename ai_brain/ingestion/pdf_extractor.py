import hashlib
from pathlib import Path
from typing import Dict, Optional
import pdfplumber


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
