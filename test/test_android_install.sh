#!/bin/bash

# Test script to verify Android SDK installation in fresh container
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running in container
if [ ! -f /.dockerenv ] && [ ! -f /run/.containerenv ]; then
    log_warn "Not running in container. This test is designed for container environments."
fi

log_info "Starting Android SDK installation test..."

# Test 1: Run install.sh with Android platform
log_info "Test 1: Running install.sh with Android platform..."
cd /tmp
curl -fsSL https://raw.githubusercontent.com/takenagain/komodo-codex-env/main/install.sh > install.sh
echo 'Y' | timeout 1800 bash install.sh --debug --flutter-version 3.32.0 || {
    log_error "install.sh failed or timed out"
    exit 1
}

# Test 2: Check if environment is set up
log_info "Test 2: Checking environment setup..."
source ~/.komodo-codex-env/setup_env.sh 2>/dev/null || {
    log_error "Failed to source environment setup"
    exit 1
}

# Test 3: Check ANDROID_HOME
log_info "Test 3: Checking ANDROID_HOME..."
if [ -z "${ANDROID_HOME:-}" ]; then
    log_error "ANDROID_HOME not set"
    exit 1
fi
log_success "ANDROID_HOME set to: $ANDROID_HOME"

# Test 4: Check Android SDK directory exists
log_info "Test 4: Checking Android SDK directory..."
if [ ! -d "$ANDROID_HOME" ]; then
    log_error "Android SDK directory does not exist: $ANDROID_HOME"
    exit 1
fi
log_success "Android SDK directory exists: $ANDROID_HOME"

# Test 5: Check cmdline-tools
log_info "Test 5: Checking cmdline-tools..."
SDKMANAGER_PATH="$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager"
if [ ! -f "$SDKMANAGER_PATH" ]; then
    log_error "sdkmanager not found at: $SDKMANAGER_PATH"
    exit 1
fi
log_success "sdkmanager found at: $SDKMANAGER_PATH"

# Test 6: Check platform-tools
log_info "Test 6: Checking platform-tools..."
ADB_PATH="$ANDROID_HOME/platform-tools/adb"
if [ ! -f "$ADB_PATH" ]; then
    log_error "adb not found at: $ADB_PATH"
    exit 1
fi
log_success "adb found at: $ADB_PATH"

# Test 7: Check if platforms are installed
log_info "Test 7: Checking installed platforms..."
PLATFORMS_DIR="$ANDROID_HOME/platforms"
if [ ! -d "$PLATFORMS_DIR" ] || [ -z "$(ls -A "$PLATFORMS_DIR" 2>/dev/null)" ]; then
    log_error "No Android platforms installed in: $PLATFORMS_DIR"
    exit 1
fi
log_success "Android platforms found in: $PLATFORMS_DIR"
ls -la "$PLATFORMS_DIR"

# Test 8: Check if build-tools are installed
log_info "Test 8: Checking build-tools..."
BUILD_TOOLS_DIR="$ANDROID_HOME/build-tools"
if [ ! -d "$BUILD_TOOLS_DIR" ] || [ -z "$(ls -A "$BUILD_TOOLS_DIR" 2>/dev/null)" ]; then
    log_error "No build-tools installed in: $BUILD_TOOLS_DIR"
    exit 1
fi
log_success "Build-tools found in: $BUILD_TOOLS_DIR"
ls -la "$BUILD_TOOLS_DIR"

# Test 9: Test sdkmanager command
log_info "Test 9: Testing sdkmanager command..."
if ! "$SDKMANAGER_PATH" --version >/dev/null 2>&1; then
    log_error "sdkmanager command failed"
    exit 1
fi
log_success "sdkmanager command works"

# Test 10: Check Android status via CLI
log_info "Test 10: Checking Android status via CLI..."
if ! kce android-status; then
    log_error "kce android-status failed"
    exit 1
fi
log_success "Android status check passed"

# Test 11: Check Flutter doctor
log_info "Test 11: Checking Flutter doctor..."
if command -v flutter >/dev/null 2>&1; then
    # Give Flutter a moment to initialize
    sleep 5
    if flutter doctor -v | grep -i "android.*sdk"; then
        log_success "Flutter detects Android SDK"
    else
        log_warn "Flutter may not detect Android SDK properly"
        flutter doctor -v
    fi
else
    log_warn "Flutter not found in PATH, skipping Flutter doctor test"
fi

# Test 12: Verify no sudo was required
log_info "Test 12: Verifying no sudo usage..."
if [ "$ANDROID_HOME" = "/opt/android-sdk" ] || [[ "$ANDROID_HOME" == /opt/* ]]; then
    log_error "Android SDK installed in system directory, may have required sudo: $ANDROID_HOME"
    exit 1
fi
log_success "Android SDK installed in user directory (no sudo required): $ANDROID_HOME"

# Summary
log_success "All Android SDK installation tests passed!"
log_info "Summary:"
log_info "  ANDROID_HOME: $ANDROID_HOME"
log_info "  Platform-tools: $(ls -1 "$ANDROID_HOME/platform-tools" | head -3 | tr '\n' ' ')..."
log_info "  Platforms: $(ls -1 "$ANDROID_HOME/platforms" | tr '\n' ' ')"
log_info "  Build-tools: $(ls -1 "$ANDROID_HOME/build-tools" | tr '\n' ' ')"

exit 0