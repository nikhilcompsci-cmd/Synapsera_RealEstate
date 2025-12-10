"""
Simple script to start the API server and run tests.
"""
import subprocess
import time
import sys

print("🚀 Starting AI Brain API Server...")
print("=" * 50)

# Start the server
server_process = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "main:app", "--reload"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

# Wait for server to start
print("\n⏳ Waiting for server to initialize...")
time.sleep(8)

print("\n" + "=" * 50)
print("✅ Server should be running now!")
print("=" * 50)
print("\n🌐 Access the API:")
print("   - Interactive Docs: http://localhost:8000/docs")
print("   - Health Check: http://localhost:8000/health")
print("   - Database Admin: http://localhost:8081")
print("\n📝 To test the API:")
print("   - Open another terminal and run: python test_api.py")
print("   - Or visit http://localhost:8000/docs in your browser")
print("\n⏸️  Press Ctrl+C to stop the server")
print("=" * 50)
print("\n")

try:
    # Keep server running and show output
    for line in server_process.stdout:
        print(line, end='')
except KeyboardInterrupt:
    print("\n\n🛑 Stopping server...")
    server_process.terminate()
    server_process.wait()
    print("✅ Server stopped")
