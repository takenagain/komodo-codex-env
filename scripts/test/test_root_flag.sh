#!/bin/bash

# Script to test the --allow-root flag in the Komodo Codex Environment installer

set -euo pipefail

# Colors for formatted output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Testing Komodo Codex Environment installer with --allow-root flag ===${NC}"

# Create a temporary directory for downloading the installer
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

echo -e "${BLUE}[INFO]${NC} Downloading installer..."
curl -sSL https://raw.githubusercontent.com/takenagain/komodo-codex-env/refs/heads/main/install.sh -o install.sh

# Check if download was successful
if [[ -f install.sh ]]; then
    echo -e "${GREEN}[SUCCESS]${NC} Downloaded installer"
else
    echo -e "${RED}[ERROR]${NC} Failed to download installer"
    exit 1
fi

# Make script executable
chmod +x install.sh

# Verify if the --allow-root flag is implemented
if grep -q "ALLOW_ROOT" install.sh && grep -q -- "--allow-root" install.sh; then
    echo -e "${GREEN}[SUCCESS]${NC} --allow-root flag is implemented"
else
    echo -e "${RED}[ERROR]${NC} --allow-root flag is not implemented"
    exit 1
fi

# Check if the root check is properly implemented
if grep -q "if \[\[ \$EUID -eq 0 \]\]; then" install.sh && grep -q "if \[\[ \"\$ALLOW_ROOT\" = true \]\]" install.sh; then
    echo -e "${GREEN}[SUCCESS]${NC} Root check with override is implemented"
else
    echo -e "${RED}[ERROR]${NC} Root check with override is not implemented"
    exit 1
fi

echo -e "${GREEN}[SUCCESS]${NC} All checks passed!"
echo -e "${BLUE}[INFO]${NC} To run the installer as root, use:"
echo -e "curl -sSL https://raw.githubusercontent.com/takenagain/komodo-codex-env/refs/heads/main/install.sh | bash -s -- --allow-root"

# Clean up
cd - > /dev/null
rm -rf "$TEMP_DIR"