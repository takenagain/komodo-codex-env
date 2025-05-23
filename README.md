# Komodo Codex Environment Setup

A Python-based replacement for the original bash script to set up Flutter development environment for Komodo Wallet.

## Features

- **Modular Architecture**: Clean separation of concerns with dedicated managers for different components
- **Parallel Execution**: Efficient dependency management with job scheduling
- **Cross-Platform**: Supports macOS (brew), Linux (apt/pacman), and other Unix-like systems
- **Rich Console Output**: Beautiful progress bars and colored output
- **Async Documentation**: Fast concurrent documentation fetching
- **Type Safety**: Full type hints and modern Python practices

## Quick Start

### Prerequisites

- Python 3.13+
- `uv` package manager
- Git

### Installation

```bash
# Clone and setup
git clone <repository-url>
cd komodo-codex-env

# Install dependencies
uv sync

# Run the setup
uv run komodo-codex-env setup
```

## Usage

### Main Setup Command

```bash
# Full environment setup
uv run komodo-codex-env setup

# Setup with custom Flutter installation method
uv run komodo-codex-env setup --flutter-method precompiled

# Dry run to see what would be done
uv run komodo-codex-env setup --dry-run
```

### Individual Commands

```bash
# Check system dependencies
uv run komodo-codex-env check-deps

# Check Flutter status
uv run komodo-codex-env flutter-status

# Fetch documentation only
uv run komodo-codex-env fetch-docs

# Update script from remote
uv run komodo-codex-env update-script
```

## Configuration

The tool supports configuration via environment variables:

```bash
export KOMODO_CODEX_FLUTTER_PATH=/custom/flutter/path
export KOMODO_CODEX_DOCS_PATH=/custom/docs/path
export KOMODO_CODEX_DRY_RUN=true
export KOMODO_CODEX_VERBOSE=true
```

## Architecture

- `config.py` - Configuration management
- `executor.py` - Parallel command execution
- `git_manager.py` - Git operations
- `dependency_manager.py` - System dependencies
- `flutter_manager.py` - Flutter SDK management
- `documentation_manager.py` - Documentation fetching
- `setup.py` - Main orchestrator
- `cli.py` - Command-line interface

## Advantages over Bash Script

1. **Better Error Handling**: Structured exception handling vs complex bash conditionals
2. **Type Safety**: Full type hints and IDE support
3. **Modularity**: Clean separation of concerns
4. **Testability**: Each component can be unit tested
5. **Maintainability**: Object-oriented design with clear interfaces
6. **Performance**: Async operations and parallel execution
7. **User Experience**: Rich console output with progress indicators

## Development

```bash
# Install development dependencies
uv add --dev pytest pytest-asyncio black mypy

# Run tests
uv run pytest

# Format code
uv run black src/

# Type checking
uv run mypy src/
```

## Migration from Bash Script

This Python implementation provides equivalent functionality to the original bash script with these improvements:

- Replaced complex associative arrays with proper data structures
- Converted string manipulation to robust path handling
- Improved dependency resolution and parallel execution
- Added structured configuration management
- Enhanced error reporting and user feedback

## License

Same license as the original Komodo Wallet project.
