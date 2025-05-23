# Scripts Directory

This directory contains standalone scripts and utilities for Android SDK installation and testing.

## Scripts Overview

### Android SDK Installation

- **`install_android_sdk.py`** - Standalone Python script for Android SDK installation
- **`install_android_sdk.sh`** - Shell wrapper script with user-friendly interface

### Testing Scripts

- **`test_android_install.py`** - Unit tests for Android SDK functionality
- **`test_integration.py`** - Integration tests for parallel Flutter and Android setup

## Usage

### Standalone Android SDK Installation

```bash
# Basic installation using Python script
./scripts/install_android_sdk.py

# Using shell wrapper (recommended)
./scripts/install_android_sdk.sh

# With options
./scripts/install_android_sdk.sh --skip-java --android-home /custom/path

# Show help
./scripts/install_android_sdk.sh --help
```

### Running Tests

```bash
# Run Android SDK unit tests
cd scripts && python test_android_install.py

# Run integration tests
cd scripts && python test_integration.py

# Run both from project root
python scripts/test_android_install.py
python scripts/test_integration.py
```

## Script Details

### install_android_sdk.py

Standalone Android SDK installer that can run independently of the main tool:

- Detects and installs Java JDK if needed
- Downloads Android SDK command-line tools
- Installs essential packages (platform-tools, build-tools, API levels)
- Configures environment variables
- Cross-platform support (Linux, macOS, Windows)

**Environment Variables:**
- `ANDROID_HOME` - Custom Android SDK directory
- `SKIP_JAVA_INSTALL` - Skip Java installation

### install_android_sdk.sh

User-friendly shell wrapper for the Python installer:

- Command-line argument parsing
- Disk space checking
- Python version detection
- Colored output and progress feedback

**Options:**
- `--skip-java` - Skip Java installation
- `--android-home DIR` - Set custom Android SDK directory
- `--help` - Show usage information

### test_android_install.py

Comprehensive unit tests for Android SDK functionality:

- Android SDK detection and verification
- Java version parsing
- Environment variable setup
- URL generation for different platforms
- Directory structure validation

### test_integration.py

Integration tests for parallel execution and workflow validation:

- Parallel vs sequential execution modes
- Platform filtering logic
- Configuration flag handling
- Error propagation and failure handling
- Mock-based testing for complex workflows

## Requirements

### For Android SDK Installation Scripts

- Python 3.11+
- Internet connectivity
- 5GB+ available disk space
- curl (for downloads)

### For Testing Scripts

- Python 3.11+
- Access to komodo_codex_env source code
- unittest.mock for mocking

## Examples

### Quick Android SDK Setup

```bash
# Navigate to scripts directory
cd scripts

# Run installation
./install_android_sdk.sh

# Verify installation
flutter doctor
```

### Development Testing

```bash
# Test Android SDK functionality
python scripts/test_android_install.py

# Test integration with main tool
python scripts/test_integration.py

# Run both tests
for test in scripts/test_*.py; do python "$test"; done
```

### Custom Installation

```bash
# Install to custom location
./scripts/install_android_sdk.sh --android-home /opt/android-sdk

# Skip Java if already installed
./scripts/install_android_sdk.sh --skip-java

# Environment variable approach
ANDROID_HOME=/custom/path ./scripts/install_android_sdk.py
```

## Troubleshooting

### Common Issues

1. **Permission errors**: Ensure write access to target directory
2. **Python not found**: Install Python 3.11+ or use full path
3. **Network issues**: Check internet connectivity and firewall
4. **Disk space**: Ensure 5GB+ available space

### Debug Mode

```bash
# Run with verbose output
./scripts/install_android_sdk.py --verbose

# Check test output
python scripts/test_android_install.py -v
```

For detailed troubleshooting, see `docs/android/ANDROID_SDK_GUIDE.md`.