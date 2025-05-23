#!/bin/bash

# Android SDK Installation Script for Flutter Development
# This script provides a convenient wrapper for the Python Android SDK installer

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    local message="$1"
    local color="${2:-$BLUE}"
    echo -e "${color}${message}${NC}"
}

print_error() {
    print_status "$1" "$RED"
}

print_success() {
    print_status "$1" "$GREEN"
}

print_warning() {
    print_status "$1" "$YELLOW"
}

print_info() {
    print_status "$1" "$BLUE"
}

# Check if Python is available
check_python() {
    if command -v python3 &> /dev/null; then
        echo "python3"
    elif command -v python &> /dev/null; then
        local version=$(python --version 2>&1)
        if [[ $version == *"Python 3"* ]]; then
            echo "python"
        else
            return 1
        fi
    else
        return 1
    fi
}

# Main function
main() {
    print_info "=== Android SDK Installation for Flutter Development ==="
    print_info ""
    
    # Get script directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PYTHON_SCRIPT="$SCRIPT_DIR/install_android_sdk.py"
    
    # Check if Python script exists
    if [[ ! -f "$PYTHON_SCRIPT" ]]; then
        print_error "Python installation script not found: $PYTHON_SCRIPT"
        exit 1
    fi
    
    # Check Python availability
    PYTHON_CMD=$(check_python)
    if [[ $? -ne 0 ]]; then
        print_error "Python 3 is required but not found."
        print_info "Please install Python 3 and try again."
        print_info ""
        print_info "Installation instructions:"
        print_info "- Ubuntu/Debian: sudo apt install python3"
        print_info "- macOS: brew install python3"
        print_info "- Or download from: https://www.python.org/downloads/"
        exit 1
    fi
    
    print_info "Using Python: $PYTHON_CMD"
    print_info ""
    
    # Check if running as root (not recommended)
    if [[ $EUID -eq 0 ]]; then
        print_warning "Warning: Running as root is not recommended."
        print_warning "The Android SDK should be installed in your user directory."
        read -p "Continue anyway? (y/N): " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Installation cancelled."
            exit 0
        fi
    fi
    
    # Check available disk space (require at least 5GB)
    if command -v df &> /dev/null; then
        HOME_SPACE=$(df "$HOME" | awk 'NR==2 {print $4}')
        REQUIRED_SPACE=5242880  # 5GB in KB
        
        if [[ $HOME_SPACE -lt $REQUIRED_SPACE ]]; then
            print_warning "Warning: Less than 5GB available in home directory."
            print_warning "Android SDK installation requires approximately 3-5GB of space."
            read -p "Continue anyway? (y/N): " -r
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                print_info "Installation cancelled."
                exit 0
            fi
        fi
    fi
    
    # Parse command line arguments
    SKIP_JAVA=false
    ANDROID_HOME=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-java)
                SKIP_JAVA=true
                shift
                ;;
            --android-home)
                ANDROID_HOME="$2"
                shift 2
                ;;
            --help|-h)
                print_info "Android SDK Installation Script"
                print_info ""
                print_info "Usage: $0 [OPTIONS]"
                print_info ""
                print_info "Options:"
                print_info "  --skip-java        Skip Java installation"
                print_info "  --android-home DIR Set custom Android SDK directory"
                print_info "  --help, -h         Show this help message"
                print_info ""
                print_info "Environment variables:"
                print_info "  ANDROID_HOME       Custom Android SDK directory"
                print_info "  SKIP_JAVA         Set to 'true' to skip Java installation"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                print_info "Use --help for usage information."
                exit 1
                ;;
        esac
    done
    
    # Set environment variables for Python script
    export SKIP_JAVA_INSTALL="$SKIP_JAVA"
    if [[ -n "$ANDROID_HOME" ]]; then
        export ANDROID_HOME="$ANDROID_HOME"
    fi
    
    # Run the Python installation script
    print_info "Starting Android SDK installation..."
    print_info ""
    
    if ! "$PYTHON_CMD" "$PYTHON_SCRIPT"; then
        print_error "Android SDK installation failed."
        print_info ""
        print_info "Troubleshooting:"
        print_info "1. Check internet connectivity"
        print_info "2. Ensure sufficient disk space (5GB+)"
        print_info "3. Check permissions for writing to home directory"
        print_info "4. Try running with --skip-java if Java is already installed"
        print_info ""
        print_info "For manual installation, visit:"
        print_info "https://developer.android.com/studio/command-line"
        exit 1
    fi
    
    print_success ""
    print_success "=== Installation Summary ==="
    print_info "Android SDK has been installed successfully!"
    print_info ""
    print_warning "IMPORTANT: Restart your terminal or run the following to apply changes:"
    
    # Detect shell and provide appropriate command
    if [[ -n "${ZSH_VERSION:-}" ]]; then
        print_info "  source ~/.zshrc"
    elif [[ -n "${BASH_VERSION:-}" ]]; then
        print_info "  source ~/.bashrc"
    else
        print_info "  source ~/.profile"
    fi
    
    print_info ""
    print_info "Next steps:"
    print_info "1. Restart terminal or source your shell profile"
    print_info "2. Run: flutter doctor"
    print_info "3. Accept Android licenses: flutter doctor --android-licenses"
    print_info "4. Connect device or start emulator: flutter devices"
    print_info "5. Build your first APK: flutter build apk"
    print_info ""
    print_success "Happy Flutter development! 🚀"
}

# Handle script interruption
trap 'print_warning "\nInstallation interrupted by user."; exit 130' INT TERM

# Run main function
main "$@"