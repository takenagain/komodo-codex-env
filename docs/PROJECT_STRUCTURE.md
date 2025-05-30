# Project Structure and Organization

This document outlines the complete file organization of the Komodo Codex Environment Setup Tool after the Android SDK integration and file reorganization.

## Overview

The project has been reorganized to provide clear separation between:
- Core Python package (`src/`)
- Standalone utilities (`scripts/`)
- Documentation (`docs/`)
- Project configuration (root)

## Directory Structure

```
komodo-codex-env/
├── src/komodo_codex_env/               # Main Python package
│   ├── __init__.py                     # Package initialization
│   ├── cli.py                          # Command-line interface
│   ├── config.py                       # Configuration management
│   ├── setup.py                        # Main orchestrator
│   ├── executor.py                     # Parallel execution system
│   ├── dependency_manager.py           # System dependencies
│   ├── git_manager.py                  # Git operations
│   ├── flutter_manager.py              # Flutter/FVM management
│   ├── android_manager.py              # Android SDK management
│   └── documentation_manager.py        # Documentation fetching
├── scripts/                            # Standalone scripts and utilities
│   ├── README.md                       # Scripts documentation
│   ├── run_tests.py                    # Test runner helper script
│   ├── setup_dev_env.sh                # Python development setup script
│   └── verify_fvm.py                   # FVM verification script
├── docs/                               # Documentation
│   ├── README.md                       # Documentation index
│   ├── android/                        # Android-specific documentation
│   │   ├── ANDROID_SDK_GUIDE.md        # User guide for Android SDK
│   │   └── ANDROID_SDK_IMPLEMENTATION.md # Technical implementation details
│   └── commit_conventions.md           # Git commit conventions
├── .venv/                              # Python virtual environment
├── .git/                               # Git repository data
├── .gitignore                          # Git ignore rules
├── .python-version                     # Python version specification
├── .ropeproject/                       # Rope IDE configuration
├── AGENTS.md                           # Agent documentation
├── KDF_API_DOCUMENTATION.md           # KDF API documentation
├── PROJECT_STRUCTURE.md               # This file
├── README.md                           # Main project README
├── install.sh                          # Main installation script
├── pyproject.toml                      # Python project configuration
├── requirements-dev.txt                # Development dependencies
├── requirements.txt                    # Runtime dependencies
└── uv.lock                            # UV package lock file
```

## Core Components (src/komodo_codex_env/)

### Main Modules

- **`cli.py`** - Command-line interface with full command set including Android SDK commands
- **`setup.py`** - Main orchestrator implementing parallel execution of Flutter and Android setup
- **`config.py`** - Configuration management with Android SDK settings support
- **`executor.py`** - Parallel execution framework with job dependency management

### Manager Classes

- **`flutter_manager.py`** - Flutter SDK management via FVM (Flutter Version Management)
- **`android_manager.py`** - Android SDK installation and configuration management
- **`dependency_manager.py`** - System dependency management with environment variable support
- **`git_manager.py`** - Git repository operations and branch management
- **`documentation_manager.py`** - Asynchronous documentation fetching and management

## Standalone Scripts (scripts/)

### Android SDK Installation

### Development and Testing Scripts

- **`run_tests.py`** - Test runner helper script
  - Unit test execution with optional parallelization
  - Integration test execution with Docker
  - Coverage reporting and analysis
  - Linting and syntax checking
  - Specific test file execution

- **`verify_fvm.py`** - FVM installation verification
  - Checks FVM availability for multiple users
  - Verifies PATH configuration in shell profiles
  - Lists installed Flutter versions via FVM
  - Validates FVM command functionality
  - Cross-platform verification support
  - Automated Docker container management

## Documentation (docs/)

### User Documentation

- **`README.md`** - Documentation index and navigation guide
- **`android/ANDROID_SDK_GUIDE.md`** - Comprehensive Android SDK user guide
  - Installation options and workflows
  - Platform-specific instructions
  - Troubleshooting and debugging
  - Command reference and examples

### Technical Documentation

- **`android/ANDROID_SDK_IMPLEMENTATION.md`** - Implementation details
  - Architecture and design decisions
  - Component integration patterns
  - Parallel execution system
  - Testing strategies and validation
  - Performance considerations

### Development Guidelines

- **`bloc_concepts.md`** - Flutter BLoC architecture concepts
- **`bloc_conventions.md`** - Coding conventions for BLoC pattern
- **`bloc_modeling.md`** - Data modeling guidelines
- **`bloc_testing.md`** - Testing strategies for BLoC components
- **`commit_conventions.md`** - Git commit message standards

## Usage Patterns

### Primary Workflows

1. **Full Environment Setup**: `PYTHONPATH=src uv run python -m komodo_codex_env.cli setup`
2. **Development Environment**: `./scripts/setup_dev_env.sh`
3. **Development Testing**: `python scripts/run_tests.py unit`

### Configuration Files

- **`pyproject.toml`** - Python project metadata and dependencies
- **`uv.lock`** - Locked dependency versions for reproducible builds
- **`.python-version`** - Python version specification for version managers

### Environment Management

- **`.venv/`** - Isolated Python environment for development
- **`requirements.txt`** - Runtime dependencies
- **`requirements-dev.txt`** - Development and testing dependencies

## Key Features by Location

### Core Package Features (`src/`)

- Parallel execution of Flutter and Android SDK installation
- Comprehensive configuration management
- Cross-platform dependency resolution
- Async documentation fetching
- Rich console output with progress indicators

### Standalone Script Features (`scripts/`)

- Independent Android SDK installation capability
- User-friendly command-line interfaces
- Comprehensive testing coverage
- Platform-specific optimizations

### Documentation Features (`docs/`)

- Complete user guides and tutorials
- Technical implementation details
- Development guidelines and conventions
- Troubleshooting and debugging guides

## Design Principles

### Modularity
- Clear separation of concerns between components
- Independent functionality in standalone scripts
- Organized documentation by topic and audience

### Maintainability
- Consistent file organization patterns
- Comprehensive testing at multiple levels
- Clear documentation for users and developers

### Usability
- Multiple usage patterns for different needs
- Progressive complexity from simple to advanced
- Comprehensive error handling and user feedback

### Extensibility
- Plugin-like architecture for new managers
- Configurable parallel execution system
- Modular documentation structure

This organization provides a solid foundation for continued development while maintaining clear boundaries between different aspects of the system.
