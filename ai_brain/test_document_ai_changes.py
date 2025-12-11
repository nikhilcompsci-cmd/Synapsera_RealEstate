"""Test runner for Document AI changes."""
import subprocess
import sys
from pathlib import Path


def run_tests():
    """Run all tests for Document AI integration."""
    print("=" * 80)
    print("Testing Document AI Integration")
    print("=" * 80)
    
    # Change to ai_brain directory
    ai_brain_dir = Path(__file__).parent
    
    test_commands = [
        {
            "name": "Unit Tests - DocumentAIService",
            "cmd": [
                sys.executable, "-m", "pytest",
                "tests/unit/test_document_ai_service.py",
                "-v", "--tb=short"
            ]
        },
        {
            "name": "Unit Tests - PDFExtractor Document AI Integration",
            "cmd": [
                sys.executable, "-m", "pytest",
                "tests/unit/test_pdf_extractor_document_ai.py",
                "-v", "--tb=short"
            ]
        },
        {
            "name": "Integration Tests - Document AI Workflow",
            "cmd": [
                sys.executable, "-m", "pytest",
                "tests/integration/test_document_ai_integration.py",
                "-v", "--tb=short"
            ]
        },
        {
            "name": "All Document AI Tests",
            "cmd": [
                sys.executable, "-m", "pytest",
                "tests/",
                "-v", "--tb=short",
                "-k", "document_ai or DocumentAI"
            ]
        }
    ]
    
    results = {}
    
    for test in test_commands:
        print("\n" + "=" * 80)
        print(f"Running: {test['name']}")
        print("=" * 80)
        
        try:
            result = subprocess.run(
                test["cmd"],
                cwd=ai_brain_dir,
                capture_output=True,
                text=True
            )
            
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            
            results[test['name']] = {
                "passed": result.returncode == 0,
                "returncode": result.returncode
            }
            
        except Exception as e:
            print(f"Error running {test['name']}: {e}")
            results[test['name']] = {"passed": False, "error": str(e)}
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for name, result in results.items():
        status = "✅ PASSED" if result.get("passed") else "❌ FAILED"
        print(f"{status} - {name}")
        if not result.get("passed") and "error" in result:
            print(f"  Error: {result['error']}")
    
    # Overall result
    all_passed = all(r.get("passed", False) for r in results.values())
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 80)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(run_tests())
