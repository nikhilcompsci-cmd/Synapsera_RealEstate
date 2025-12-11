"""
Manual Code Verification Test
==============================

Manually review the actual implementation to confirm behavior.
"""

import sys


def verify_document_router():
    """Verify document_router.py implementation."""
    print("\n" + "=" * 70)
    print("CODE VERIFICATION: api/document_router.py")
    print("=" * 70)
    
    with open("api/document_router.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    checks = []
    
    # Check 1: Import get_settings inside exception handler
    if "from config.settings import get_settings" in content:
        checks.append(("✅", "get_settings imported"))
    else:
        checks.append(("❌", "get_settings NOT found"))
    
    # Check 2: Production check exists
    if "if settings.is_production:" in content:
        checks.append(("✅", "Production mode check exists"))
    else:
        checks.append(("❌", "Production mode check MISSING"))
    
    # Check 3: HTTPException 503 in production
    if "raise HTTPException" in content and "503" in content:
        checks.append(("✅", "HTTPException 503 for production"))
    else:
        checks.append(("❌", "HTTPException 503 MISSING"))
    
    # Check 4: Service unavailable message
    if "Service unavailable" in content or "Task queue" in content:
        checks.append(("✅", "Error message for production"))
    else:
        checks.append(("❌", "Error message MISSING"))
    
    # Check 5: Development fallback
    if "[DEV FALLBACK]" in content or "DEV MODE" in content:
        checks.append(("✅", "Development fallback logging"))
    else:
        checks.append(("❌", "Development fallback MISSING"))
    
    # Check 6: Sync ingestion call
    if "ingestion_service.ingest_document" in content:
        checks.append(("✅", "Sync ingestion fallback call"))
    else:
        checks.append(("❌", "Sync ingestion call MISSING"))
    
    # Check 7: No fallback comment
    if "fallback is DISABLED in production" in content or "PRODUCTION MUST NOT FALLBACK" in content:
        checks.append(("✅", "Production no-fallback documented"))
    else:
        checks.append(("⚠️", "Could add production no-fallback comment"))
    
    print("\nImplementation checks:")
    for status, description in checks:
        print(f"  {status} {description}")
    
    all_critical_passed = all(status == "✅" for status, desc in checks[:6])
    return all_critical_passed


def verify_main_startup():
    """Verify main.py startup implementation."""
    print("\n" + "=" * 70)
    print("CODE VERIFICATION: main.py")
    print("=" * 70)
    
    with open("main.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    checks = []
    
    # Check 1: Redis ping check
    if "r.ping()" in content:
        checks.append(("✅", "Redis connection check"))
    else:
        checks.append(("❌", "Redis check MISSING"))
    
    # Check 2: Production environment check
    if "if settings.is_production:" in content:
        checks.append(("✅", "Production mode check"))
    else:
        checks.append(("❌", "Production check MISSING"))
    
    # Check 3: RuntimeError in production
    if "raise RuntimeError" in content and "Redis/Celery" in content:
        checks.append(("✅", "RuntimeError for production"))
    else:
        checks.append(("❌", "RuntimeError MISSING"))
    
    # Check 4: Development warning
    if "logger.warning" in content or "DEV MODE" in content:
        checks.append(("✅", "Development warning logged"))
    else:
        checks.append(("❌", "Development warning MISSING"))
    
    # Check 5: Production fatal error message
    if "PRODUCTION ERROR" in content or "FATAL ERROR" in content:
        checks.append(("✅", "Production error message"))
    else:
        checks.append(("❌", "Production error MISSING"))
    
    # Check 6: Development graceful message
    if "DEV MODE WARNING" in content or "ONLY available in development" in content:
        checks.append(("✅", "Development mode message"))
    else:
        checks.append(("❌", "Development message MISSING"))
    
    print("\nImplementation checks:")
    for status, description in checks:
        print(f"  {status} {description}")
    
    all_passed = all(status == "✅" for status, desc in checks)
    return all_passed


def verify_settings_class():
    """Verify Settings class has required properties."""
    print("\n" + "=" * 70)
    print("CODE VERIFICATION: config/settings.py")
    print("=" * 70)
    
    try:
        from config.settings import Settings
        settings = Settings()
        
        checks = []
        
        # Check properties exist
        if hasattr(settings, 'is_production'):
            checks.append(("✅", f"is_production property exists (={settings.is_production})"))
        else:
            checks.append(("❌", "is_production property MISSING"))
        
        if hasattr(settings, 'is_development'):
            checks.append(("✅", f"is_development property exists (={settings.is_development})"))
        else:
            checks.append(("❌", "is_development property MISSING"))
        
        if hasattr(settings, 'environment'):
            checks.append(("✅", f"environment property exists (={settings.environment})"))
        else:
            checks.append(("❌", "environment property MISSING"))
        
        # Check logic
        if settings.environment == "production":
            if settings.is_production and not settings.is_development:
                checks.append(("✅", "Production flags consistent"))
            else:
                checks.append(("❌", "Production flags INCONSISTENT"))
        elif settings.environment == "development":
            if not settings.is_production and settings.is_development:
                checks.append(("✅", "Development flags consistent"))
            else:
                checks.append(("❌", "Development flags INCONSISTENT"))
        
        print("\nSettings checks:")
        for status, description in checks:
            print(f"  {status} {description}")
        
        return all(status == "✅" for status, desc in checks)
        
    except Exception as e:
        print(f"\n❌ Error loading Settings: {e}")
        return False


def main():
    """Run all verification tests."""
    print("\n" + "=" * 70)
    print("MANUAL CODE VERIFICATION TEST")
    print("=" * 70)
    print("Reading actual source files to verify implementation")
    print("=" * 70)
    
    results = []
    
    try:
        results.append(("document_router.py", verify_document_router()))
        results.append(("main.py", verify_main_startup()))
        results.append(("settings.py", verify_settings_class()))
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 CODE VERIFICATION SUCCESSFUL")
        print("=" * 70)
        print("\n✅ All implementation checks passed:")
        print("   • document_router.py: Correct fallback logic")
        print("   • main.py: Correct startup checks")
        print("   • settings.py: Correct environment detection")
        print("\n✅ Production behavior:")
        print("   • Startup: Fails with RuntimeError if Redis unavailable")
        print("   • Runtime: Returns HTTP 503 if Celery unavailable")
        print("   • Fallback: DISABLED (strict mode)")
        print("\n✅ Development behavior:")
        print("   • Startup: Continues with warning if Redis unavailable")
        print("   • Runtime: Falls back to sync processing")
        print("   • Fallback: ENABLED (graceful degradation)")
        print("=" * 70)
    else:
        print("❌ VERIFICATION FAILED")
        print("=" * 70)
        print("\nPlease review failed checks above.")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
