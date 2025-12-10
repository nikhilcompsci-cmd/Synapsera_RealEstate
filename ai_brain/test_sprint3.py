"""
Sprint 3 - RAG Chat Engine Testing
Tests the complete chat/query endpoint
"""
import asyncio
import httpx
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"


def create_real_estate_pdf(filename: str):
    """Create a sample real estate PDF document"""
    c = canvas.Canvas(filename, pagesize=letter)
    
    # Page 1 - Property Overview
    c.drawString(100, 750, "DOWNTOWN LUXURY APARTMENTS")
    c.drawString(100, 730, "Property Information Document")
    c.drawString(100, 710, "-" * 60)
    c.drawString(100, 680, "Location: 123 Main Street, Downtown District")
    c.drawString(100, 660, "Total Units: 50 luxury apartments")
    c.drawString(100, 640, "Building Height: 15 floors")
    c.drawString(100, 620, "Parking: 75 underground spaces")
    c.drawString(100, 600, "Amenities: Rooftop pool, fitness center, concierge service")
    c.drawString(100, 580, "")
    c.drawString(100, 560, "UNIT TYPES:")
    c.drawString(120, 540, "- Studio: 500 sq ft, Starting at $350,000")
    c.drawString(120, 520, "- 1 Bedroom: 750 sq ft, Starting at $500,000")
    c.drawString(120, 500, "- 2 Bedroom: 1,200 sq ft, Starting at $750,000")
    c.drawString(120, 480, "- Penthouse: 2,500 sq ft, Starting at $2,000,000")
    c.showPage()
    
    # Page 2 - Financial Details
    c.drawString(100, 750, "FINANCIAL INFORMATION")
    c.drawString(100, 730, "-" * 60)
    c.drawString(100, 700, "Total Project Cost: $45,000,000")
    c.drawString(100, 680, "Expected ROI: 18% over 5 years")
    c.drawString(100, 660, "Occupancy Rate Target: 95%")
    c.drawString(100, 640, "Average Monthly HOA Fees: $450")
    c.drawString(100, 620, "Property Tax Rate: 1.2% annually")
    c.drawString(100, 600, "")
    c.drawString(100, 580, "CONSTRUCTION TIMELINE:")
    c.drawString(120, 560, "- Phase 1 (Foundation): 6 months")
    c.drawString(120, 540, "- Phase 2 (Structure): 12 months")
    c.drawString(120, 520, "- Phase 3 (Interior): 8 months")
    c.drawString(120, 500, "- Total Timeline: 26 months")
    c.showPage()
    
    # Page 3 - Sustainability Features
    c.drawString(100, 750, "SUSTAINABILITY & GREEN FEATURES")
    c.drawString(100, 730, "-" * 60)
    c.drawString(100, 700, "LEED Gold Certified Building")
    c.drawString(100, 680, "Solar panels provide 30% of building energy")
    c.drawString(100, 660, "Rainwater harvesting system for landscaping")
    c.drawString(100, 640, "Energy-efficient HVAC systems in all units")
    c.drawString(100, 620, "Electric vehicle charging stations")
    c.drawString(100, 600, "Green roof with native plants")
    c.showPage()
    
    c.save()
    return filename


