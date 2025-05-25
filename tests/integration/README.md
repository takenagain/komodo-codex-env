# Integration Tests for Komodo Codex Environment

This directory contains comprehensive integration tests for the Komodo Codex Environment setup and Komodo Wallet APK build process.

## Overview

The integration tests verify the complete pipeline from environment setup to building a Flutter APK for the Komodo Wallet project. Tests are organized into focused suites that can be run independently or as a complete pipeline.

## Test Structure

### Test Classes

1. **SystemDependenciesTest** - Verifies system dependencies and user environment
2. **InstallationTest** - Tests the install.sh script execution and verification
3. **EnvironmentSetupTest** - Tests Komodo environment setup with Android support
4. **AndroidEnvironmentTest** - Tests Android SDK configuration and tools
5. **KomodoWalletBuildTest** - Tests the complete APK build process
6. **FullPipelineIntegrationTest** - End-to-end integration test

### Key Features

- **Docker-based isolation** - Each test runs in a clean Docker container
- **Proper user management** - Tests run as `testuser` (non-root) for realistic scenarios
- **Comprehensive logging** - Rich logging with different verbosity levels
- **Intermediate verifications** - Each major step is verified before proceeding
- **Robust error handling** - Clear error messages with debugging information
- **Resource management** - Proper container cleanup and resource allocation

## Prerequisites

### Required Dependencies

```bash
pip install rich requests
```

### Docker Requirements

- Docker must be installed and accessible
- Sufficient system resources (4GB RAM recommended for Android builds)
- Network access for downloading dependencies

## Usage

### Quick Start

Run all tests:
```bash
python tests/integration/test_komodo_wallet_build.py
```

### Using the Test Runner

The `run_tests.py` script provides more control over test execution:

```bash
# Run all tests
python tests/integration/run_tests.py --suite all --verbose

# Run only system dependency checks
python tests/integration/run_tests.py --suite system

# Run only installation tests
python tests/integration/run_tests.py --suite install

# Run environment setup tests
python tests/integration/run_tests.py --suite environment

# Run Android environment tests
python tests/integration/run_tests.py --suite android

# Run build tests only
python tests/integration/run_tests.py --suite build

# Run full pipeline integration test
python tests/integration/run_tests.py --suite full

# Enable debug logging
python tests/integration/run_tests.py --suite all --debug

# Stop on first failure
python tests/integration/run_tests.py --suite all --failfast
```

### Individual Test Execution

Run specific test classes:
```bash
python -m unittest tests.integration.test_komodo_wallet_build.SystemDependenciesTest
python -m unittest tests.integration.test_komodo_wallet_build.InstallationTest
python -m unittest tests.integration.test_komodo_wallet_build.EnvironmentSetupTest
```

## Test Configuration

### Android SDK Paths

The tests support multiple Android SDK installation locations:
- System-wide: `/opt/android-sdk-linux` (default from android_manager.py)
- User-specific: `/home/testuser/Android/Sdk` (fallback)

### Environment Variables

Key environment variables used:
- `ANDROID_HOME` - Android SDK installation directory
- `ANDROID_SDK_ROOT` - Android SDK root directory (same as ANDROID_HOME)
- `JAVA_HOME` - Java Development Kit installation

### Container Configuration

Docker containers are configured with:
- 4GB memory limit
- 2GB shared memory
- Privileged mode (required for Android SDK operations)
- 2-hour timeout for long builds

## Test Scenarios

### System Dependencies Test
- Verifies required system tools (git, curl, unzip, etc.)
- Tests user environment setup
- Validates sudo access and permissions

### Installation Test
- Tests install.sh script execution
- Verifies UV and FVM installation
- Checks Komodo environment directory creation

### Environment Setup Test
- Tests Komodo Codex Environment setup with Android support
- Verifies Android SDK installation
- Tests Flutter environment configuration with FVM

### Android Environment Test
- Tests Android environment variables
- Verifies Android tools accessibility (sdkmanager, adb)
- Tests Java installation for Android development

### Build Test
- Tests Komodo Wallet repository cloning
- Verifies Flutter dependencies installation
- Tests complete APK build process
- Verifies APK file creation

### Full Pipeline Test
- Runs complete end-to-end pipeline
- Tests all components in sequence
- Provides comprehensive integration verification

## Debugging

### Logging Levels

- **WARNING** (default) - Shows only warnings and errors
- **INFO** (`--verbose`) - Shows progress and status information
- **DEBUG** (`--debug`) - Shows detailed execution information

### Common Issues

1. **Docker not available**
   - Ensure Docker is installed and running
   - Check user permissions for Docker access

2. **Container startup failures**
   - Check available system resources
   - Verify Docker image builds successfully

3. **Android SDK installation failures**
   - Check network connectivity
   - Verify sufficient disk space
   - Check Java installation

4. **APK build failures**
   - Review Flutter and Android environment setup
   - Check dependency installation logs
   - Verify Android SDK tools accessibility

### Debugging Commands

Check container logs:
```bash
docker logs <container_id>
```

Connect to running container:
```bash
docker exec -it <container_id> bash
```

Check environment variables:
```bash
docker exec <container_id> env
```

## Performance Considerations

### Timeouts

Default timeouts are set conservatively:
- Install script: 20 minutes
- Environment setup: 30 minutes
- APK build: 30 minutes

### Resource Usage

Tests require significant resources:
- Memory: 4GB+ recommended
- Disk: 10GB+ for Android SDK and dependencies
- Network: High bandwidth for dependency downloads

### Optimization Tips

1. **Parallel execution** - Use `--suite` to run only required tests
2. **Docker layer caching** - Rebuild images only when necessary
3. **Container reuse** - Consider keeping containers for debugging
4. **Network caching** - Use local mirrors for dependencies if available

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install rich requests
      - name: Run integration tests
        run: |
          python tests/integration/run_tests.py --suite all --verbose --failfast
```

### Docker Compose Example

```yaml
version: '3.8'
services:
  test:
    build:
      context: .
      dockerfile: .devcontainer/Dockerfile
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - DOCKER_BUILDKIT=1
    command: python tests/integration/run_tests.py --suite all --verbose
```

## Contributing

### Adding New Tests

1. Extend appropriate test class or create new one
2. Follow naming convention: `test_<functionality>`
3. Add proper logging and error handling
4. Update test runner configuration if needed

### Test Guidelines

- Use descriptive test names and docstrings
- Implement proper cleanup in tearDown methods
- Add intermediate verification steps
- Use appropriate timeouts for operations
- Include debugging information in failure messages

### Code Style

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Add comprehensive docstrings
- Include error handling and logging