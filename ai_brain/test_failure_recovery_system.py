"""
Failed Document Recovery System - Integration Tests
===================================================

Tests all components of the failure handling system:
1. Database models
2. Error classification
3. Failed documents service
4. Enhanced ingestion task
5. API schemas

Author: AI Brain Team
Date: December 2025
"""

import sys
import traceback
from datetime import datetime


def test_models():
    """Test database models import and basic functionality."""
    print("\n" + "="*70)
    print("TEST 1: Database Models")
    print("="*70)
    
    try:
        from db.models_failed_documents import (
            FailedDocument, 
            ProcessingCheckpoint, 
            ErrorType, 
            FailureStatus
        )
        print("✅ Models imported successfully")
        
        # Test enum values
        assert ErrorType.TRANSIENT.value == "transient"
        assert ErrorType.PERMANENT.value == "permanent"
        assert ErrorType.USER_FIXABLE.value == "user_fixable"
        assert ErrorType.SYSTEM_ISSUE.value == "system_issue"
        assert ErrorType.RATE_LIMIT.value == "rate_limit"
        assert ErrorType.TIMEOUT.value == "timeout"
        assert ErrorType.UNKNOWN.value == "unknown"
        print("✅ ErrorType enum values correct")
        
        assert FailureStatus.RETRYING.value == "retrying"
        assert FailureStatus.PERMANENTLY_FAILED.value == "permanently_failed"
        assert FailureStatus.RESOLVED.value == "resolved"
        assert FailureStatus.IGNORED.value == "ignored"
        print("✅ FailureStatus enum values correct")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        traceback.print_exc()
        return False


def test_error_classifier():
    """Test error classification logic."""
    print("\n" + "="*70)
    print("TEST 2: Error Classification Service")
    print("="*70)
    
    try:
        from services.error_classifier import error_classifier
        from db.models_failed_documents import ErrorType
        print("✅ Error classifier imported")
        
        # Test transient error (network/connection issues)
        exc = ConnectionError("Redis connection refused")
        error_type, config = error_classifier.classify(exc)
        assert error_type == ErrorType.TRANSIENT
        assert config['max_retries'] == 5
        assert config['can_auto_retry'] == True
        assert config['exponential_backoff'] == True
        print(f"✅ Transient error classified correctly: {error_type.value}")
        
        # Test permanent error
        exc = Exception("corrupted PDF file")
        error_type, config = error_classifier.classify(exc)
        assert error_type == ErrorType.PERMANENT
        assert config['max_retries'] == 0
        assert config['can_auto_retry'] == False
        print(f"✅ Permanent error classified correctly: {error_type.value}")
        
        # Test user-fixable error
        exc = Exception("password required for PDF")
        error_type, config = error_classifier.classify(exc)
        assert error_type == ErrorType.USER_FIXABLE
        assert config['notify_user'] == True
        print(f"✅ User-fixable error classified correctly: {error_type.value}")
        
        # Test system issue
        exc = Exception("disk full - no space left")
        error_type, config = error_classifier.classify(exc)
        assert error_type == ErrorType.SYSTEM_ISSUE
        assert config['alert_admin'] == True
        print(f"✅ System issue classified correctly: {error_type.value}")
        
        # Test rate limit
        exc = Exception("rate limit exceeded - too many requests")
        error_type, config = error_classifier.classify(exc)
        assert error_type == ErrorType.RATE_LIMIT
        assert config['max_retries'] == 10
        assert config['retry_delay'] == 300
        print(f"✅ Rate limit classified correctly: {error_type.value}")
        
        # Test timeout
        exc = Exception("operation timeout after 30 minutes")
        error_type, config = error_classifier.classify(exc)
        assert error_type == ErrorType.TIMEOUT
        assert config['max_retries'] == 2
        print(f"✅ Timeout classified correctly: {error_type.value}")
        
        # Test sanitization
        raw_msg = "Failed at /home/user123/secret with password=mysecret123 and api_key=abc123"
        sanitized = error_classifier.sanitize_error_message(raw_msg)
        assert "user123" not in sanitized
        assert "mysecret123" not in sanitized
        assert "abc123" not in sanitized
        assert "[user]" in sanitized
        assert "[REDACTED]" in sanitized
        print("✅ Error message sanitization working")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        traceback.print_exc()
        return False


def test_failed_documents_service():
    """Test failed documents service methods."""
    print("\n" + "="*70)
    print("TEST 3: Failed Documents Service")
    print("="*70)
    
    try:
        from services.failed_documents_service import failed_documents_service
        print("✅ Failed documents service imported")
        
        # Verify service has required methods
        assert hasattr(failed_documents_service, 'record_failure')
        assert hasattr(failed_documents_service, 'get_failed_documents')
        assert hasattr(failed_documents_service, 'get_documents_pending_retry')
        assert hasattr(failed_documents_service, 'schedule_retry')
        assert hasattr(failed_documents_service, 'mark_resolved')
        assert hasattr(failed_documents_service, 'mark_permanently_failed')
        assert hasattr(failed_documents_service, 'cleanup_orphaned_files')
        assert hasattr(failed_documents_service, 'get_failure_metrics')
        print("✅ All required methods present")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        traceback.print_exc()
        return False