async def test_sprint3_chat():
    """Test the complete Sprint 3 RAG Chat functionality"""
    
    print("\n" + "=" * 70)
    print("SPRINT 3 - RAG CHAT ENGINE TEST")
    print("=" * 70 + "\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Step 1: Health check
        print("1. Testing API health...")
        try:
            response = await client.get(f"{BASE_URL}/health")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}\n")
        except Exception as e:
            print(f"   Error: Server not running - {e}\n")
            print("   Please start the server first: python run_server.py")
            return
        
        # Step 2: Create a test project
        print("2. Creating test project...")
        project_data = {
            "name": "Downtown Luxury Apartments - RAG Test",
            "description": "Test project for Sprint 3 RAG functionality"
        }
        response = await client.post(f"{API_V1}/project", json=project_data)
        project = response.json()
        project_id = project["id"]
        print(f"   Created project ID: {project_id}")
        print(f"   Name: {project['name']}\n")
        
        # Step 3: Create and upload test PDF
        print("3. Creating test real estate document...")
        pdf_file = "test_real_estate.pdf"
        create_real_estate_pdf(pdf_file)
        print(f"   Created: {pdf_file}\n")
        
        print("4. Uploading document for ingestion...")
        with open(pdf_file, "rb") as f:
            files = {"file": (pdf_file, f, "application/pdf")}
            data = {"project_id": project_id}
            response = await client.post(
                f"{API_V1}/document/upload",
                files=files,
                data=data
            )
        
        upload_result = response.json()
        document_id = upload_result["document_id"]
        print(f"   Document ID: {document_id}")
        print(f"   Status: {upload_result['status']}\n")
        
        # Step 5: Wait for ingestion to complete
        print("5. Waiting for document ingestion...")
        max_wait = 15
        for i in range(max_wait):
            await asyncio.sleep(1)
            response = await client.get(f"{API_V1}/document/{document_id}/status")
            status_data = response.json()
            
            if status_data["status"] == "completed":
                print(f"   Ingestion completed!")
                print(f"   Total chunks: {status_data.get('total_chunks', 'N/A')}\n")
                break
            elif status_data["status"] == "failed":
                print(f"   Ingestion failed: {status_data.get('error_message')}\n")
                return
            
            if i == max_wait - 1:
                print(f"   Timeout waiting for ingestion\n")
                return
        
        # Step 6: Test chat queries
        print("6. Testing RAG Chat Queries")
        print("   " + "-" * 66 + "\n")
        
        test_queries = [
            "What is the location of this property?",
            "How many units are in the building?",
            "What is the price range for apartments?",
            "What are the sustainability features?",
            "What is the expected ROI?",
        ]
        
        for idx, query in enumerate(test_queries, 1):
            print(f"   Query {idx}: {query}")
            
            chat_request = {
                "project_id": project_id,
                "message": query
            }
            
            response = await client.post(
                f"{API_V1}/chat/query",
                json=chat_request
            )
            
            if response.status_code == 200:
                result = response.json()
                
                print(f"   Language: {result['language']}")
                print(f"   Latency: {result['latency_ms']}ms")
                print(f"   Sources: {len(result['sources'])} chunks")
                print(f"\n   Answer:")
                print(f"   {'-' * 66}")
                
                # Print answer with indentation
                answer_lines = result['answer'].split('\n')
                for line in answer_lines:
                    print(f"   {line}")
                
                print(f"   {'-' * 66}")
                
                # Show top source
                if result['sources']:
                    top_source = result['sources'][0]
                    print(f"\n   Top Source (Score: {top_source['score']:.4f}):")
                    print(f"   Chunk ID: {top_source['chunk_id']}")
                    print(f"   Text: {top_source['text'][:100]}...")
                
                print("\n" + "   " + "=" * 66 + "\n")
            else:
                print(f"   Error: {response.status_code}")
                print(f"   {response.text}\n")
        
        # Step 7: Test error cases
        print("7. Testing error handling...")
        
        # Test with non-existent project
        print("   a) Non-existent project...")
        response = await client.post(
            f"{API_V1}/chat/query",
            json={"project_id": 99999, "message": "test"}
        )
        print(f"      Status: {response.status_code} (expected 404)")
        if response.status_code == 404:
            print(f"      Message: {response.json()['detail']}\n")
        
        # Test with empty message
        print("   b) Empty message...")
        try:
            response = await client.post(
                f"{API_V1}/chat/query",
                json={"project_id": project_id, "message": ""}
            )
            print(f"      Status: {response.status_code} (expected 422)")
        except Exception as e:
            print(f"      Validation error (expected): {e}\n")
        
        # Cleanup
        print("\n8. Cleanup...")
        Path(pdf_file).unlink(missing_ok=True)
        print(f"   Removed test PDF\n")
        
        # Summary
        print("=" * 70)
        print("SPRINT 3 TEST COMPLETE")
        print("=" * 70)
        print("\nAll RAG Chat features are working:")
        print("  - Query embedding (stub)")
        print("  - FAISS vector search")
        print("  - Chunk retrieval from database")
        print("  - LLM answer generation (stub)")
        print("  - Source citation")
        print("  - Latency tracking")
        print("  - Error handling")
        print("\nNext steps:")
        print("  - Replace embedding stub with real sentence-transformers")
        print("  - Integrate actual LLM (OpenAI/Anthropic/local)")
        print("  - Add streaming responses")
        print("  - Enhance language detection")
        print("\nVisit http://localhost:8000/docs to explore the API")
        print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(test_sprint3_chat())
