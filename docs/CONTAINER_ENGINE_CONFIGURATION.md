# Container Engine Configuration

This document describes how to configure and use different container engines (Docker and Podman) with the Komodo Codex Environment integration tests.

## Overview

The integration tests have been designed to work with both Docker and Podman container engines through a unified abstraction layer. This allows for greater flexibility in different environments and systems where one container engine might be preferred over another.

## Supported Container Engines

### Docker
- **Default choice**: Docker is the default container engine if available
- **Compatibility**: Fully supported with all integration tests
- **Installation**: Follow [Docker installation guide](https://docs.docker.com/get-docker/)

### Podman
- **Alternative option**: Podman can be used as a drop-in replacement for Docker
- **Compatibility**: Fully supported with automatic command adjustments
- **Installation**: Follow [Podman installation guide](https://podman.io/getting-started/installation)

## Configuration Methods

### Method 1: Environment Variable (Recommended)

Set the `CONTAINER_ENGINE` environment variable to specify which engine to use:

```bash
# Use Docker explicitly
export CONTAINER_ENGINE=docker
python scripts/run_tests.py integration

# Use Podman explicitly  
export CONTAINER_ENGINE=podman
python scripts/run_tests.py integration
```

### Method 2: Auto-Detection (Default)

If no `CONTAINER_ENGINE` environment variable is set, the system will automatically detect available container engines in this order:

1. **Docker** - Checked first as it's the most common
2. **Podman** - Used as fallback if Docker is not available

```bash
# Auto-detect available container engine
python scripts/run_tests.py integration
```

### Method 3: Per-Test Configuration

For advanced use cases, you can configure the container engine programmatically:

```python
from tests.integration.container_engine import ContainerEngine

# Explicit engine selection
engine = ContainerEngine(engine='podman')

# Auto-detection
engine = ContainerEngine()
```

## Environment Setup Examples

### Using Docker

```bash
# Ensure Docker is running
sudo systemctl start docker

# Run integration tests with Docker
export CONTAINER_ENGINE=docker
python scripts/run_tests.py integration --verbose
```

### Using Podman

```bash
# Ensure Podman is available
podman version

# Run integration tests with Podman
export CONTAINER_ENGINE=podman
python scripts/run_tests.py integration --verbose
```

### CI/CD Configuration

#### GitHub Actions with Docker
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
      - name: Run integration tests with Docker
        env:
          CONTAINER_ENGINE: docker
          ENABLE_INTEGRATION_TESTS: true
        run: |
          rye run pytest tests/integration/ -v
```

#### GitHub Actions with Podman
```yaml
name: Integration Tests (Podman)
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install Podman
        run: |
          sudo apt-get update
          sudo apt-get install -y podman
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install rye
          rye sync
      - name: Run integration tests with Podman
        env:
          CONTAINER_ENGINE: podman
          ENABLE_INTEGRATION_TESTS: true
        run: |
          rye run pytest tests/integration/ -v
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Container Engine Not Found
```
ContainerEngineError: Container engine 'docker' is not available
```

**Solutions:**
- Install the specified container engine
- Use auto-detection: `unset CONTAINER_ENGINE`
- Switch to an available engine: `export CONTAINER_ENGINE=podman`

#### 2. Permission Issues with Docker
```
docker: permission denied while trying to connect to the Docker daemon socket
```

**Solutions:**
- Add user to docker group: `sudo usermod -aG docker $USER`
- Use sudo: `sudo python scripts/run_tests.py integration`
- Switch to Podman (rootless): `export CONTAINER_ENGINE=podman`

#### 3. Podman Socket Issues
```
Error: unable to connect to Podman socket
```

**Solutions:**
- Start Podman socket: `systemctl --user start podman.socket`
- Use Podman in rootless mode
- Check Podman configuration: `podman info`

#### 4. Container Build Failures

**For Docker:**
```bash
# Check Docker daemon status
sudo systemctl status docker

# Clean Docker cache
docker system prune -a
```

**For Podman:**
```bash
# Check Podman status
podman info

# Clean Podman cache
podman system prune -a
```

### Debugging Container Issues

#### 1. Enable Verbose Logging
```bash
export CONTAINER_ENGINE=podman
python scripts/run_tests.py integration --verbose
```

#### 2. Check Container Engine Status
```python
from tests.integration.container_engine import ContainerEngine

engine = ContainerEngine()
print(f"Using engine: {engine.engine}")
print(f"Version: {engine.version()}")
print(f"Available: {engine.is_available()}")
```

#### 3. Manual Container Operations
```bash
# Test container engine manually
docker version    # or: podman version
docker run hello-world    # or: podman run hello-world
```

## Advanced Configuration

### Custom Container Arguments

The container engine abstraction supports custom arguments for specific use cases:

```python
# Example: Custom security settings for Podman
engine = ContainerEngine(engine='podman')
result = engine.run(
    image='test-image',
    extra_args=['--security-opt', 'seccomp=unconfined'],
    detach=True
)
```

### Engine-Specific Optimizations

The abstraction layer automatically applies engine-specific optimizations:

- **Podman**: Rootless container support, different security contexts
- **Docker**: Traditional privileged container handling

### Container Resource Configuration

```bash
# Increase container memory limits for large builds
export CONTAINER_MEMORY=8g
export CONTAINER_CPUS=4
```

## Best Practices

### 1. Consistent Environment
- Use the same container engine across your development team
- Document the preferred engine in your project README
- Set up CI/CD to test with both engines if possible

### 2. Security Considerations
- **Podman**: Preferred for rootless containers and enhanced security
- **Docker**: Ensure proper user permissions and group membership

### 3. Performance Optimization
- Use local image caching to speed up repeated builds
- Consider using multi-stage builds for smaller images
- Clean up unused containers and images regularly

### 4. Development Workflow
```bash
# Development script example
#!/bin/bash
set -e

# Auto-detect or use preferred engine
export CONTAINER_ENGINE=${CONTAINER_ENGINE:-docker}

echo "Using container engine: $CONTAINER_ENGINE"

# Run tests
python scripts/run_tests.py integration --verbose

# Cleanup
$CONTAINER_ENGINE system prune -f
```

## Migration Guide

### From Docker-only to Multi-Engine Support

If you're migrating from a Docker-only setup:

1. **No changes needed** - existing Docker workflows continue to work
2. **Optional**: Set `CONTAINER_ENGINE=docker` explicitly
3. **Test**: Try Podman as alternative: `CONTAINER_ENGINE=podman`

### Testing Both Engines

```bash
# Test with Docker
export CONTAINER_ENGINE=docker
python scripts/run_tests.py integration

# Test with Podman  
export CONTAINER_ENGINE=podman
python scripts/run_tests.py integration

# Auto-detection test
unset CONTAINER_ENGINE
python scripts/run_tests.py integration
```

## Integration Test Compatibility

All integration tests support both container engines:

- `test_flutter_only_integration.py` - ✅ Docker & Podman
- `test_flutter_android_integration.py` - ✅ Docker & Podman  
- `test_kdf_rust_integration.py` - ✅ Docker & Podman
- `test_kdf_sdk_integration.py` - ✅ Docker & Podman

## Support and Contributing

### Reporting Issues

When reporting container engine related issues, please include:

1. Container engine type and version
2. Operating system and version
3. Full error message and stack trace
4. Steps to reproduce the issue

### Contributing

To contribute container engine improvements:

1. Test changes with both Docker and Podman
2. Update this documentation if adding new features
3. Ensure backward compatibility with existing workflows
4. Add appropriate error handling and logging

## Related Documentation

- [Integration Tests README](../tests/integration/README.md)
- [Project Structure](PROJECT_STRUCTURE.md)
- [Docker Official Documentation](https://docs.docker.com/)
- [Podman Official Documentation](https://podman.io/docs)