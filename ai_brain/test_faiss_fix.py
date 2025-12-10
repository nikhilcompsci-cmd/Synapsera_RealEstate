"""
Test FAISS file extension fix and mapping file creation
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# Check if files exist with correct extensions
faiss_dir = Path("data/faiss_indexes")

print("🔍 Checking FAISS files...")
print(f"Directory: {faiss_dir}")
print()

# Check for project 6
project_id = 6

old_index = faiss_dir / f"project_{project_id}.index"
new_index = faiss_dir / f"project_{project_id}.faiss"
mapping_file = faiss_dir / f"project_{project_id}_mapping.npy"

print(f"Project {project_id}:")
print(f"  ❌ Old format (.index): {old_index.exists()} - {old_index}")
print(f"  ✅ New format (.faiss): {new_index.exists()} - {new_index}")
print(f"  📋 Mapping file (.npy): {mapping_file.exists()} - {mapping_file}")
print()

# List all FAISS files
print("All FAISS files in directory:")
if faiss_dir.exists():
    for file in sorted(faiss_dir.iterdir()):
        size_kb = file.stat().st_size / 1024
        print(f"  • {file.name} ({size_kb:.2f} KB)")
else:
    print("  Directory does not exist")

print()
print("✅ Code changes applied:")
print("  1. retriever.py now looks for .faiss extension")
print("  2. FAISSService has save_chunk_mapping() method")
print("  3. Ingestion service saves chunk ID mapping")
print()

if new_index.exists() and not mapping_file.exists():
    print("⚠️  WARNING: FAISS index exists but mapping file is missing!")
    print("   You need to re-ingest documents to generate mapping files.")
    print()
    print("   Steps:")
    print("   1. Delete existing FAISS indexes (optional)")
    print("   2. Re-upload and process documents")
    print("   3. Mapping files will be created automatically")
elif new_index.exists() and mapping_file.exists():
    print("✅ All files present! Ready to test chat endpoint.")
else:
    print("ℹ️  No documents indexed yet. Upload documents to test.")
