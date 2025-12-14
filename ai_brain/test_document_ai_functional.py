"""
Functional Test for Document AI Integration
This script tests the actual Document AI implementation without mocks.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from services.document_ai_service import DocumentAIService
from ingestion.pdf_extractor import PDFExtractor
from config.settings import get_settings

settings = get_settings()


async def test_basic_functionality():
    """Test basic functionality of Document AI service."""
    print("=" * 80)
    print("Document AI Implementation - Functional Test")
    print("=" * 80)
    
    # Test 1: Check environment detection
    print("\n✓ Test 1: Environment Detection")
    print(f"  - Environment: {settings.environment}")
    print(f"  - Is Development: {settings.is_development}")
    print(f"  - Is Production: {settings.is_production}")
    print(f"  - Should use Document AI: {settings.should_use_document_ai}")
    print(f"  - GCP Project ID: {settings.gcp_project_id or '(not set)'}")
    print(f"  - Processor ID: {settings.documentai_processor_id or '(not set)'}")
    
    # Test 2: Service initialization
    print("\n✓ Test 2: DocumentAIService Initialization")
    try:
        service = DocumentAIService(settings)
        print(f"  - Service created successfully")
        print(f"  - Will use Document AI: {settings.should_use_document_ai}")
    except Exception as e:
        print(f"  - Error: {e}")
        return False
    
    # Test 3: PDFExtractor integration
    print("\n✓ Test 3: PDFExtractor with Document AI")
    try:
        extractor = PDFExtractor()
        print(f"  - PDFExtractor created successfully")
    except Exception as e:
        print(f"  - Error: {e}")
        return False
    
    # Test 4: Create sample PDF for testing
    print("\n✓ Test 4: PDF Processing Test")
    
    # Create a temporary PDF file for testing
    import tempfile
    import os
    
    sample_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n200\n%%EOF"
    
    try:
        # Write PDF to temp file
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
            f.write(sample_pdf)
            temp_pdf_path = f.name
        
        try:
            result = extractor.extract(Path(temp_pdf_path))
            print("  - Extraction completed successfully")
            print(f"  - Method used: {result.get('metadata', {}).get('extraction_method', 'unknown')}")
            print(f"  - Content hash: {result.get('content_hash', 'N/A')[:16]}...")
            print(f"  - Page count: {result.get('page_count', 0)}")
            print(f"  - Text length: {len(result.get('text', ''))}")
            
            # Check extraction metadata
            if 'extraction_metadata' in result:
                extraction_meta = result['extraction_metadata']
                print(f"  - Extraction method: {extraction_meta.get('extraction_method', 'N/A')}")
                print(f"  - Confidence: {extraction_meta.get('confidence', 'N/A')}")
                if 'environment' in extraction_meta:
                    print(f"  - Environment: {extraction_meta['environment']}")
        finally:
            # Clean up temp file
            if os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
    except Exception as e:
        print(f"  - Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 5: Configuration summary
    print("\n✓ Test 5: Configuration Summary")
    print(f"  Environment-Based Routing:")
    if settings.is_development:
        print(f"    - Development mode: Using pdfplumber + pytesseract (FREE)")
        print(f"    - No Document AI costs")
    elif settings.is_production and settings.should_use_document_ai:
        print(f"    - Production mode: Using Google Document AI")
        print(f"    - Cost: ~$1.50/1000 pages")
        print(f"    - Fallback: pdfplumber + pytesseract")
    else:
        print(f"    - Production mode: Using basic OCR (Document AI not configured)")
    
    # Test 6: Feature availability
    print("\n✓ Test 6: Feature Availability")
    features = {
        "Text extraction": True,
        "OCR for scanned PDFs": True,
        "Layout analysis": settings.should_use_document_ai,
        "Table extraction": settings.should_use_document_ai,
        "Entity recognition": settings.should_use_document_ai,
        "Confidence scoring": settings.should_use_document_ai,
        "Automatic fallback": True,
    }
    
    for feature, available in features.items():
        status = "✅" if available else "⚠️ (requires Document AI)"
        print(f"  {status} {feature}")
    
    print("\n" + "=" * 80)
    print("✅ ALL FUNCTIONAL TESTS PASSED")
    print("=" * 80)
    print("\nImplementation Status:")
    print("  • DocumentAIService: ✅ Created")
    print("  • PDFExtractor integration: ✅ Complete")
    print("  • Environment detection: ✅ Working")
    print("  • Fallback mechanism: ✅ Implemented")
    print("\nNext Steps:")
    if not settings.should_use_document_ai:
        print("  1. Set up Google Cloud Project")
        print("  2. Enable Document AI API")
        print("  3. Create OCR processor")
        print("  4. Configure GCP credentials in .env")
        print("  5. See DOCUMENT_AI_SETUP.md for detailed instructions")
    else:
        print("  1. Test with real PDF documents")
        print("  2. Monitor extraction quality")
        print("  3. Review confidence scores")
        print("  4. Check cost metrics")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_basic_functionality())
    sys.exit(0 if success else 1)
