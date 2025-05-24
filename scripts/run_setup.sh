#!/bin/bash

# Komodo Codex Environment - Setup Runner with FVM
# This script runs the full setup with all options enabled using FVM for Flutter management
# Usage: ./run_setup.sh [--flutter-version VERSION]

set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Default Flutter version
FLUTTER_VERSION="3.32.0"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --flutter-version)
            FLUTTER_VERSION="$2"
            shift 2
            ;;
        --flutter-version=*)
            FLUTTER_VERSION="${1#*=}"
            shift
            ;;
        *)
            echo "Unknown option $1"
            echo "Usage: $0 [--flutter-version VERSION]"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}Starting Komodo Codex Environment Setup with FVM and All Options Enabled${NC}"
echo -e "${YELLOW}Flutter version: $FLUTTER_VERSION${NC}"

# Change to script directory
cd "$(dirname "$0")"

# Ensure dependencies are installed
echo -e "${YELLOW}Installing/updating dependencies...${NC}"
uv sync --dev

# Check if we have the basic system dependencies
echo -e "${YELLOW}Checking system dependencies...${NC}"
PYTHONPATH=src uv run python -m komodo_codex_env.cli check-deps

# Set Python path and run the full setup with FVM
echo -e "${YELLOW}Running full setup with FVM and Flutter version $FLUTTER_VERSION...${NC}"
PYTHONPATH=src uv run python -m komodo_codex_env.cli setup \
    --flutter-version "$FLUTTER_VERSION" \
    --install-method precompiled \
    --platforms web,android,linux \
    --kdf-docs \
    --verbose

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}Setup completed successfully!${NC}"
    
    # Show FVM status
    echo -e "${YELLOW}Checking FVM and Flutter status...${NC}"
    PYTHONPATH=src uv run python -m komodo_codex_env.cli flutter-status
    
    # List FVM versions
    echo -e "${YELLOW}Installed Flutter versions via FVM:${NC}"
    PYTHONPATH=src uv run python -m komodo_codex_env.cli fvm-list
    
    echo -e "${GREEN}All done! You can now use the following commands:${NC}"
    echo ""
    echo "System checks:"
    echo "  PYTHONPATH=src uv run python -m komodo_codex_env.cli check-deps"
    echo "  PYTHONPATH=src uv run python -m komodo_codex_env.cli flutter-status"
    echo ""
    echo "Documentation:"
    echo "  PYTHONPATH=src uv run python -m komodo_codex_env.cli fetch-docs"
    echo ""
    echo "FVM Flutter management:"
    echo "  PYTHONPATH=src uv run python -m komodo_codex_env.cli fvm-list"
    echo "  PYTHONPATH=src uv run python -m komodo_codex_env.cli fvm-install <version>"
    echo "  PYTHONPATH=src uv run python -m komodo_codex_env.cli fvm-use <version>"
    echo "  PYTHONPATH=src uv run python -m komodo_codex_env.cli fvm-releases"
    echo ""
    echo "Direct FVM usage (after setup):"
    echo "  fvm flutter doctor"
    echo "  fvm flutter create my_app"
    echo "  fvm flutter pub get"
    echo ""
    echo "Full help:"
    echo "  PYTHONPATH=src uv run python -m komodo_codex_env.cli --help"
    
else
    echo -e "${RED}Setup failed with exit code $exit_code${NC}"
    echo -e "${YELLOW}You can try running individual commands to debug:${NC}"
    echo "  PYTHONPATH=src uv run python -m komodo_codex_env.cli check-deps"
    echo "  PYTHONPATH=src uv run python -m komodo_codex_env.cli --help"
fi

exit $exit_code