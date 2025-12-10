"""
Quick test to verify pdfplumber migration works correctly
"""
import asyncio
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Create test PDF
def create_test_pdf():
    """Create a simple test PDF"""
    pdf_path = "test_pdfplumber_migration.pdf"
    c = canvas.Canvas(pdf_path, pagesize=letter)
    
    # Page 1
    c.drawString(100, 750, "Test Document for pdfplumber Migration")
    c.drawString(100, 730, "This PDF tests the migration from PyPDF2 to pdfplumber.")
    c.drawString(100, 710, "")
    c.drawString(100, 690, "Benefits of pdfplumber:")
    c.drawString(120, 670, "- Better table extraction")
    c.drawString(120, 650, "- Improved form handling")
    c.drawString(120, 630, "- More accurate text positioning")
    c.showPage()
    
    # Page 2
    c.drawString(100, 750, "Page 2 - Additional Content")
    c.drawString(100, 730, "pdfplumber provides enhanced PDF parsing capabilities.")
    c.showPage()
    
    c.save()
    return pdf_path

async def test_extraction():
    """Test PDF extraction with pdfplumber"""
    from ingestion.pdf_extractor import PDFExtractor
    
    print("\n" + "="*70)
    print("TESTING PDFPLUMBER MIGRATION")
    print("="*70 + "\n")
    
    # Create test PDF
    print("1. Creating test PDF...")
    pdf_path = create_test_pdf()
    print(f"   Created: {pdf_path}\n")
    
    # Test extraction
    print("2. Testing PDF extraction with pdfplumber...")
    extractor = PDFExtractor()
    result = extractor.extract(pdf_path)
    
    # Display results
    print(f"\n3. Extraction Results:")
    print(f"   - Success: {result['error'] is None}")
    print(f"   - Pages: {result['page_count']}")
    print(f"   - Content Hash: {result['content_hash'][:16]}...")
    print(f"   - Text Length: {len(result['text'])} characters")
    print(f"   - Metadata: {result['metadata']}\n")
    
    print("4. Sample extracted text (first 300 chars):")
    print("   " + "-" * 66)
    print(f"   {result['text'][:300]}...")
    print("   " + "-" * 66 + "\n")
    
    # Verify key content
    print("5. Verification:")
    checks = [
        ("Contains 'pdfplumber'", "pdfplumber" in result['text']),
        ("Contains 'PyPDF2'", "PyPDF2" in result['text']),
        ("Contains 'table extraction'", "table extraction" in result['text']),
        ("Page count == 2", result['page_count'] == 2),
        ("Has content hash", bool(result['content_hash'])),
        ("No errors", result['error'] is None)
    ]
    
    all_passed = True
    for check_name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {check_name}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*70)
    if all_passed:
        print("SUCCESS: pdfplumber migration is working correctly!")
    else:
        print("FAILURE: Some checks failed")
    print("="*70 + "\n")
    
    # Cleanup
    Path(pdf_path).unlink(missing_ok=True)
    print("Test PDF cleaned up.\n")

if __name__ == "__main__":
    asyncio.run(test_extraction())
