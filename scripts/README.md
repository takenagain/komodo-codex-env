# Scripts Directory

This directory contains utilities for development environment setup, testing, and verification.

## Scripts Overview

### Available Scripts

- **`run_tests.py`** - Test runner helper script for development
- **`setup_dev_env.sh`** - Development environment setup using Rye
- **`verify_fvm.py`** - FVM installation verification script



## Usage

### Development Environment Setup

```bash
# Set up Python development environment using Rye
./scripts/setup_dev_env.sh

# This will:
# - Install/update dependencies with Rye
# - Check system dependencies
# - Set up the development environment
```

### Running Tests

```bash
# Run tests using the test runner
python scripts/run_tests.py unit

# Run with verbose output
python scripts/run_tests.py unit --verbose

# Run all tests
python scripts/run_tests.py all
```

## Script Details

### run_tests.py

Test runner helper script providing convenient commands for running different types of tests:

- Unit test execution with optional parallelization
- Integration test execution with Docker
- Coverage reporting and analysis
- Linting and syntax checking
- Specific test file execution

### verify_fvm.py

FVM (Flutter Version Management) installation verification script:

- Checks FVM availability for multiple users
- Verifies PATH configuration in shell profiles
- Lists installed Flutter versions via FVM
- Validates FVM command functionality
- Cross-platform verification support

## Requirements

### For Development Scripts

- Python 3.11+
- Rye package manager (for setup_dev_env.sh)
- Access to komodo_codex_env source code
- pytest for testing (installed via Rye)

## Examples

### Development Workflow

```bash
# Set up development environment
./scripts/setup_dev_env.sh

# Run unit tests
python scripts/run_tests.py unit

# Run integration tests
python scripts/run_tests.py integration

# Generate test coverage report
python scripts/run_tests.py coverage

# Verify FVM installation
python scripts/verify_fvm.py
```
</edits>



## Troubleshooting

### Common Issues

1. **Python not found**: Install Python 3.11+ or use full path
2. **Rye not installed**: Install Rye package manager for setup_dev_env.sh
3. **FVM not found**: Run verify_fvm.py to check installation status
4. **Test failures**: Use run_tests.py with verbose output for debugging

### Debug Mode

```bash
# Run tests with verbose output
python scripts/run_tests.py unit --verbose

# Verify FVM installation
python scripts/verify_fvm.py

# Set up development environment
./scripts/setup_dev_env.sh
```

For main tool troubleshooting, see the primary documentation in `docs/`.