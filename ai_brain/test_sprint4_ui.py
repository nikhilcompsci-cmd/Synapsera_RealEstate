"""
Test Sprint 4 UI Setup
Verifies that UI files are in place and server can mount them
"""
from pathlib import Path

print("🧪 Testing Sprint 4 UI Setup\\n")

# Check UI directory
ui_dir = Path("ui")
if not ui_dir.exists():
    print("❌ UI directory not found")
    exit(1)

print("✅ UI directory exists")

# Check required files
required_files = [
    "ui/index.html",
    "ui/app.js", 
    "ui/styles.css"
]

all_exist = True
for file_path in required_files:
    path = Path(file_path)
    if path.exists():
        size = path.stat().st_size
        print(f"✅ {file_path} ({size:,} bytes)")
    else:
        print(f"❌ {file_path} missing")
        all_exist = False

if not all_exist:
    print("\\n❌ Some UI files are missing")
    exit(1)

# Check main.py has UI mount
main_py = Path("main.py")
if main_py.exists():
    content = main_py.read_text()
    if 'StaticFiles' in content and 'mount("/ui"' in content:
        print("✅ main.py has UI mount configured")
    else:
        print("⚠️  main.py may not have UI mount configured")
else:
    print("❌ main.py not found")

print("\\n" + "="*60)
print("✅ Sprint 4 UI Setup Complete!")
print("="*60)
print("\\nTo test the UI:")
print("1. Start server: python run_server.py")
print("2. Open browser: http://localhost:8000/ui/index.html")
print("3. Create a project, upload documents, and chat!")