def test_enhanced_ingestion_task():
    """Test enhanced ingestion task with failure handling."""
    print("\n" + "="*70)
    print("TEST 4: Enhanced Ingestion Task")
    print("="*70)
    
    try:
        from tasks.ingestion_tasks import ingest_document_async, get_task_status
        print("✅ Ingestion tasks imported")
        
        # Verify task is registered with Celery
        assert ingest_document_async.name == 'tasks.ingestion.ingest_document'
        print(f"✅ Task registered: {ingest_document_async.name}")
        
        # Verify task configuration
        assert ingest_document_async.max_retries == 3
        assert ingest_document_async.default_retry_delay == 60
        print("✅ Task configuration correct")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        traceback.print_exc()
        return False


def test_api_schemas():
    """Test API schemas for failed documents."""
    print("\n" + "="*70)
    print("TEST 5: API Schemas")
    print("="*70)
    
    try:
        from api.schemas import (
            FailedDocumentResponse,
            FailedDocumentListResponse,
            RetryFailedDocumentRequest,
            UpdateFailedDocumentRequest,
            FailureMetricsResponse,
            SystemHealthResponse
        )
        print("✅ All schemas imported successfully")
        
        # Test FailedDocumentResponse schema
        schema_fields = FailedDocumentResponse.model_fields.keys()
        required_fields = {
            'id', 'project_id', 'filename', 'error_type', 
            'error_message', 'status', 'retry_count', 
            'max_retries', 'created_at'
        }
        assert required_fields.issubset(schema_fields)
        print(f"✅ FailedDocumentResponse has all required fields")
        
        # Test RetryFailedDocumentRequest
        schema_fields = RetryFailedDocumentRequest.model_fields.keys()
        assert 'retry_delay_seconds' in schema_fields
        print("✅ RetryFailedDocumentRequest schema correct")
        
        # Test FailureMetricsResponse
        schema_fields = FailureMetricsResponse.model_fields.keys()
        required_fields = {
            'total_failures', 'by_error_type', 'by_status',
            'avg_retry_count', 'success_rate', 'time_window_days'
        }
        assert required_fields.issubset(schema_fields)
        print("✅ FailureMetricsResponse schema correct")
        
        # Test SystemHealthResponse
        schema_fields = SystemHealthResponse.model_fields.keys()
        required_fields = {
            'status', 'celery_workers', 'redis_connected',
            'database_connected', 'failed_tasks_24h', 'timestamp'
        }
        assert required_fields.issubset(schema_fields)
        print("✅ SystemHealthResponse schema correct")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        traceback.print_exc()
        return False


def test_database_migration():
    """Test database migration file exists and is valid."""
    print("\n" + "="*70)
    print("TEST 6: Database Migration")
    print("="*70)
    
    try:
        import os
        migration_file = "alembic/versions/003_create_failed_documents_and_checkpoints_tables.py"
        
        if not os.path.exists(migration_file):
            print(f"❌ Migration file not found: {migration_file}")
            return False
        
        print(f"✅ Migration file exists: {migration_file}")
        
        # Try importing the migration
        import importlib.util
        spec = importlib.util.spec_from_file_location("migration_003", migration_file)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        
        # Verify migration has required functions
        assert hasattr(migration, 'upgrade')
        assert hasattr(migration, 'downgrade')
        assert migration.revision == '003'
        assert migration.down_revision == '002'
        print("✅ Migration structure valid")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        traceback.print_exc()
        return False


def test_celery_configuration():
    """Test Celery configuration includes failure handling."""
    print("\n" + "="*70)
    print("TEST 7: Celery Configuration")
    print("="*70)
    
    try:
        from celery_app import celery_app, BaseTask
        print("✅ Celery app imported")
        
        # Verify BaseTask has retry configuration
        assert hasattr(BaseTask, 'autoretry_for')
        assert hasattr(BaseTask, 'retry_kwargs')
        assert hasattr(BaseTask, 'retry_backoff')
        print("✅ BaseTask has retry configuration")
        
        # Verify task is registered
        registered_tasks = list(celery_app.tasks.keys())
        assert 'tasks.ingestion.ingest_document' in registered_tasks
        print("✅ Ingestion task registered with Celery")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all integration tests."""
    print("\n" + "="*70)
    print("FAILED DOCUMENT RECOVERY SYSTEM - INTEGRATION TESTS")
    print("="*70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Database Models", test_models),
        ("Error Classification", test_error_classifier),
        ("Failed Documents Service", test_failed_documents_service),
        ("Enhanced Ingestion Task", test_enhanced_ingestion_task),
        ("API Schemas", test_api_schemas),
        ("Database Migration", test_database_migration),
        ("Celery Configuration", test_celery_configuration),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ UNEXPECTED ERROR in {test_name}: {e}")
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! System is ready for deployment.")
        print("\nNext steps:")
        print("1. Apply database migration: alembic upgrade head")
        print("2. Restart Celery workers")
        print("3. Restart API server")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
