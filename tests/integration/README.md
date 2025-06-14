# Integration Tests for Komodo Codex Environment

This directory contains streamlined integration tests for the Komodo Codex Environment setup and Flutter development workflow.

## Overview

The integration tests verify the complete pipeline from environment setup to building Flutter applications. Tests are organized into focused suites that can be run independently or together.

## Test Structure

### Container-Based Integration Tests

1. **test_flutter_only_integration.py** - Tests Flutter development without Android SDK
2. **test_flutter_android_integration.py** - Tests Flutter development with Android SDK
3. **test_kdf_rust_integration.py** - Tests KDF dependencies and Rust toolchain
4. **test_kdf_sdk_integration.py** - Tests KDF-SDK install type and melos setup

### Unit Tests (Fast)

4. **test_android_fvm_paths.py** - Tests Android SDK and FVM path detection logic
5. **test_android_manager.py** - Tests Android manager functionality
6. **test_setup.py** - Tests setup configuration and mocking
7. **test_docs_location.py** - Tests documentation fetching behavior

### Key Features

- **Container-based isolation** - Each test runs in a clean container (Docker or Podman)
- **Multi-engine support** - Works with both Docker and Podman container engines
- **Proper user management** - Tests run as `testuser` (non-root) for realistic scenarios
- **Comprehensive logging** - Rich logging with different verbosity levels
- **End-to-end verification** - Each test creates and builds a Flutter application
- **Robust error handling** - Clear error messages with debugging information
- **Resource management** - Proper container cleanup and resource allocation

## Prerequisites

### Required Dependencies

```bash
pip install rich requests
```

### Container Engine Requirements

- Either Docker or Podman must be installed and accessible
- Network access for downloading dependencies
- See [Container Engine Configuration](../../docs/CONTAINER_ENGINE_CONFIGURATION.md) for detailed setup

#### Container Engine Selection

The tests support both Docker and Podman. You can specify which engine to use:

```bash
# Use Docker (default if available)
export CONTAINER_ENGINE=docker

# Use Podman
export CONTAINER_ENGINE=podman

# Auto-detect (tries Docker first, then Podman)
unset CONTAINER_ENGINE
```

## Usage

### Quick Start

Run all tests:
```bash
rye run pytest tests/integration/
```

Run with parallel execution:
```bash
rye run pytest tests/integration/ -n 4
```

### Individual Test Execution

Run specific tests:
```bash
# Flutter-only test
rye run pytest tests/integration/test_flutter_only_integration.py -v

# Flutter + Android test
rye run pytest tests/integration/test_flutter_android_integration.py -v

# Fast unit tests only
rye run pytest tests/integration/test_setup.py tests/integration/test_docs_location.py -v
```

## Test Scenarios

### Flutter-Only Integration Test
- Runs install.sh script
- Sets up Flutter environment with FVM (platforms: web,linux)
- Verifies FVM installation and functionality
- Creates a simple Flutter application
- Builds application for web platform
- Verifies build artifacts

### Flutter + Android Integration Test
- Runs install.sh script
- Sets up Flutter environment with FVM + Android SDK (platforms: web,android,linux)
- Verifies FVM and Android SDK installation
- Creates a simple Flutter application with Android support
- Builds APK for Android platform
- Verifies APK creation and Flutter doctor Android detection

### KDF Rust Integration Test
- Runs install.sh script with `--install-type KDF`
- Installs Komodo DeFi Framework dependencies
- Verifies Rust toolchain installation
- Creates a simple Cargo project
- Builds the project to ensure compilation succeeds

### KDF-SDK Integration Test
- Runs install.sh script with `--install-type KDF-SDK`
- Executes the setup command
- Verifies that the `melos` tool is installed

### Setup Configuration Test
- Tests parallel vs sequential setup execution
- Tests Android SDK configuration options
- Tests platform selection logic
- Uses mocking for fast execution

### Documentation Location Test
- Tests documentation fetching to different target directories
- Verifies file creation behavior
- Non-Docker based for speed

## Test Configuration

### Android SDK Paths

The tests support multiple Android SDK installation locations:
- System-wide: `/opt/android-sdk` (default from android_manager.py)
- User-specific: `/home/testuser/Android/Sdk` (fallback)

### Environment Variables

Key environment variables used:
- `ANDROID_HOME` - Android SDK installation directory
- `ANDROID_SDK_ROOT` - Android SDK root directory (same as ANDROID_HOME)
- `JAVA_HOME` - Java Development Kit installation

