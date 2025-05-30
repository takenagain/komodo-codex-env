# Development Setup Guide

This guide covers setting up the development environment for the Komodo Codex Environment project.

## Quick Start

### Prerequisites

- Python 3.11+ (Python 3.13 recommended)
- [Rye](https://rye.astral.sh/) package manager
- Git
- Make (usually pre-installed on macOS/Linux)

### One-Command Setup

```bash
# Clone the repository
git clone <repository-url>
cd komodo-codex-env

# Set up complete development environment
make setup
```

## Development Approaches

We provide multiple ways to manage the development environment:

### 1. Makefile (Recommended)

The Makefile provides the most comprehensive and standardized approach:

```bash
# View all available commands
make help

# Development setup
make setup              # Complete setup (install deps + check system)
make install            # Install dependencies only
make check-deps         # Check system dependencies

# Testing
make test              # Run all tests
make test-verbose      # Run tests with verbose output
make test-coverage     # Run tests with coverage report
make quick-test        # Fast test run (stops on first failure)

# Code Quality
make lint              # Run linting
make format            # Format code
make type-check        # Run type checking
make ci                # Run all CI checks (lint + type + test)
make pre-commit        # Run pre-commit checks

# Development
make run-cli           # Run CLI (use ARGS="--help" for arguments)
make docs              # Fetch documentation
make clean             # Clean build artifacts
make update            # Update dependencies
```

Examples:
```bash
# Run CLI with specific arguments
make run-cli ARGS="check-deps"
make run-cli ARGS="--help"

# Run all quality checks before committing
make pre-commit
```

### 2. Rye Scripts

Use Rye's built-in script system defined in `pyproject.toml`:

```bash
# Setup
rye run setup          # Check system dependencies
rye run check-deps     # Check system dependencies

# Testing
rye run test           # Run tests
rye run test-v         # Verbose tests
rye run test-cov       # Tests with coverage
rye run test-quick     # Quick test run

# Code Quality
rye run lint           # Lint code
rye run format         # Format code
rye run format-check   # Check formatting

# CLI
rye run cli --help     # Run CLI
rye run docs           # Fetch docs
rye run status         # Check status

# Utilities
rye run clean          # Clean cache files
```

### 3. Legacy Shell Script

For compatibility, the shell script is still available:

```bash
./scripts/setup_dev_env.sh
```

## Development Workflow

### Initial Setup

1. **Install Rye** (if not already installed):
   ```bash
   curl -sSf https://rye.astral.sh/get | bash
   ```

2. **Clone and setup project**:
   ```bash
   git clone <repository-url>
   cd komodo-codex-env
   make setup
   ```

### Daily Development

```bash
# Start development session
make install           # Ensure dependencies are current

# Make changes...

# Before committing
make pre-commit        # Run all quality checks

# Or run individual checks
make test              # Run tests
make lint              # Check code style
make format            # Fix formatting
```

### Testing

```bash
# Basic testing
make test              # Run all tests
make test-verbose      # Detailed output
make quick-test        # Stop on first failure

# Coverage analysis
make test-coverage     # Generate coverage report
# View coverage report at htmlcov/index.html

# Integration testing
python scripts/run_tests.py integration
```

### Code Quality

```bash
# Formatting
make format            # Auto-format code
rye run format-check   # Check without changing

# Linting
make lint              # Check for issues

# Type checking (if mypy is installed)
make type-check        # Verify type hints
```

## Project Structure

```
komodo-codex-env/
├── Makefile                   # Development commands (recommended)
├── pyproject.toml            # Project config + Rye scripts
├── DEVELOPMENT.md            # This file
├── src/komodo_codex_env/     # Main package
├── tests/                    # Test suite
└── scripts/                  # Utility scripts
    ├── setup_dev_env.sh      # Legacy setup script
    └── ...                   # Other utility scripts
```

## Available Commands Summary

| Task | Makefile | Rye Scripts | Description |
|------|----------|-------------|-------------|
| Setup | `make setup` | `rye run setup` | Full environment setup |
| Test | `make test` | `rye run test` | Run test suite |
| Lint | `make lint` | `rye run lint` | Code linting |
| Format | `make format` | `rye run format` | Code formatting |
| CLI | `make run-cli ARGS="..."` | `rye run cli ...` | Run the CLI tool |
| Clean | `make clean` | `rye run clean` | Clean artifacts |
| Help | `make help` | N/A | Show available commands |

## Troubleshooting

### Rye Not Found
```bash
# Install Rye
curl -sSf https://rye.astral.sh/get | bash
# Restart shell or source ~/.bashrc
```

### Make Not Found (Windows)
```bash
# Use Rye scripts instead
rye run test
rye run lint
# Or install make via chocolatey/scoop
```

### Dependency Issues
```bash
# Reset environment
make clean
rye sync
make setup
```

### Test Failures
```bash
# Run specific test with verbose output
make run-cli ARGS="check-deps"
rye run test-v
```

## IDE Configuration

### VS Code
Recommended extensions:
- Python
- Ruff (for linting/formatting)
- Pylance (for type checking)

### PyCharm
- Configure Python interpreter to use Rye's virtual environment
- Enable Ruff for formatting/linting

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Run `make pre-commit` to ensure quality
5. Submit a pull request

The `make pre-commit` command runs all necessary checks:
- Code formatting
- Linting
- Type checking
- Full test suite