#!/bin/bash

# Komodo Codex Environment - Development Environment Setup
# This script sets up the Python development environment using Rye
# Usage: ./setup_dev_env.sh

set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}Starting Komodo Codex Environment Python Development Setup${NC}"

# Change to script directory
cd "$(dirname "$0")"

# Change to project root (parent directory of scripts)
cd ..

# Check if rye is installed
if ! command -v rye &> /dev/null; then
    echo -e "${RED}Error: Rye is not installed.${NC}"
    echo -e "${YELLOW}Please install Rye first: https://rye.astral.sh/guide/installation/${NC}"
    echo "Quick install: curl -sSf https://rye.astral.sh/get | bash"
    exit 1
fi

# Ensure dependencies are installed
echo -e "${YELLOW}Installing/updating Python dependencies with Rye...${NC}"
rye sync

# Check if we have the basic system dependencies
echo -e "${YELLOW}Checking system dependencies...${NC}"
rye run python -m komodo_codex_env.cli check-deps

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}Python development environment setup completed successfully!${NC}"
    
    echo -e "${GREEN}Available commands for Python development:${NC}"
    echo ""
    echo "System checks:"
    echo "  rye run python -m komodo_codex_env.cli check-deps"
    echo ""
    echo "Documentation:"
    echo "  rye run python -m komodo_codex_env.cli fetch-docs"
    echo ""
    echo "Development commands:"
    echo "  rye run pytest                    # Run tests"
    echo "  rye run python -m komodo_codex_env.cli --help    # Show all CLI options"
    echo ""
    echo "Package management:"
    echo "  rye add <package>                # Add dependency"
    echo "  rye add --dev <package>          # Add dev dependency"
    echo "  rye sync                         # Sync dependencies"
    echo "  rye run <command>                # Run command in environment"
    
else
    echo -e "${RED}Setup failed with exit code $exit_code${NC}"
    echo -e "${YELLOW}You can try running individual commands to debug:${NC}"
    echo "  rye run python -m komodo_codex_env.cli check-deps"
    echo "  rye run python -m komodo_codex_env.cli --help"
fi

exit $exit_code