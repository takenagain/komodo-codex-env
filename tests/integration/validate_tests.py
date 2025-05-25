#!/usr/bin/env python3
"""Validation script to check integration test functionality."""

import sys
import traceback
from pathlib import Path

# Add the test directory to the path
sys.path.insert(0, str(Path(__file__).parent))

def validate_imports():
    """Validate that all test modules can be imported."""
    print("Validating imports...")
    
    try:
        from test_komodo_wallet_build import (
            SystemDependenciesTest,
            InstallationTest,
            EnvironmentSetupTest,
            AndroidEnvironmentTest,
            KomodoWalletBuildTest,
            FullPipelineIntegrationTest,
            setup_logging,
            docker_available
        )
        print("✓ All test classes imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"✗ Unexpected error during import: {e}")
        traceback.print_exc()
        return False

def validate_docker():
    """Validate Docker availability."""
    print("Validating Docker availability...")
    
    try:
        from test_komodo_wallet_build import docker_available
        if docker_available():
            print("✓ Docker is available")
            return True
        else:
            print("✗ Docker is not available")
            return False
    except Exception as e:
        print(f"✗ Error checking Docker: {e}")
        return False

def validate_dependencies():
    """Validate required dependencies."""
    print("Validating dependencies...")
    
    missing_deps = []
    
    try:
        import rich
        print("✓ rich is available")
    except ImportError:
        missing_deps.append("rich")
        print("✗ rich is not available")
    
    try:
        import requests
        print("✓ requests is available")
    except ImportError:
        missing_deps.append("requests")
        print("✗ requests is not available")
    
    if missing_deps:
        print(f"Missing dependencies: {missing_deps}")
        print("Install with: pip install " + " ".join(missing_deps))
        return False
    
    return True

def validate_test_structure():
    """Validate test class structure."""
    print("Validating test structure...")
    
    try:
        from test_komodo_wallet_build import (
            SystemDependenciesTest,
            InstallationTest,
            EnvironmentSetupTest,
            AndroidEnvironmentTest,
            KomodoWalletBuildTest,
            FullPipelineIntegrationTest
        )
        
        import unittest
        
        test_classes = [
            SystemDependenciesTest,
            InstallationTest,
            EnvironmentSetupTest,
            AndroidEnvironmentTest,
            KomodoWalletBuildTest,
            FullPipelineIntegrationTest
        ]
        
        for test_class in test_classes:
            if not issubclass(test_class, unittest.TestCase):
                print(f"✗ {test_class.__name__} is not a proper TestCase")
                return False
            
            # Check for test methods
            test_methods = [method for method in dir(test_class) 
                          if method.startswith('test_') and callable(getattr(test_class, method))]
            
            if not test_methods:
                print(f"✗ {test_class.__name__} has no test methods")
                return False
            
            print(f"✓ {test_class.__name__} has {len(test_methods)} test methods")
        
        return True
        
    except Exception as e:
        print(f"✗ Error validating test structure: {e}")
        traceback.print_exc()
        return False

def validate_file_paths():
    """Validate required file paths exist."""
    print("Validating file paths...")
    
    required_files = [
        "../../.devcontainer/Dockerfile",
        "../../install.sh",
        "../..",  # PROJECT_ROOT
    ]
    
    current_dir = Path(__file__).parent
    all_exist = True
    
    for file_path in required_files:
        full_path = current_dir / file_path
        if full_path.exists():
            print(f"✓ {file_path} exists")
        else:
            print(f"✗ {file_path} does not exist")
            all_exist = False
    
    return all_exist

def main():
    """Run all validations."""
    print("=" * 60)
    print("Komodo Wallet Integration Tests Validation")
    print("=" * 60)
    
    validations = [
        ("Dependencies", validate_dependencies),
        ("Imports", validate_imports),
        ("Docker", validate_docker),
        ("Test Structure", validate_test_structure),
        ("File Paths", validate_file_paths),
    ]
    
    results = []
    
    for name, validation_func in validations:
        print(f"\n--- {name} ---")
        try:
            result = validation_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ {name} validation failed with exception: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {name}: {status}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("✓ All validations passed! Tests are ready to run.")
        return 0
    else:
        print("✗ Some validations failed. Please address the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())