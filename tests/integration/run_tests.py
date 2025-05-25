#!/usr/bin/env python3
"""Test runner for Komodo Wallet integration tests.

This script allows running specific test suites or all tests with proper logging configuration.
"""

import argparse
import logging
import sys
import unittest
from pathlib import Path

# Add the test directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from test_komodo_wallet_build import (
    SystemDependenciesTest,
    InstallationTest,
    EnvironmentSetupTest,
    AndroidEnvironmentTest,
    KomodoWalletBuildTest,
    FullPipelineIntegrationTest,
    setup_logging
)


def create_test_suite(test_classes):
    """Create a test suite from the given test classes."""
    suite = unittest.TestSuite()
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    return suite


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run Komodo Wallet integration tests")
    parser.add_argument(
        "--suite",
        choices=[
            "system",
            "install", 
            "environment",
            "android",
            "build",
            "full",
            "all"
        ],
        default="all",
        help="Test suite to run"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true", 
        help="Enable debug logging"
    )
    parser.add_argument(
        "--failfast", "-f",
        action="store_true",
        help="Stop on first failure"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    if args.debug:
        setup_logging(logging.DEBUG)
    elif args.verbose:
        setup_logging(logging.INFO)
    else:
        setup_logging(logging.WARNING)
    
    # Define test suites
    test_suites = {
        "system": [SystemDependenciesTest],
        "install": [InstallationTest],
        "environment": [EnvironmentSetupTest],
        "android": [AndroidEnvironmentTest],
        "build": [KomodoWalletBuildTest],
        "full": [FullPipelineIntegrationTest],
        "all": [
            SystemDependenciesTest,
            InstallationTest,
            EnvironmentSetupTest,
            AndroidEnvironmentTest,
            KomodoWalletBuildTest,
            FullPipelineIntegrationTest
        ]
    }
    
    # Get selected test classes
    selected_classes = test_suites.get(args.suite, test_suites["all"])
    
    # Create and run test suite
    suite = create_test_suite(selected_classes)
    runner = unittest.TextTestRunner(
        verbosity=2 if args.verbose or args.debug else 1,
        failfast=args.failfast
    )
    
    print(f"Running {args.suite} test suite...")
    print(f"Test classes: {[cls.__name__ for cls in selected_classes]}")
    print("-" * 60)
    
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()