# Komodo Codex Environment Setup

A Python-based replacement for the original bash script to set up Flutter development environment for Komodo Wallet using FVM (Flutter Version Management).

## Features

- **FVM Integration**: Uses Flutter Version Management for better Flutter version control
- **Android SDK Management**: Automated Android SDK installation and configuration for APK building
- **Parallel Execution**: Efficient dependency management with job scheduling for Flutter and Android SDK setup
- **Modular Architecture**: Clean separation of concerns with dedicated managers for different components
- **Cross-Platform**: Supports macOS (brew), Linux (apt/pacman), and other Unix-like systems
- **Rich Console Output**: Beautiful progress bars and colored output
- **Async Documentation**: Fast concurrent documentation fetching
- **Type Safety**: Full type hints and modern Python practices
- **Version Switching**: Easy Flutter version management via FVM

## Quick Start

### Prerequisites

- Python 3.11+ (Python 3.13 recommended)
- [Rye](https://rye.astral.sh/) package manager
- Git
- FVM (Flutter Version Management) - installed automatically
- Java 17+ (OpenJDK) - installed automatically for Android development

### One-Line Installation

```bash
# Quick install with all dependencies and FVM setup
curl -fsSL https://raw.githubusercontent.com/KomodoPlatform/komodo-codex-env/main/install.sh | bash

# Example with custom options
curl -fsSL https://raw.githubusercontent.com/KomodoPlatform/komodo-codex-env/main/install.sh | bash -s -- \
  --flutter-version stable \
  --platforms web,android \
  --install-type ALL
```

### Manual Installation

```bash
# Clone and setup
git clone <repository-url>
cd komodo-codex-env

# Install dependencies
rye sync

# Run the setup with FVM
PYTHONPATH=src rye run python -m komodo_codex_env.cli setup --verbose
```

## Project Structure

```
komodo-codex-env/
├── src/komodo_codex_env/           # Main Python package
│   ├── android_manager.py          # Android SDK management
│   ├── flutter_manager.py          # Flutter/FVM management
│   ├── setup.py                    # Main orchestrator
│   ├── cli.py                      # Command-line interface
│   └── ...                         # Other core modules
├── scripts/                        # Standalone scripts and utilities
│   ├── run_tests.py                # Test runner helper script
│   ├── setup_dev_env.sh            # Development environment setup
│   ├── verify_fvm.py               # FVM verification script
│   └── README.md                   # Scripts documentation
├── docs/                           # Documentation
│   ├── android/                    # Android-specific documentation
│   │   ├── ANDROID_SDK_GUIDE.md    # User guide for Android SDK
│   │   └── ANDROID_SDK_IMPLEMENTATION.md  # Technical details
│   └── README.md                   # Documentation index
├── README.md                       # This file
└── ...                             # Other project files
```

## Usage

### Main Setup Command

```bash
# Full environment setup with FVM
PYTHONPATH=src rye run python -m komodo_codex_env.cli setup

# Setup with custom Flutter version
PYTHONPATH=src rye run python -m komodo_codex_env.cli setup --flutter-version 3.29.3

# Setup with specific platforms (Android SDK auto-installed if android is included)
PYTHONPATH=src rye run python -m komodo_codex_env.cli setup --platforms web,android,linux

# Skip Android SDK installation
PYTHONPATH=src rye run python -m komodo_codex_env.cli setup --no-android

# Verbose output
PYTHONPATH=src rye run python -m komodo_codex_env.cli setup --verbose
```

### Individual Commands

```bash
# Check system dependencies
PYTHONPATH=src rye run python -m komodo_codex_env.cli check-deps

# Check Flutter status via FVM
PYTHONPATH=src rye run python -m komodo_codex_env.cli flutter-status

# Fetch documentation only
PYTHONPATH=src rye run python -m komodo_codex_env.cli fetch-docs

# FVM Flutter management
PYTHONPATH=src rye run python -m komodo_codex_env.cli fvm-list
PYTHONPATH=src rye run python -m komodo_codex_env.cli fvm-install 3.29.3
PYTHONPATH=src rye run python -m komodo_codex_env.cli fvm-use 3.29.3
PYTHONPATH=src rye run python -m komodo_codex_env.cli fvm-releases

# Android SDK management
PYTHONPATH=src rye run python -m komodo_codex_env.cli android-status
PYTHONPATH=src rye run python -m komodo_codex_env.cli android-install
PYTHONPATH=src rye run python -m komodo_codex_env.cli android-licenses

# Update script from remote
PYTHONPATH=src rye run python -m komodo_codex_env.cli update-script
```

## Configuration

The tool supports configuration via environment variables:

```bash
# Flutter version (FVM will manage the actual installation)
export FLUTTER_VERSION=stable

# Platform targets
export PLATFORMS=web,android,linux

# Android SDK options
export INSTALL_ANDROID_SDK=true

# Documentation options
export SHOULD_FETCH_KDF_API_DOCS=true
export SHOULD_FETCH_AGENTS_DOCS=true

# Execution options
export PARALLEL_EXECUTION=true
export MAX_PARALLEL_JOBS=4
```

## Architecture

- `config.py` - Configuration management
- `executor.py` - Parallel command execution
- `git_manager.py` - Git operations
- `dependency_manager.py` - System dependencies with platform-aware package mapping
- `flutter_manager.py` - Flutter SDK management via FVM
- `android_manager.py` - Android SDK installation and configuration
- `documentation_manager.py` - Documentation fetching
- `setup.py` - Main orchestrator with parallel Flutter and Android setup
- `cli.py` - Command-line interface with FVM and Android commands

### Scripts Directory

- `scripts/run_tests.py` - Test runner helper script for development
- `scripts/setup_dev_env.sh` - Development environment setup using Rye
- `scripts/verify_fvm.py` - FVM installation verification script

### Documentation

- `docs/android/ANDROID_SDK_GUIDE.md` - Comprehensive Android SDK usage guide
- `docs/android/ANDROID_SDK_IMPLEMENTATION.md` - Technical implementation details

## Advantages over Bash Script

1. **FVM Integration**: Professional Flutter version management instead of manual git clones
2. **Better Error Handling**: Structured exception handling vs complex bash conditionals
3. **Type Safety**: Full type hints and IDE support
4. **Platform Awareness**: Smart package mapping for different operating systems
5. **Modularity**: Clean separation of concerns
6. **Testability**: Each component can be unit tested
7. **Maintainability**: Object-oriented design with clear interfaces
8. **Performance**: Async operations and parallel execution
9. **User Experience**: Rich console output with progress indicators
10. **Version Control**: Easy switching between Flutter versions

## Development

```bash
# Install development dependencies
rye sync

# Run tests
rye run pytest

# Run integration tests with container engine support (Docker/Podman)
python scripts/run_tests.py integration

# Run tests with specific container engine
CONTAINER_ENGINE=docker python scripts/run_tests.py integration
CONTAINER_ENGINE=podman python scripts/run_tests.py integration

# Format code
rye run ruff format src/

# Type checking
rye run mypy src/

# Run the tool locally
PYTHONPATH=src rye run python -m komodo_codex_env.cli --help
```

## Migration from Bash Script

This Python implementation provides equivalent functionality to the original bash script with these improvements:

- **FVM Integration**: Professional Flutter version management replacing manual git operations
- **Platform Intelligence**: Smart package mapping for macOS, Linux, and other platforms
- **Replaced complex associative arrays**: Proper data structures and type safety
- **Converted string manipulation**: Robust path handling with pathlib
- **Improved dependency resolution**: Parallel execution and better error handling
- **Added structured configuration management**: Environment variables and command-line options
- **Enhanced error reporting**: Rich console output and detailed feedback
- **Version Management**: Easy Flutter version switching and management

## FVM Benefits

- **Multiple Flutter Versions**: Install and manage multiple Flutter versions simultaneously
- **Project-Specific Versions**: Use different Flutter versions for different projects
- **Global Default**: Set a global default Flutter version while maintaining project overrides
- **Easy Switching**: Switch between Flutter versions instantly
- **Clean Management**: FVM handles all the complexity of Flutter SDK management
- **Disk Space Optimization**: Shared caching reduces disk usage compared to multiple manual installations

## Quick Start with FVM

After installation, you can use FVM directly:

```bash
# List installed Flutter versions
fvm list

# Install a specific Flutter version
fvm install 3.29.3

# Set global default
fvm global stable

# Use for current project
fvm use 3.29.3

# Run Flutter commands via FVM
fvm flutter doctor
fvm flutter create my_app
fvm flutter pub get
```

## Android SDK Installation

The tool includes automated Android SDK installation for APK building:

### CLI-Based Android SDK Installation

Android SDK installation is handled through the main CLI tool:

```bash
# Install Android SDK only
PYTHONPATH=src rye run python -m komodo_codex_env.cli android-install

# Check Android SDK status
PYTHONPATH=src rye run python -m komodo_codex_env.cli android-status

# Accept Android licenses
PYTHONPATH=src rye run python -m komodo_codex_env.cli android-licenses
```

### Development Scripts

The scripts directory provides utilities for development and verification:

```bash
# Run development tests
python scripts/run_tests.py unit

# Run integration tests (requires Docker or Podman)
python scripts/run_tests.py integration

# Use specific container engine for integration tests
CONTAINER_ENGINE=podman python scripts/run_tests.py integration

# Set up development environment
./scripts/setup_dev_env.sh

# Verify FVM installation
python scripts/verify_fvm.py
```

### Android SDK Features

- **Automatic Java Installation**: Installs OpenJDK 17 if not present
- **Command Line Tools**: Downloads and installs latest Android SDK command line tools
- **Essential Packages**: Installs platform-tools, build-tools, Android API levels 33-35
- **Environment Setup**: Configures ANDROID_HOME and PATH variables
- **License Management**: Handles Android SDK license acceptance
- **Cross-Platform**: Supports Linux, macOS, and Windows

## Testing

The project includes comprehensive unit and integration tests with support for multiple container engines.

### Unit Tests

```bash
# Run all unit tests
python scripts/run_tests.py unit

# Run with verbose output
python scripts/run_tests.py unit --verbose

# Run in parallel
python scripts/run_tests.py unit --parallel
```

### Integration Tests

Integration tests use containerized environments (Docker or Podman) to test complete workflows:

```bash
# Run all integration tests (auto-detects Docker/Podman)
python scripts/run_tests.py integration

# Use Docker explicitly
CONTAINER_ENGINE=docker python scripts/run_tests.py integration

# Use Podman explicitly  
CONTAINER_ENGINE=podman python scripts/run_tests.py integration

# Run specific integration test
python scripts/run_tests.py specific tests/integration/test_flutter_only_integration.py
```

### Container Engine Support

The integration tests support both Docker and Podman:

- **Docker**: Traditional container engine (default if available)
- **Podman**: Rootless container alternative with enhanced security
- **Auto-detection**: Automatically selects available engine
- **Configuration**: Use `CONTAINER_ENGINE` environment variable to specify

For detailed container configuration, see [Container Engine Configuration](docs/CONTAINER_ENGINE_CONFIGURATION.md).

### Android Development Workflow

After installation:

```bash
# Check Android setup
flutter doctor

# Accept Android licenses (if not done during installation)
flutter doctor --android-licenses

# List available devices/emulators
flutter devices

# Build APK
flutter build apk

# Build app bundle
flutter build appbundle
```

### Parallel Installation

When using the main setup command with `android` in platforms, Flutter and Android SDK installation run in parallel for faster setup:

```bash
# This installs Flutter via FVM and Android SDK simultaneously
PYTHONPATH=src rye run python -m komodo_codex_env.cli setup --platforms web,android
```

</edits>

## License

Same license as the original Komodo Wallet project.
