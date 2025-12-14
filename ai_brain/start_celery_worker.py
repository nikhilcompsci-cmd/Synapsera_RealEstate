"""
Celery Worker Startup Script
=============================

Starts a Celery worker for processing async ingestion tasks.

Usage:
    python start_celery_worker.py

For production, use systemd or supervisor instead.
"""

import sys
import subprocess
from pathlib import Path

def start_worker():
    """Start Celery worker with recommended settings."""
    
    print("=" * 70)
    print("Starting Celery Worker for AI Brain")
    print("=" * 70)
    print()
    
    # Check if Redis is running
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis connection successful")
    except Exception as e:
        print("❌ Redis connection failed!")
        print(f"   Error: {e}")
        print()
        print("Please start Redis first:")
        print("   Windows: redis-server")
        print("   Linux: sudo systemctl start redis")
        return False
    
    print()
    print("Starting Celery worker...")
    print("   Queues: default, high_priority, low_priority")
    print("   Concurrency: 4 workers")
    print("   Log Level: INFO")
    print()
    print("Press CTRL+C to stop the worker")
    print("=" * 70)
    print()
    
    # Start Celery worker
    cmd = [
        sys.executable,
        "-m", "celery",
        "-A", "celery_app",
        "worker",
        "--loglevel=info",
        "--pool=solo",  # Required for Windows
        "--concurrency=4",
    ]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n\nStopping Celery worker...")
        return True

if __name__ == "__main__":
    start_worker()
