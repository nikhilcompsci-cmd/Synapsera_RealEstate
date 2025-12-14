"""
Document Quality Validation Service

Validates document quality before processing to:
- Detect corrupted/invalid files
- Check file size limits
- Validate MIME types with magic bytes
- Detect password-protected PDFs
- Check for empty/blank pages
- Verify PDF structure integrity
- Estimate processing complexity
"""
import hashlib
import mimetypes
import PyPDF2
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import structlog

logger = structlog.get_logger()

# Initialize mimetypes
mimetypes.init()


class ValidationSeverity(Enum):
    """Validation issue severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationCode(Enum):
    """Validation issue codes."""
    # File-level issues
    FILE_TOO_LARGE = "file_too_large"
    FILE_TOO_SMALL = "file_too_small"
    FILE_CORRUPTED = "file_corrupted"
    INVALID_MIME_TYPE = "invalid_mime_type"
    MIME_MISMATCH = "mime_mismatch"
    
    # PDF-specific issues
    PDF_ENCRYPTED = "pdf_encrypted"
    PDF_DAMAGED = "pdf_damaged"
    PDF_NO_PAGES = "pdf_no_pages"
    PDF_TOO_MANY_PAGES = "pdf_too_many_pages"
    PDF_MOSTLY_BLANK = "pdf_mostly_blank"
    PDF_LOW_QUALITY = "pdf_low_quality"
    PDF_UNSUPPORTED_VERSION = "pdf_unsupported_version"
    
    # Content issues
    NO_EXTRACTABLE_TEXT = "no_extractable_text"
    SUSPICIOUS_CONTENT = "suspicious_content"
    MIXED_LANGUAGES = "mixed_languages"
    
    # Processing warnings
    HIGH_COMPLEXITY = "high_complexity"
    REQUIRES_OCR = "requires_ocr"
    SLOW_PROCESSING_EXPECTED = "slow_processing_expected"


@dataclass
class ValidationIssue:
    """Represents a validation issue found in a document."""
    code: ValidationCode
    severity: ValidationSeverity
    message: str
    details: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            "code": self.code.value,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details or {}
        }


@dataclass
class ValidationResult:
    """Result of document validation."""
    is_valid: bool
    can_process: bool
    issues: List[ValidationIssue]
    metadata: Dict
    quality_score: float  # 0.0 to 1.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            "is_valid": self.is_valid,
            "can_process": self.can_process,
            "issues": [issue.to_dict() for issue in self.issues],
            "metadata": self.metadata,
            "quality_score": self.quality_score
        }
    
    @property
    def has_critical_issues(self) -> bool:
        """Check if there are any critical issues."""
        return any(issue.severity == ValidationSeverity.CRITICAL for issue in self.issues)
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)
    
    @property
    def warnings(self) -> List[ValidationIssue]:
        """Get all warnings."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]
    
    @property
    def errors(self) -> List[ValidationIssue]:
        """Get all errors."""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]


