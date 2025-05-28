#!/usr/bin/env python3
"""
Test Runner Helper Script for Komodo Codex Environment

This script provides convenient commands for running different types of tests
with proper configuration and reporting.
"""

import argparse
import subprocess
import sys
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=cwd, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}")
        return False

def run_unit_tests(verbose=False, parallel=False):
    """Run unit tests only."""
    cmd = ["rye", "run", "pytest", "tests/unit/"]
    
    if verbose:
        cmd.append("-v")
    
    if parallel:
        cmd.extend(["-n", "auto"])
    
    cmd.extend(["--tb=short"])
    return run_command(cmd)

def run_integration_tests(verbose=False, timeout=3600):
    """Run integration tests with Docker."""
    cmd = ["rye", "run", "pytest", "tests/integration/"]
    
    if verbose:
        cmd.append("-v")
    
    cmd.extend(["--tb=short", f"--timeout={timeout}"])
    return run_command(cmd)

def run_all_tests(verbose=False, parallel=False):
    """Run all tests."""
    cmd = ["rye", "run", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    if parallel:
        cmd.extend(["-n", "auto"])
    
    cmd.extend(["--tb=short"])
    return run_command(cmd)

def run_specific_test(test_path, verbose=False):
    """Run a specific test file or test method."""
    cmd = ["rye", "run", "pytest", test_path]
    
    if verbose:
        cmd.append("-v")
    
    cmd.extend(["--tb=short"])
    return run_command(cmd)

def check_test_coverage():
    """Run tests with coverage reporting."""
    try:
        # Try to install coverage if not available
        subprocess.run(["rye", "add", "--dev", "pytest-cov"], check=False, capture_output=True)
        
        cmd = [
            "rye", "run", "pytest", 
            "--cov=src/komodo_codex_env", 
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "tests/unit/"
        ]
        return run_command(cmd)
    except Exception as e:
        print(f"Coverage check failed: {e}")
        return False

def lint_and_test():
    """Run linting and then tests."""
    print("Running linting checks...")
    
    # Try to run basic Python syntax checks
    try:
        cmd = ["python", "-m", "py_compile"]
        src_files = list(Path("src").rglob("*.py"))
        test_files = list(Path("tests").rglob("*.py"))
        
        for py_file in src_files + test_files:
            result = subprocess.run([*cmd, str(py_file)], capture_output=True)
            if result.returncode != 0:
                print(f"Syntax error in {py_file}")
                return False
        
        print("✓ Syntax checks passed")
    except Exception as e:
        print(f"Linting check failed: {e}")
    
    print("Running tests...")
    return run_unit_tests(verbose=True)

def main():
    parser = argparse.ArgumentParser(
        description="Test runner for Komodo Codex Environment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_tests.py unit                    # Run unit tests
  python scripts/run_tests.py unit --verbose          # Run unit tests with verbose output
  python scripts/run_tests.py unit --parallel         # Run unit tests in parallel
  python scripts/run_tests.py integration             # Run integration tests
  python scripts/run_tests.py all                     # Run all tests
  python scripts/run_tests.py specific tests/unit/test_setup.py  # Run specific test
  python scripts/run_tests.py coverage                # Run with coverage
  python scripts/run_tests.py lint                    # Run linting and tests
        """
    )
    
    parser.add_argument(
        "test_type",
        choices=["unit", "integration", "all", "specific", "coverage", "lint"],
        help="Type of tests to run"
    )
    
    parser.add_argument(
        "test_path",
        nargs="?",
        help="Specific test path (required for 'specific' test type)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Run tests with verbose output"
    )
    
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Run tests in parallel (unit tests only)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=3600,
        help="Timeout for integration tests in seconds (default: 3600)"
    )
    
    args = parser.parse_args()
    
    # Change to project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    print(f"Running tests from: {project_root}")
    
    success = False
    
    if args.test_type == "unit":
        success = run_unit_tests(verbose=args.verbose, parallel=args.parallel)
    elif args.test_type == "integration":
        success = run_integration_tests(verbose=args.verbose, timeout=args.timeout)
    elif args.test_type == "all":
        success = run_all_tests(verbose=args.verbose, parallel=args.parallel)
    elif args.test_type == "specific":
        if not args.test_path:
            print("Error: test_path is required for specific test type")
            sys.exit(1)
        success = run_specific_test(args.test_path, verbose=args.verbose)
    elif args.test_type == "coverage":
        success = check_test_coverage()
    elif args.test_type == "lint":
        success = lint_and_test()
    
    if success:
        print("\n✅ Tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()