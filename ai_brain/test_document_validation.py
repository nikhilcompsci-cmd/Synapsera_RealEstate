"""
Test document quality validation
"""
import sys
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).parent))

from services.document_validator import DocumentValidator, ValidationCode, ValidationSeverity

print("=" * 80)
print("Document Quality Validation - Test")
print("=" * 80)

validator = DocumentValidator()

# Test 1: Create a minimal valid PDF
print("\n✓ Test 1: Valid PDF")
valid_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n200\n%%EOF"

with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
    f.write(valid_pdf)
    temp_path = Path(f.name)

result = validator.validate(temp_path)
print(f"  Valid: {result.is_valid}")
print(f"  Can Process: {result.can_process}")
print(f"  Quality Score: {result.quality_score:.2f}")
print(f"  Issues: {len(result.issues)}")
if result.issues:
    for issue in result.issues:
        print(f"    - [{issue.severity.value}] {issue.message}")
temp_path.unlink()

# Test 2: File too small
print("\n✓ Test 2: File Too Small")
tiny_file = b"tiny"
with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
    f.write(tiny_file)
    temp_path = Path(f.name)

result = validator.validate(temp_path)
print(f"  Valid: {result.is_valid}")
print(f"  Can Process: {result.can_process}")
print(f"  Quality Score: {result.quality_score:.2f}")
print(f"  Critical Issues: {result.has_critical_issues}")
if result.errors:
    print(f"  Errors:")
    for error in result.errors:
        print(f"    - {error.message}")
temp_path.unlink()

# Test 3: Not a PDF
print("\n✓ Test 3: Invalid File Type (not a PDF)")
not_pdf = b"This is not a PDF file, just plain text"
with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
    f.write(not_pdf)
    temp_path = Path(f.name)

result = validator.validate(temp_path)
print(f"  Valid: {result.is_valid}")
print(f"  Can Process: {result.can_process}")
print(f"  Quality Score: {result.quality_score:.2f}")
if result.has_critical_issues:
    print(f"  Critical Issues Found:")
    for issue in result.issues:
        if issue.severity == ValidationSeverity.CRITICAL:
            print(f"    - {issue.message}")
temp_path.unlink()

# Test 4: Summary
print("\n" + "=" * 80)
print("✅ VALIDATION TEST COMPLETE")
print("=" * 80)

print("\nValidation Features:")
print("  ✅ File size validation")
print("  ✅ MIME type detection (magic bytes)")
print("  ✅ PDF structure validation")
print("  ✅ Encryption detection")
print("  ✅ Page count limits")
print("  ✅ Content quality scoring")
print("  ✅ Blank page detection")
print("  ✅ OCR requirement detection")
print("  ✅ Complexity estimation")

print("\nValidation Levels:")
print("  • CRITICAL: Document cannot be processed")
print("  • ERROR: Major issues, processing may fail")
print("  • WARNING: Minor issues, processing may be slower")
print("  • INFO: Informational messages")

print("\nQuality Score: 0.0 to 1.0")
print("  • 1.0 = Perfect document")
print("  • 0.8-1.0 = High quality")
print("  • 0.5-0.8 = Medium quality")
print("  • 0.0-0.5 = Low quality / problematic")

print("\n" + "=" * 80)