### Container Configuration

Containers (Docker/Podman) are configured with:
- 1-2 hour timeout for builds
- Temporary filesystem mounts for performance optimization
- Proper user permission setup
- Engine-specific optimizations (rootless for Podman, privileged for Docker when needed)

## Debugging

### Logging Levels

Tests use Rich logging for clear output:
- **INFO** (default) - Shows progress and status information
- **DEBUG** - Shows detailed execution information (via pytest -v)

### Common Issues

1. **Container engine not available**
   - Ensure Docker or Podman is installed and running
   - Check user permissions for container engine access
   - Try switching engines: `export CONTAINER_ENGINE=podman` or `export CONTAINER_ENGINE=docker`

2. **Container startup failures**
   - Check available system resources
   - Verify container image builds successfully
   - Try cleaning container cache: `docker system prune` or `podman system prune`

3. **Android SDK installation failures**
   - Check network connectivity
   - Verify sufficient disk space
   - Check Java installation

4. **Flutter build failures**
   - Review Flutter and Android environment setup
   - Check dependency installation logs
   - Verify Android SDK tools accessibility

### Debugging Commands

Check container logs:
```bash
# Docker
docker logs <container_id>
# Podman
podman logs <container_id>
```

Connect to running container:
```bash
# Docker
docker exec -it <container_id> bash
# Podman
podman exec -it <container_id> bash
```

Check environment variables:
```bash
# Docker
docker exec <container_id> env
# Podman
podman exec <container_id> env
```

Check which container engine is being used:
```bash
echo $CONTAINER_ENGINE  # Shows configured engine
# or let the system auto-detect and show you:
python -c "from tests.integration.container_engine import ContainerEngine; print(ContainerEngine().engine)"
```

## Performance Considerations

### Timeouts

Default timeouts are set for different operations:
- Install script: 15 minutes
- Flutter-only setup: 20 minutes
- Flutter + Android setup: 40 minutes
- APK build: 30 minutes

### Resource Usage

Tests may require significant resources:
- Disk: Sufficient space for Android SDK and dependencies (~8GB)
- Network: High bandwidth for dependency downloads
- Memory: 4GB+ recommended for Android builds

### Optimization Tips

1. **Parallel execution** - Use `pytest -n <workers>` for concurrent test execution
2. **Selective testing** - Run only the tests you need during development
3. **Container layer caching** - Container images are cached between runs
4. **Container reuse** - Consider keeping containers for debugging
5. **Engine selection** - Choose the most suitable engine for your environment:
   - **Docker**: Traditional, widely supported
   - **Podman**: Rootless, more secure, good for rootless environments

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
          pip install rye
          rye sync
      - name: Run integration tests
        run: |
          rye run pytest tests/integration/ -v --tb=short
```

### Expected Runtime

- **Flutter-only test**: ~8-12 minutes
- **Flutter + Android test**: ~15-25 minutes
- **KDF Rust test**: ~5-10 minutes
- **KDF-SDK test**: ~10-20 minutes
- **Unit tests**: ~30 seconds
- **Total runtime**: ~10-15 minutes (sequential), ~8-10 minutes (parallel)

## Test Status

### Current Status (Latest Update)

- **Unit Tests**: ✅ 37 tests passing
- **Integration Tests**: ⚠️ Properly skipped in non-Docker environments
- **Total Coverage**: All core functionality tested
- **CI Ready**: Tests configured for automated execution

### Recent Fixes Applied

1. **Android SDK Path Consistency**: Fixed mismatched default paths between config and manager
2. **Permission Handling**: Added accessibility checks for FVM installation paths
3. **Pytest Configuration**: Added comprehensive test configuration with async settings
4. **Container Engine Support**: Added Docker and Podman support with automatic detection
5. **Docker Environment**: Improved container setup with proper user permissions
6. **Error Handling**: Enhanced robustness with graceful fallbacks and skip conditions

### Test Execution

```bash
# Run all tests
rye run pytest

# Run only unit tests (fast)
rye run pytest tests/unit/

# Run with verbose output
rye run pytest -v

# Run with parallel execution
rye run pytest -n 4
```

## Contributing

### Adding New Tests

1. Follow the established patterns in existing test files
2. Use descriptive test names and docstrings
3. Add proper logging and error handling
4. Include verification steps for all major functionality

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
</edits>