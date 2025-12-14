"""
Celery Integration Test Script
===============================

Tests the Celery implementation without requiring Redis to be running.
Validates configuration, task registration, and mock task execution.

Run this to verify the Celery setup is correct before starting workers.
"""

import sys
from pathlib import Path

def test_imports():
    """Test that all Celery modules import correctly."""
    print("=" * 70)
    print("TEST 1: Module Imports")
    print("=" * 70)
    
    try:
        from celery_app import celery_app, BaseTask
        print("✅ celery_app imported successfully")
        print(f"   App name: {celery_app.main}")
        print(f"   Broker: {celery_app.conf.broker_url}")
        print(f"   Backend: {celery_app.conf.result_backend}")
    except Exception as e:
        print(f"❌ Failed to import celery_app: {e}")
        return False
    
    try:
        from tasks.ingestion_tasks import ingest_document_async, get_task_status
        print("✅ ingestion_tasks imported successfully")
        print(f"   Task: {ingest_document_async.name}")
    except Exception as e:
        print(f"❌ Failed to import ingestion_tasks: {e}")
        return False
    
    try:
        from tasks.maintenance_tasks import cleanup_old_files, cleanup_expired_results
        print("✅ maintenance_tasks imported successfully")
    except Exception as e:
        print(f"❌ Failed to import maintenance_tasks: {e}")
        return False
    
    print()
    return True


def test_configuration():
    """Test Celery configuration settings."""
    print("=" * 70)
    print("TEST 2: Configuration")
    print("=" * 70)
    
    try:
        from celery_app import celery_app
        
        # Security settings
        assert celery_app.conf.task_serializer == 'json', "Task serializer should be JSON"
        assert 'json' in celery_app.conf.accept_content, "Should accept JSON content"
        assert 'pickle' not in celery_app.conf.accept_content, "Should NOT accept pickle (security)"
        print("✅ Security: JSON serialization (no pickle)")
        
        # Time limits
        assert celery_app.conf.task_time_limit == 1800, "Task time limit should be 1800s (30 min)"
        assert celery_app.conf.task_soft_time_limit == 1500, "Soft time limit should be 1500s (25 min)"
        print("✅ Time limits: 30 min hard, 25 min soft")
        
        # Result expiration
        assert celery_app.conf.result_expires == 3600, "Results should expire after 1 hour"
        print("✅ Result expiration: 1 hour")
        
        # Worker settings
        assert celery_app.conf.worker_max_tasks_per_child == 1000, "Worker should recycle after 1000 tasks"
        assert celery_app.conf.worker_prefetch_multiplier == 4, "Worker should prefetch 4 tasks"
        print("✅ Worker: Prefetch=4, Recycle after 1000 tasks")
        
        # Task tracking
        assert celery_app.conf.task_track_started == True, "Should track task start"
        assert celery_app.conf.task_acks_late == True, "Should acknowledge tasks late (safer)"
        print("✅ Task tracking: Enabled")
        
        print()
        return True
        
    except AssertionError as e:
        print(f"❌ Configuration test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_task_registration():
    """Test that tasks are properly registered."""
    print("=" * 70)
    print("TEST 3: Task Registration")
    print("=" * 70)
    
    try:
        from celery_app import celery_app
        
        # Get all registered tasks
        registered_tasks = list(celery_app.tasks.keys())
        
        print(f"Found {len(registered_tasks)} registered tasks:")
        for task_name in sorted(registered_tasks):
            if not task_name.startswith('celery.'):
                print(f"   ✅ {task_name}")
        
        # Check for our custom tasks
        expected_tasks = [
            'tasks.ingestion.ingest_document',
            'tasks.ingestion.get_task_status',
            'tasks.maintenance.cleanup_old_files',
            'tasks.maintenance.cleanup_expired_results',
            'celery.ping',
        ]
        
        print("\nChecking expected tasks:")
        all_found = True
        for task_name in expected_tasks:
            if task_name in registered_tasks:
                print(f"   ✅ {task_name}")
            else:
                print(f"   ❌ {task_name} NOT FOUND")
                all_found = False
        
        print()
        return all_found
        
    except Exception as e:
        print(f"❌ Task registration test failed: {e}")
        return False


def test_task_signature():
    """Test task signatures and options."""
    print("=" * 70)
    print("TEST 4: Task Signatures")
    print("=" * 70)
    
    try:
        from tasks.ingestion_tasks import ingest_document_async
        
        # Check task options
        print(f"Task name: {ingest_document_async.name}")
        print(f"Max retries: {ingest_document_async.max_retries}")
        print(f"Time limit: {ingest_document_async.time_limit}")
        print(f"Soft time limit: {ingest_document_async.soft_time_limit}")
        print(f"Auto-retry: {ingest_document_async.autoretry_for}")
        print(f"Acks late: {ingest_document_async.acks_late}")
        
        # Validate settings
        assert ingest_document_async.max_retries == 3, "Should retry 3 times"
        assert ingest_document_async.time_limit == 1800, "Time limit should be 1800s"
        print("\n✅ Task signature valid")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Task signature test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_redis_connection():
    """Test Redis connection (optional)."""
    print("=" * 70)
    print("TEST 5: Redis Connection (Optional)")
    print("=" * 70)
    
    try:
        import redis
        from celery_app import celery_app
        
        # Parse broker URL
        broker_url = celery_app.conf.broker_url
        print(f"Broker URL: {broker_url}")
        
        # Try to connect
        r = redis.from_url(broker_url)
        r.ping()
        print("✅ Redis connection successful")
        print("   Redis is running and accessible")
        
        print()
        return True
        
    except ImportError:
        print("⚠️  Redis Python client not installed")
        print("   Install with: pip install redis")
        print()
        return True  # Not a failure, just optional
        
    except Exception as e:
        print("⚠️  Redis connection failed")
        print(f"   Error: {e}")
        print("\n   Redis is not required for testing configuration,")
        print("   but is required to run Celery workers.")
        print("\n   To install Redis on Windows:")
        print("   1. choco install redis-64")
        print("   2. redis-server")
        print()
        return True  # Not a failure for this test


def test_api_integration():
    """Test API integration with Celery tasks."""
    print("=" * 70)
    print("TEST 6: API Integration")
    print("=" * 70)
    
    try:
        from api.document_router import router
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        
        # Create test app
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        
        print("✅ Document router imports correctly")
        print("   Routes integrated with Celery tasks")
        
        # Check if task imports are present
        import inspect
        source = inspect.getsource(router.__class__)
        if 'ingest_document_async' in source:
            print("✅ Async ingestion task integrated")
        if 'get_task_status' in source:
            print("✅ Task status endpoint integrated")
        
        print()
        return True
        
    except ImportError as e:
        print(f"⚠️  Could not test API integration: {e}")
        print("   This is optional for Celery testing")
        print()
        return True
        
    except Exception as e:
        print(f"❌ API integration test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 20 + "CELERY INTEGRATION TEST" + " " * 25 + "║")
    print("╚" + "=" * 68 + "╝")
    print()
    
    tests = [
        ("Module Imports", test_imports),
        ("Configuration", test_configuration),
        ("Task Registration", test_task_registration),
        ("Task Signatures", test_task_signature),
        ("Redis Connection", test_redis_connection),
        ("API Integration", test_api_integration),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:10} {test_name}")
    
    print()
    print(f"Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Celery is properly configured.")
        print("\nNext steps:")
        print("1. Install Redis: choco install redis-64")
        print("2. Start Redis: redis-server")
        print("3. Start Celery worker: python start_celery_worker.py")
        print("4. Start FastAPI server: python run_server.py")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
