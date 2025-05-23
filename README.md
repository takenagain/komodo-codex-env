# Komodo Codex Environment Setup

A Python-based replacement for the original bash script to set up Flutter development environment for Komodo Wallet using FVM (Flutter Version Management).

## Features

- **FVM Integration**: Uses Flutter Version Management for better Flutter version control
- **Modular Architecture**: Clean separation of concerns with dedicated managers for different components
- **Parallel Execution**: Efficient dependency management with job scheduling
- **Cross-Platform**: Supports macOS (brew), Linux (apt/pacman), and other Unix-like systems
- **Rich Console Output**: Beautiful progress bars and colored output
- **Async Documentation**: Fast concurrent documentation fetching
- **Type Safety**: Full type hints and modern Python practices
- **Version Switching**: Easy Flutter version management via FVM

## Quick Start

### Prerequisites

- Python 3.11+ (Python 3.13 recommended)
- `uv` package manager
- Git
- FVM (Flutter Version Management) - installed automatically

### One-Line Installation

```bash
# Quick install with all dependencies and FVM setup
curl -fsSL https://raw.githubusercontent.com/KomodoPlatform/komodo-codex-env/main/install.sh | bash
```

### Manual Installation

```bash
# Clone and setup
git clone <repository-url>
cd komodo-codex-env

# Install dependencies
uv sync --dev

# Run the setup with FVM
PYTHONPATH=src uv run python -m komodo_codex_env.cli setup --verbose
```

## Usage

### Main Setup Command

```bash
# Full environment setup with FVM
PYTHONPATH=src uv run python -m komodo_codex_env.cli setup

# Setup with custom Flutter version
PYTHONPATH=src uv run python -m komodo_codex_env.cli setup --flutter-version 3.29.3

# Setup with specific platforms
PYTHONPATH=src uv run python -m komodo_codex_env.cli setup --platforms web,android,linux

# Verbose output
PYTHONPATH=src uv run python -m komodo_codex_env.cli setup --verbose
```

### Individual Commands

```bash
# Check system dependencies
PYTHONPATH=src uv run python -m komodo_codex_env.cli check-deps

# Check Flutter status via FVM
PYTHONPATH=src uv run python -m komodo_codex_env.cli flutter-status

# Fetch documentation only
PYTHONPATH=src uv run python -m komodo_codex_env.cli fetch-docs

# FVM Flutter management
PYTHONPATH=src uv run python -m komodo_codex_env.cli fvm-list
PYTHONPATH=src uv run python -m komodo_codex_env.cli fvm-install 3.29.3
PYTHONPATH=src uv run python -m komodo_codex_env.cli fvm-use 3.29.3
PYTHONPATH=src uv run python -m komodo_codex_env.cli fvm-releases

# Update script from remote
PYTHONPATH=src uv run python -m komodo_codex_env.cli update-script
```

## Configuration

The tool supports configuration via environment variables:

```bash
# Flutter version (FVM will manage the actual installation)
export FLUTTER_VERSION=3.32.0

# Platform targets
export PLATFORMS=web,android,linux

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
- `documentation_manager.py` - Documentation fetching
- `setup.py` - Main orchestrator
- `cli.py` - Command-line interface with FVM commands

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
uv sync --dev

# Run tests
uv run pytest

# Format code
uv run black src/

# Type checking
uv run mypy src/

# Run the tool locally
PYTHONPATH=src uv run python -m komodo_codex_env.cli --help
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
fvm global 3.32.0

# Use for current project
fvm use 3.29.3

# Run Flutter commands via FVM
fvm flutter doctor
fvm flutter create my_app
fvm flutter pub get
```

## License

Same license as the original Komodo Wallet project.
