#!/usr/bin/env python3
"""Test runner for Komodo Wallet integration tests.

This script allows running specific test suites or all tests with proper logging configuration.
"""

import argparse
import logging
import os
import sys
import unittest
from concurrent.futures import ProcessPoolExecutor, as_completed
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


def _run_test_by_name(test_name: str, verbosity: int, failfast: bool) -> bool:
    """Utility to run a single test by dotted name in a separate process."""
    # Each process must configure logging separately
    setup_logging(logging.INFO if verbosity > 1 else logging.WARNING)
    suite = unittest.defaultTestLoader.loadTestsFromName(test_name)
    runner = unittest.TextTestRunner(verbosity=verbosity, failfast=failfast)
    result = runner.run(suite)
    return result.wasSuccessful()


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
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel using multiple processes"
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=os.cpu_count() or 2,
        help="Number of worker processes for parallel mode"
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
    
    verbosity = 2 if args.verbose or args.debug else 1

    print(f"Running {args.suite} test suite...")
    print(f"Test classes: {[cls.__name__ for cls in selected_classes]}")
    print("-" * 60)

    if args.parallel:
        test_names = []
        for cls in selected_classes:
            for name in unittest.defaultTestLoader.getTestCaseNames(cls):
                test_names.append(f"{cls.__module__}.{cls.__name__}.{name}")

        results = []
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = [
                executor.submit(_run_test_by_name, tn, verbosity, args.failfast)
                for tn in test_names
            ]
            for future in as_completed(futures):
                results.append(future.result())

        success = all(results)
    else:
        suite = create_test_suite(selected_classes)
        runner = unittest.TextTestRunner(
            verbosity=verbosity,
            failfast=args.failfast
        )
        result = runner.run(suite)
        success = result.wasSuccessful()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

