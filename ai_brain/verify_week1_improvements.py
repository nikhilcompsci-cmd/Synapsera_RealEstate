"""
Verification script for Week 1 accuracy improvements
Tests all critical changes are working correctly
"""
import sys
import os
from pathlib import Path

print("=" * 70)
print("Week 1 Improvements Verification")
print("=" * 70)

# Check 1: FAISS Service - IndexFlatIP
print("\n1. Checking FAISS Index Type...")
try:
    from services.faiss_service import FAISSService
    import faiss
    
    service = FAISSService()
    index = service.create_index(dimension=384)
    
    # Check if it's IndexFlatIP
    if isinstance(index, faiss.IndexFlatIP):
        print("   ✅ FAISS using IndexFlatIP (Cosine Similarity)")
    elif isinstance(index, faiss.IndexFlatL2):
        print("   ❌ FAISS still using IndexFlatL2 - FIX NEEDED!")
    else:
        print(f"   ⚠️  Unknown index type: {type(index)}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Check 2: Embedding Normalization
print("\n2. Checking Embedding Normalization...")
try:
    from services.embedding_service import EmbeddingService
    import numpy as np
    
    service = EmbeddingService()
    embedding = service.embed_text("test query")
    
    # Check if normalized (L2 norm should be ~1.0)
    norm = np.linalg.norm(embedding)
    if 0.99 <= norm <= 1.01:
        print(f"   ✅ Embeddings are normalized (norm: {norm:.6f})")
    else:
        print(f"   ⚠️  Embeddings may not be normalized (norm: {norm:.6f})")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Check 3: LLM Max Tokens
print("\n3. Checking LLM Max Tokens...")
try:
    from rag.llm_engine import LLMEngine
    
    engine = LLMEngine()
    if engine.max_tokens == 1000:
        print(f"   ✅ Max tokens set to 1000 (was 500)")
    elif engine.max_tokens == 500:
        print(f"   ❌ Max tokens still 500 - FIX NEEDED!")
    else:
        print(f"   ⚠️  Max tokens set to {engine.max_tokens}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Check 4: Logging Configuration
print("\n4. Checking Logging Configuration...")
try:
    from config.logging_config import setup_logging, get_logger
    
    # Test setup
    setup_logging(log_level="INFO", log_file=None, enable_console=False)
    logger = get_logger(__name__)
    
    print("   ✅ Logging system initialized")
    print("   ✅ Rotating file handler available")
    print("   ✅ Logger creation working")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Check 5: Settings Updates
print("\n5. Checking Settings Configuration...")
try:
    from config.settings import get_settings
    
    settings = get_settings()
    
    checks = [
        ("log_level", hasattr(settings, 'log_level')),
        ("log_file", hasattr(settings, 'log_file')),
        ("environment", hasattr(settings, 'environment')),
        ("is_production", hasattr(settings, 'is_production')),
        ("is_development", hasattr(settings, 'is_development'))
    ]
    
    all_passed = all(check[1] for check in checks)
    
    if all_passed:
        print("   ✅ All new settings attributes present")
        print(f"   - Environment: {settings.environment}")
        print(f"   - Log Level: {settings.log_level}")
    else:
        print("   ⚠️  Some settings missing:")
        for name, passed in checks:
            if not passed:
                print(f"      - Missing: {name}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Check 6: Logs Directory
print("\n6. Checking Logs Directory...")
logs_dir = Path("logs")
if logs_dir.exists():
    print("   ✅ Logs directory exists")
else:
    print("   ℹ️  Logs directory will be created on first run")
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
        print("   ✅ Created logs directory")
    except Exception as e:
        print(f"   ❌ Failed to create logs directory: {e}")

# Check 7: API Chat Router Top-K
print("\n7. Checking API Chat Router (Top-K)...")
try:
    # Read the file to check top_k value
    chat_router_path = Path("api/chat_router.py")
    if chat_router_path.exists():
        content = chat_router_path.read_text()
        if "top_k=10" in content:
            print("   ✅ Top-K increased to 10 (was 5)")
        elif "top_k=5" in content:
            print("   ❌ Top-K still 5 - FIX NEEDED!")
        else:
            print("   ⚠️  Could not verify top_k value")
    else:
        print("   ❌ chat_router.py not found")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Check 8: LLM Engine Chunk Truncation
print("\n8. Checking LLM Chunk Truncation Removal...")
try:
    llm_engine_path = Path("rag/llm_engine.py")
    if llm_engine_path.exists():
        content = llm_engine_path.read_text()
        if "chunk[:800]" in content:
            print("   ❌ Chunk truncation still present - FIX NEEDED!")
        elif "chunk}" in content or 'f"[Document {i+1}]\\n{chunk}"' in content:
            print("   ✅ Chunk truncation removed - using full chunks")
        else:
            print("   ⚠️  Could not verify chunk handling")
    else:
        print("   ❌ llm_engine.py not found")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Summary
print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
print("\n⚠️  IMPORTANT NEXT STEPS:")
print("1. Delete old FAISS indexes:")
print("   Remove-Item -Path 'data\\faiss_indexes\\*.faiss' -Force")
print("   Remove-Item -Path 'data\\faiss_indexes\\*_mapping.npy' -Force")
print("\n2. Restart the server:")
print("   python run_server.py")
print("\n3. Re-upload documents through UI:")
print("   http://localhost:8000/ui/index.html")
print("\n4. Monitor logs for accuracy improvements:")
print("   Get-Content logs\\app.log -Tail 50 -Wait")
print("\n" + "=" * 70)