class DocumentValidator:
    """Validates document quality before processing."""
    
    # Configuration
    MIN_FILE_SIZE = 100  # bytes
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
    MAX_PAGES = 1000
    MIN_TEXT_LENGTH = 10  # characters per page
    BLANK_PAGE_THRESHOLD = 50  # characters
    MAX_BLANK_PAGES_RATIO = 0.5  # 50% of pages
    
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'application/x-pdf',
    }
    
    PDF_MAGIC_BYTES = b'%PDF-'
    
    def __init__(self):
        """Initialize validator."""
        pass
    
    def validate(self, file_path: Path) -> ValidationResult:
        """
        Validate document quality.
        
        Args:
            file_path: Path to document file
            
        Returns:
            ValidationResult with validation status and issues
        """
        logger.info("document_validation_started", file_path=str(file_path))
        
        issues: List[ValidationIssue] = []
        metadata: Dict = {}
        
        try:
            # 1. Basic file validation
            file_issues, file_meta = self._validate_file(file_path)
            issues.extend(file_issues)
            metadata.update(file_meta)
            
            # Stop if critical file issues
            if any(i.severity == ValidationSeverity.CRITICAL for i in file_issues):
                return self._build_result(issues, metadata)
            
            # 2. MIME type validation
            mime_issues, mime_meta = self._validate_mime_type(file_path)
            issues.extend(mime_issues)
            metadata.update(mime_meta)
            
            # 3. PDF-specific validation
            if metadata.get('mime_type', '').startswith('application/pdf'):
                pdf_issues, pdf_meta = self._validate_pdf(file_path)
                issues.extend(pdf_issues)
                metadata.update(pdf_meta)
                
                # 4. Content validation
                if not any(i.code == ValidationCode.PDF_ENCRYPTED for i in pdf_issues):
                    content_issues, content_meta = self._validate_content(file_path)
                    issues.extend(content_issues)
                    metadata.update(content_meta)
            
            # Build final result
            result = self._build_result(issues, metadata)
            
            logger.info(
                "document_validation_completed",
                file_path=str(file_path),
                is_valid=result.is_valid,
                can_process=result.can_process,
                quality_score=result.quality_score,
                issues_count=len(issues)
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "document_validation_failed",
                file_path=str(file_path),
                error=str(e),
                exc_info=True
            )
            issues.append(ValidationIssue(
                code=ValidationCode.FILE_CORRUPTED,
                severity=ValidationSeverity.CRITICAL,
                message=f"Validation failed: {str(e)}",
                details={"exception": str(e)}
            ))
            return self._build_result(issues, metadata)
    
    def _validate_file(self, file_path: Path) -> Tuple[List[ValidationIssue], Dict]:
        """Validate basic file properties."""
        issues = []
        metadata = {}
        
        try:
            # Check file exists
            if not file_path.exists():
                issues.append(ValidationIssue(
                    code=ValidationCode.FILE_CORRUPTED,
                    severity=ValidationSeverity.CRITICAL,
                    message="File does not exist"
                ))
                return issues, metadata
            
            # Check file size
            file_size = file_path.stat().st_size
            metadata['file_size'] = file_size
            
            if file_size < self.MIN_FILE_SIZE:
                issues.append(ValidationIssue(
                    code=ValidationCode.FILE_TOO_SMALL,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"File too small: {file_size} bytes (minimum {self.MIN_FILE_SIZE})",
                    details={"file_size": file_size, "min_size": self.MIN_FILE_SIZE}
                ))
            elif file_size > self.MAX_FILE_SIZE:
                issues.append(ValidationIssue(
                    code=ValidationCode.FILE_TOO_LARGE,
                    severity=ValidationSeverity.ERROR,
                    message=f"File too large: {file_size / (1024*1024):.1f} MB (maximum {self.MAX_FILE_SIZE / (1024*1024):.0f} MB)",
                    details={"file_size": file_size, "max_size": self.MAX_FILE_SIZE}
                ))
            
            # Calculate file hash
            metadata['file_hash'] = self._calculate_hash(file_path)
            
        except Exception as e:
            issues.append(ValidationIssue(
                code=ValidationCode.FILE_CORRUPTED,
                severity=ValidationSeverity.CRITICAL,
                message=f"Cannot read file: {str(e)}"
            ))
        
        return issues, metadata
    
    def _validate_mime_type(self, file_path: Path) -> Tuple[List[ValidationIssue], Dict]:
        """Validate MIME type using magic bytes."""
        issues = []
        metadata = {}
        
        try:
            # Check magic bytes first
            with open(file_path, 'rb') as f:
                magic_bytes = f.read(5)
                metadata['magic_bytes'] = magic_bytes.hex()
                
                if magic_bytes != self.PDF_MAGIC_BYTES:
                    issues.append(ValidationIssue(
                        code=ValidationCode.MIME_MISMATCH,
                        severity=ValidationSeverity.CRITICAL,
                        message="File is not a valid PDF (magic bytes mismatch)",
                        details={"magic_bytes": magic_bytes.hex(), "expected": self.PDF_MAGIC_BYTES.hex()}
                    ))
                    metadata['mime_type'] = 'unknown'
                    return issues, metadata
            
            # Use mimetypes library as fallback
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if not mime_type:
                mime_type = 'application/pdf'  # Assume PDF if magic bytes match
            
            metadata['mime_type'] = mime_type
            
            # Check if allowed
            if mime_type not in self.ALLOWED_MIME_TYPES and not mime_type.endswith('/pdf'):
                issues.append(ValidationIssue(
                    code=ValidationCode.INVALID_MIME_TYPE,
                    severity=ValidationSeverity.WARNING,
                    message=f"Unexpected MIME type: {mime_type} (but magic bytes indicate PDF)",
                    details={"detected_mime": mime_type, "allowed_types": list(self.ALLOWED_MIME_TYPES)}
                ))
        
        except Exception as e:
            issues.append(ValidationIssue(
                code=ValidationCode.FILE_CORRUPTED,
                severity=ValidationSeverity.CRITICAL,
                message=f"Cannot detect file type: {str(e)}"
            ))
        
        return issues, metadata
    
    def _validate_pdf(self, file_path: Path) -> Tuple[List[ValidationIssue], Dict]:
        """Validate PDF-specific properties."""
        issues = []
        metadata = {}
        
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                
                # Check encryption
                if reader.is_encrypted:
                    issues.append(ValidationIssue(
                        code=ValidationCode.PDF_ENCRYPTED,
                        severity=ValidationSeverity.CRITICAL,
                        message="PDF is password-protected",
                        details={"encrypted": True}
                    ))
                    metadata['encrypted'] = True
                    return issues, metadata
                
                metadata['encrypted'] = False
                
                # Check page count
                page_count = len(reader.pages)
                metadata['page_count'] = page_count
                
                if page_count == 0:
                    issues.append(ValidationIssue(
                        code=ValidationCode.PDF_NO_PAGES,
                        severity=ValidationSeverity.CRITICAL,
                        message="PDF has no pages"
                    ))
                elif page_count > self.MAX_PAGES:
                    issues.append(ValidationIssue(
                        code=ValidationCode.PDF_TOO_MANY_PAGES,
                        severity=ValidationSeverity.ERROR,
                        message=f"PDF has too many pages: {page_count} (maximum {self.MAX_PAGES})",
                        details={"page_count": page_count, "max_pages": self.MAX_PAGES}
                    ))
                
                # Extract metadata
                pdf_info = reader.metadata
                if pdf_info:
                    metadata['pdf_metadata'] = {
                        'title': pdf_info.get('/Title', ''),
                        'author': pdf_info.get('/Author', ''),
                        'creator': pdf_info.get('/Creator', ''),
                        'producer': pdf_info.get('/Producer', ''),
                    }
                
                # Check PDF version
                if hasattr(reader, 'pdf_header'):
                    metadata['pdf_version'] = reader.pdf_header
                
                # Estimate complexity
                complexity_score = self._estimate_complexity(reader)
                metadata['complexity_score'] = complexity_score
                
                if complexity_score > 0.8:
                    issues.append(ValidationIssue(
                        code=ValidationCode.HIGH_COMPLEXITY,
                        severity=ValidationSeverity.WARNING,
                        message="Document is complex, may take longer to process",
                        details={"complexity_score": complexity_score}
                    ))
                
        except PyPDF2.errors.PdfReadError as e:
            issues.append(ValidationIssue(
                code=ValidationCode.PDF_DAMAGED,
                severity=ValidationSeverity.CRITICAL,
                message=f"PDF is damaged or corrupted: {str(e)}",
                details={"error": str(e)}
            ))
        except Exception as e:
            issues.append(ValidationIssue(
                code=ValidationCode.FILE_CORRUPTED,
                severity=ValidationSeverity.CRITICAL,
                message=f"Cannot read PDF: {str(e)}",
                details={"error": str(e)}
            ))
        
        return issues, metadata
    
    def _validate_content(self, file_path: Path) -> Tuple[List[ValidationIssue], Dict]:
        """Validate document content quality."""
        issues = []
        metadata = {}
        
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                
                # Sample pages for content analysis
                page_count = len(reader.pages)
                sample_size = min(10, page_count)  # Check first 10 pages
                
                blank_pages = 0
                total_text_length = 0
                requires_ocr = False
                
                for i in range(sample_size):
                    try:
                        page = reader.pages[i]
                        text = page.extract_text() or ""
                        text_length = len(text.strip())
                        total_text_length += text_length
                        
                        if text_length < self.BLANK_PAGE_THRESHOLD:
                            blank_pages += 1
                            
                        # Check if OCR might be needed
                        if text_length < self.MIN_TEXT_LENGTH and i < 3:
                            requires_ocr = True
                            
                    except Exception as e:
                        logger.warning("page_extraction_failed", page=i, error=str(e))
                        blank_pages += 1
                
                # Calculate metrics
                avg_text_per_page = total_text_length / sample_size if sample_size > 0 else 0
                blank_ratio = blank_pages / sample_size if sample_size > 0 else 0
                
                metadata['avg_text_per_page'] = avg_text_per_page
                metadata['blank_pages_ratio'] = blank_ratio
                metadata['requires_ocr'] = requires_ocr
                
                # Check for mostly blank document
                if blank_ratio > self.MAX_BLANK_PAGES_RATIO:
                    issues.append(ValidationIssue(
                        code=ValidationCode.PDF_MOSTLY_BLANK,
                        severity=ValidationSeverity.WARNING,
                        message=f"Document has {blank_ratio*100:.0f}% blank pages",
                        details={"blank_ratio": blank_ratio, "blank_pages": blank_pages}
                    ))
                
                # Check if no extractable text
                if total_text_length == 0:
                    issues.append(ValidationIssue(
                        code=ValidationCode.NO_EXTRACTABLE_TEXT,
                        severity=ValidationSeverity.WARNING,
                        message="No text extracted, document may be scanned images",
                        details={"requires_ocr": True}
                    ))
                    metadata['requires_ocr'] = True
                elif requires_ocr:
                    issues.append(ValidationIssue(
                        code=ValidationCode.REQUIRES_OCR,
                        severity=ValidationSeverity.INFO,
                        message="Document appears to contain scanned images, OCR will be used"
                    ))
                
        except Exception as e:
            logger.error("content_validation_failed", error=str(e))
        
        return issues, metadata
    
    def _estimate_complexity(self, reader: PyPDF2.PdfReader) -> float:
        """
        Estimate document processing complexity (0.0 to 1.0).
        
        Factors:
        - Page count
        - File size
        - Number of images
        - Form fields
        """
        try:
            page_count = len(reader.pages)
            
            # Base score from page count
            page_score = min(page_count / self.MAX_PAGES, 1.0)
            
            # Sample first few pages for complexity
            sample_pages = min(5, page_count)
            has_images = False
            has_forms = False
            
            for i in range(sample_pages):
                page = reader.pages[i]
                
                # Check for images
                if '/XObject' in page['/Resources']:
                    xobject = page['/Resources']['/XObject'].get_object()
                    for obj in xobject:
                        if xobject[obj]['/Subtype'] == '/Image':
                            has_images = True
                            break
                
                # Check for form fields
                if '/AcroForm' in reader.trailer['/Root']:
                    has_forms = True
            
            # Calculate complexity score
            complexity = page_score * 0.5
            if has_images:
                complexity += 0.3
            if has_forms:
                complexity += 0.2
            
            return min(complexity, 1.0)
            
        except Exception:
            return 0.5  # Default moderate complexity
    
    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _build_result(self, issues: List[ValidationIssue], metadata: Dict) -> ValidationResult:
        """Build final validation result."""
        # Determine if document is valid
        has_critical = any(i.severity == ValidationSeverity.CRITICAL for i in issues)
        has_error = any(i.severity == ValidationSeverity.ERROR for i in issues)
        
        is_valid = not has_critical
        can_process = not has_critical and not has_error
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(issues, metadata)
        
        return ValidationResult(
            is_valid=is_valid,
            can_process=can_process,
            issues=issues,
            metadata=metadata,
            quality_score=quality_score
        )
    
    def _calculate_quality_score(self, issues: List[ValidationIssue], metadata: Dict) -> float:
        """
        Calculate document quality score (0.0 to 1.0).
        
        Higher score = better quality
        """
        score = 1.0
        
        # Deduct for issues
        for issue in issues:
            if issue.severity == ValidationSeverity.CRITICAL:
                score -= 0.5
            elif issue.severity == ValidationSeverity.ERROR:
                score -= 0.2
            elif issue.severity == ValidationSeverity.WARNING:
                score -= 0.1
        
        # Adjust for content quality
        if 'avg_text_per_page' in metadata:
            avg_text = metadata['avg_text_per_page']
            if avg_text < 100:
                score -= 0.2
            elif avg_text < 500:
                score -= 0.1
        
        if 'blank_pages_ratio' in metadata:
            blank_ratio = metadata['blank_pages_ratio']
            score -= (blank_ratio * 0.3)
        
        return max(0.0, min(1.0, score))
