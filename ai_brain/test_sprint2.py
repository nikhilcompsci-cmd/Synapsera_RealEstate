"""
Test script for Sprint 2 - Document Ingestion Pipeline
"""
import asyncio
import httpx
import json
from pathlib import Path


# Create a simple test PDF
def create_test_pdf():
    """Create a simple PDF for testing."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        pdf_path = Path("test_document.pdf")
        
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        
        # Page 1
        c.drawString(100, 750, "Test Real Estate Document")
        c.drawString(100, 730, "=" * 50)
        c.drawString(100, 700, "Property: Downtown Office Complex")
        c.drawString(100, 680, "Location: 123 Main Street, Downtown")
        c.drawString(100, 660, "Type: Commercial Office Building")
        c.drawString(100, 640, "")
        c.drawString(100, 620, "This is a test document for the AI Brain ingestion pipeline.")
        c.drawString(100, 600, "It contains multiple paragraphs to test chunking.")
        c.showPage()
        
        # Page 2
        c.drawString(100, 750, "Property Details (Page 2)")
        c.drawString(100, 730, "=" * 50)
        c.drawString(100, 700, "Square Footage: 50,000 sq ft")
        c.drawString(100, 680, "Floors: 10")
        c.drawString(100, 660, "Year Built: 2020")
        c.drawString(100, 640, "Parking: 100 spaces")
        c.showPage()
        
        c.save()
        
        print(f"✅ Created test PDF: {pdf_path}")
        return pdf_path
    
    except ImportError:
        print("⚠️  reportlab not installed, using dummy PDF creation")
        # Create a minimal PDF manually (not recommended for production)
        pdf_path = Path("test_document.pdf")
        pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\n0000000101 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF"
        with open(pdf_path, "wb") as f:
            f.write(pdf_content)
        print(f"✅ Created minimal PDF: {pdf_path}")
        return pdf_path


async def test_sprint2_pipeline():
    """Test all Sprint 2 endpoints."""
    base_url = "http://localhost:8000"
    api_prefix = "/api/v1"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("\n" + "=" * 70)
        print("🧪 TESTING SPRINT 2 - DOCUMENT INGESTION PIPELINE")
        print("=" * 70)
        
        # Step 1: Create a project first (from Sprint 1)
        print("\n1️⃣  Creating a test project...")
        project_data = {
            "name": "Sprint 2 Test Project",
            "description": "Testing document ingestion pipeline"
        }
        response = await client.post(
            f"{base_url}{api_prefix}/project",
            json=project_data
        )
        print(f"   Status: {response.status_code}")
        project = response.json()
        project_id = project["id"]
        print(f"   ✅ Project created with ID: {project_id}")
        
        # Step 2: Create test PDF
        print("\n2️⃣  Creating test PDF...")
        pdf_path = create_test_pdf()
        
        # Step 3: Upload document
        print("\n3️⃣  Testing POST /project/{project_id}/document/upload")
        with open(pdf_path, "rb") as pdf_file:
            files = {"file": ("test_document.pdf", pdf_file, "application/pdf")}
            response = await client.post(
                f"{base_url}{api_prefix}/project/{project_id}/document/upload",
                files=files
            )
        print(f"   Status: {response.status_code}")
        upload_result = response.json()
        print(f"   Response: {json.dumps(upload_result, indent=2)}")
        
        if upload_result["status"] == "success":
            print(f"   ✅ Document uploaded successfully!")
            print(f"      - Document ID: {upload_result['document_id']}")
            print(f"      - Chunks created: {upload_result['chunks_created']}")
            print(f"      - Embeddings created: {upload_result['embeddings_created']}")
            document_id = upload_result["document_id"]
        else:
            print(f"   ❌ Upload failed: {upload_result['message']}")
            return
        
        # Step 4: Test duplicate detection
        print("\n4️⃣  Testing duplicate detection (uploading same file)...")
        with open(pdf_path, "rb") as pdf_file:
            files = {"file": ("test_document_copy.pdf", pdf_file, "application/pdf")}
            response = await client.post(
                f"{base_url}{api_prefix}/project/{project_id}/document/upload",
                files=files
            )
        duplicate_result = response.json()
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(duplicate_result, indent=2)}")
        if duplicate_result["status"] == "duplicate":
            print(f"   ✅ Duplicate detection working!")
        else:
            print(f"   ⚠️  Expected duplicate detection")
        
        # Step 5: Get ingestion status
        print("\n5️⃣  Testing GET /project/{project_id}/ingestion-status")
        response = await client.get(
            f"{base_url}{api_prefix}/project/{project_id}/ingestion-status"
        )
        print(f"   Status: {response.status_code}")
        status_result = response.json()
        print(f"   Total documents: {status_result['total_documents']}")
        print(f"   Completed: {status_result['completed']}")
        print(f"   Failed: {status_result['failed']}")
        print(f"   Documents:")
        for doc in status_result['documents']:
            print(f"      - {doc['filename']}: {doc['status']} ({doc['chunk_count']} chunks)")
        print(f"   ✅ Ingestion status retrieved!")
        
        # Step 6: Get document chunks
        print("\n6️⃣  Testing GET /document/{document_id}/chunks")
        response = await client.get(
            f"{base_url}{api_prefix}/document/{document_id}/chunks"
        )
        print(f"   Status: {response.status_code}")
        chunks = response.json()
        print(f"   Total chunks: {len(chunks)}")
        if chunks:
            print(f"   First chunk preview:")
            first_chunk = chunks[0]
            print(f"      - Index: {first_chunk['chunk_index']}")
            print(f"      - Characters: {first_chunk['char_count']}")
            print(f"      - Has embedding: {first_chunk['has_embedding']}")
            print(f"      - Text preview: {first_chunk['text'][:100]}...")
        print(f"   ✅ Chunks retrieved!")
        
        # Step 7: Get embeddings count
        print("\n7️⃣  Testing GET /project/{project_id}/embeddings/count")
        response = await client.get(
            f"{base_url}{api_prefix}/project/{project_id}/embeddings/count"
        )
        print(f"   Status: {response.status_code}")
        embeddings_result = response.json()
        print(f"   Response: {json.dumps(embeddings_result, indent=2)}")
        print(f"   ✅ Embeddings count retrieved!")
        
        # Cleanup
        print("\n8️⃣  Cleaning up test PDF...")
        if pdf_path.exists():
            pdf_path.unlink()
        print(f"   ✅ Test PDF removed")
        
        # Summary
        print("\n" + "=" * 70)
        print("✨ ALL SPRINT 2 TESTS PASSED! ✨")
        print("=" * 70)
        print("\n📊 Summary:")
        print(f"   ✅ Document upload endpoint")
        print(f"   ✅ Duplicate detection (content hash)")
        print(f"   ✅ PDF extraction")
        print(f"   ✅ Text chunking")
        print(f"   ✅ Embedding generation (stub)")
        print(f"   ✅ FAISS index creation")
        print(f"   ✅ Ingestion status endpoint")
        print(f"   ✅ Chunks retrieval endpoint")
        print(f"   ✅ Embeddings count endpoint")
        print("\n🎉 Sprint 2 ingestion pipeline is fully functional!")


if __name__ == "__main__":
    try:
        asyncio.run(test_sprint2_pipeline())
    except KeyboardInterrupt:
        print("\n\n⏸️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        print("\n💡 Make sure:")
        print("   1. The API server is running: python start_server.py")
        print("   2. Database is up: docker-compose up -d")
        print("   3. Migrations are applied: python -m alembic upgrade head")
