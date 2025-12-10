"""
Test script to verify all API endpoints are working.
"""
import asyncio
import httpx
import json


async def test_api():
    """Test all Sprint 1 endpoints."""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        print("🧪 Testing AI Brain API Endpoints\n")
        print("=" * 50)
        
        # Test 1: Health Check
        print("\n1️⃣  Testing GET /health")
        try:
            response = await client.get(f"{base_url}/health")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {json.dumps(response.json(), indent=2)}")
            assert response.status_code == 200
            print("   ✅ Health check passed!")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        # Test 2: Create Project
        print("\n2️⃣  Testing POST /api/v1/project")
        project_data = {
            "name": "Downtown Office Complex",
            "description": "Analysis of commercial real estate documentation"
        }
        try:
            response = await client.post(
                f"{base_url}/api/v1/project",
                json=project_data
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {json.dumps(response.json(), indent=2)}")
            assert response.status_code == 201
            project_id = response.json()["id"]
            print(f"   ✅ Project created with ID: {project_id}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        # Test 3: Create Another Project
        print("\n3️⃣  Testing POST /api/v1/project (second project)")
        project_data2 = {
            "name": "Residential Tower Project",
            "description": "High-rise residential development analysis"
        }
        try:
            response = await client.post(
                f"{base_url}/api/v1/project",
                json=project_data2
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {json.dumps(response.json(), indent=2)}")
            assert response.status_code == 201
            print(f"   ✅ Second project created!")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        # Test 4: List All Projects
        print("\n4️⃣  Testing GET /api/v1/project")
        try:
            response = await client.get(f"{base_url}/api/v1/project")
            print(f"   Status: {response.status_code}")
            projects = response.json()
            print(f"   Found {len(projects)} projects:")
            for project in projects:
                print(f"     - [{project['id']}] {project['name']}")
            assert response.status_code == 200
            assert len(projects) >= 2
            print("   ✅ Project listing works!")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        # Test 5: Root Endpoint
        print("\n5️⃣  Testing GET /")
        try:
            response = await client.get(f"{base_url}/")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {json.dumps(response.json(), indent=2)}")
            assert response.status_code == 200
            print("   ✅ Root endpoint works!")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        print("\n" + "=" * 50)
        print("✨ ALL TESTS PASSED! ✨")
        print("=" * 50)
        print("\n📊 Summary:")
        print("   ✅ Health check endpoint")
        print("   ✅ Create project endpoint")
        print("   ✅ List projects endpoint")
        print("   ✅ Root endpoint")
        print("\n🎉 Sprint 1 API is fully functional!")
        print("\n🌐 Access points:")
        print(f"   - API Docs: http://localhost:8000/docs")
        print(f"   - Database Admin: http://localhost:8081")


if __name__ == "__main__":
    try:
        asyncio.run(test_api())
    except KeyboardInterrupt:
        print("\n\n⏸️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        print("\n💡 Make sure the API server is running:")
        print("   python -m uvicorn main:app --reload")
