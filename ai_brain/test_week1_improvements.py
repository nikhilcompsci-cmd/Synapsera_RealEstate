"""
Test script to verify Week 1 improvements are working
Run this after re-uploading documents
"""
import httpx
import asyncio
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1"

async def test_improvements():
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("=" * 70)
        print("Testing Week 1 Improvements")
        print("=" * 70)
        
        # Check if server is running
        print("\n1. Checking server health...")
        try:
            response = await client.get("http://localhost:8000/health")
            if response.status_code == 200:
                print("   ✅ Server is healthy")
                health = response.json()
                print(f"   Version: {health.get('version')}")
            else:
                print("   ❌ Server health check failed")
                return
        except Exception as e:
            print(f"   ❌ Cannot connect to server: {e}")
            print("   Make sure server is running: python run_server.py")
            return
        
        # List projects
        print("\n2. Listing projects...")
        try:
            response = await client.get(f"{BASE_URL}/project")
            projects = response.json()
            if projects:
                print(f"   ✅ Found {len(projects)} project(s)")
                for p in projects:
                    print(f"      - {p['name']} (ID: {p['id']})")
                project_id = projects[0]['id']
            else:
                print("   ⚠️  No projects found")
                print("   Please create a project and upload documents first")
                return
        except Exception as e:
            print(f"   ❌ Error listing projects: {e}")
            return
        
        # Test queries with different complexities
        test_queries = [
            "What is the project name?",
            "What is the price of 2 BHK?",
            "What amenities are available?",
            "Where is the project located?",
            "Tell me about the configuration and pricing"
        ]
        
        print(f"\n3. Testing chat queries with Project ID {project_id}...")
        print("   (With improvements: top_k=10, no truncation, max_tokens=1000)")
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n   Query {i}: '{query}'")
            try:
                response = await client.post(
                    f"{BASE_URL}/chat/query",
                    json={
                        "project_id": project_id,
                        "message": query
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    answer = result.get('answer', '')
                    sources = result.get('sources', [])
                    latency = result.get('latency_ms', 0)
                    
                    print(f"   ✅ Answer ({len(answer)} chars, {latency:.0f}ms):")
                    # Show first 200 chars
                    preview = answer[:200] + "..." if len(answer) > 200 else answer
                    print(f"      {preview}")
                    
                    if sources:
                        print(f"   📚 Retrieved {len(sources)} chunks:")
                        # Show top 3 scores
                        for idx, src in enumerate(sources[:3], 1):
                            score = src.get('score', 0)
                            print(f"      {idx}. Score: {score:.3f} (Chunk ID: {src.get('chunk_id')})")
                        
                        # Check for improvement indicators
                        top_score = sources[0].get('score', 0)
                        if top_score > 0.80:
                            print(f"   🎯 Excellent retrieval! Top score: {top_score:.3f}")
                        elif top_score > 0.70:
                            print(f"   ✅ Good retrieval! Top score: {top_score:.3f}")
                        else:
                            print(f"   ⚠️  Moderate retrieval. Top score: {top_score:.3f}")
                else:
                    print(f"   ❌ Error: {response.status_code}")
                    print(f"      {response.text}")
            except Exception as e:
                print(f"   ❌ Query failed: {e}")
        
        # Check log file
        print("\n4. Checking log file...")
        log_file = Path("logs/app.log")
        if log_file.exists():
            print(f"   ✅ Log file exists: {log_file}")
            size = log_file.stat().st_size
            print(f"   📊 Log size: {size:,} bytes")
            
            # Show last few lines
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines:
                    print(f"   📝 Last 3 log entries:")
                    for line in lines[-3:]:
                        print(f"      {line.strip()}")
        else:
            print("   ⚠️  Log file not created yet")
        
        print("\n" + "=" * 70)
        print("Testing Complete!")
        print("=" * 70)
        print("\n💡 To monitor logs in real-time:")
        print("   Get-Content logs\\app.log -Tail 50 -Wait")
        print("\n💡 Compare with previous results:")
        print("   - Similarity scores should be higher (0.75-0.90 range)")
        print("   - Answers should be more complete (no truncation)")
        print("   - 10 chunks retrieved instead of 5")
        print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_improvements())
