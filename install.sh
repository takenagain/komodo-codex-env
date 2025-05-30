#!/bin/bash

# Komodo Codex Environment - One-Line Installer with FVM
# Usage: curl -fsSL https://raw.githubusercontent.com/takenagain/komodo-codex-env/main/install.sh | bash
# Or: bash <(curl -fsSL https://raw.githubusercontent.com/takenagain/komodo-codex-env/main/install.sh)
# With custom Flutter version: bash <(curl -fsSL https://raw.githubusercontent.com/takenagain/komodo-codex-env/main/install.sh) --flutter-version 3.29.3
# This script installs FVM (Flutter Version Management) for better Flutter version control

#
# DEFAULT INSTALLATION PATH SUMMARY:
# =================================
# The default installation follows these steps in order:
# 1. install_system_deps   - Install system dependencies (curl, git, unzip, python, dart)
# 2. install_uv           - Install UV package manager for Python dependencies
# 3. setup_project        - Clone repository, install Python deps, verify installation
# 4. setup_shell_integration - Setup shell aliases and PATH modifications
#
# After installation, the CLI runs with these default values:
# - kce-full-setup uses: --platforms web (web only by default, use --platforms web,android,linux for full setup)
# - Flutter version: 3.32.0 (configurable via --flutter-version)
# - Install method: precompiled (faster than building from source)
# - KDF docs: enabled (--kdf-docs flag)
# - Verbose output: enabled (--verbose flag)
#
# User Management:
# - Automatically detects and switches to non-root users (ubuntu, ec2-user, etc.)
# - Installs to ~/.komodo-codex-env for the target user
# - Configures shell integration in user's shell profile
#

set -uo pipefail
# Note: removed 'e' from set options to prevent immediate exit on error

# Colors and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Configuration
REPO_URL="https://github.com/takenagain/komodo-codex-env.git"
INSTALL_DIR="${HOME}/.komodo-codex-env"
PYTHON_MIN_VERSION="3.11"
REQUIRED_PYTHON_VERSION="3.13"
ALLOW_ROOT=false
DEBUG=false
FLUTTER_VERSION="3.32.0"
PLATFORMS="web"
INSTALL_TYPE="ALL"

# Help function
show_help() {
    echo "Komodo Codex Environment - One-Line Installer with FVM"
    echo ""
    echo "Usage:"
    echo "  curl -fsSL https://raw.githubusercontent.com/takenagain/komodo-codex-env/main/install.sh | bash"
    echo "  bash <(curl -fsSL https://raw.githubusercontent.com/takenagain/komodo-codex-env/main/install.sh) [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --flutter-version VERSION    Specify Flutter version to install (default: $FLUTTER_VERSION)"
    echo "  --platforms PLATFORMS        Comma-separated list of platforms (default: $PLATFORMS)"
    echo "                              Available: web,android,linux,macos,windows,ios"
    echo "  --install-type TYPE         Installation type: ALL, KW, KDF, or KDF-SDK (default: $INSTALL_TYPE)"
    echo "  --no-android                 Exclude Android platform (equivalent to --platforms web)"
    echo "  --allow-root                 Allow installation as root user"
    echo "  --debug                      Enable debug mode with verbose output"
    echo "  --help, -h                   Show this help message"
    echo ""
    echo "Examples:"
    echo "  # Install with Flutter 3.29.3"
    echo "  bash <(curl -fsSL https://raw.githubusercontent.com/takenagain/komodo-codex-env/main/install.sh) --flutter-version 3.29.3"
    echo ""
    echo "  # Install with specific platforms"
    echo "  bash <(curl -fsSL https://raw.githubusercontent.com/takenagain/komodo-codex-env/main/install.sh) --platforms web,android,linux"
    echo ""
    echo "  # Install web only (no Android)"
    echo "  bash <(curl -fsSL https://raw.githubusercontent.com/takenagain/komodo-codex-env/main/install.sh) --no-android"
    echo ""
    echo "  # Install with debug output"
    echo "  bash <(curl -fsSL https://raw.githubusercontent.com/takenagain/komodo-codex-env/main/install.sh) --debug"
    echo ""
    echo "This script installs FVM (Flutter Version Management) for better Flutter version control."
    echo ""
    echo "User Management:"
    echo "  - Automatically detects and switches to non-root users (ubuntu, ec2-user, etc.)"
    echo "  - Installs web platform by default (Android SDK optional)"
    echo "  - Configures CLI with optimal default settings"
    echo ""
    echo "Default Installation Includes:"
    echo "  - FVM (Flutter Version Management)"
    echo "  - Android SDK (via --platforms android)"
    echo "  - Web and Linux platform support"
    echo "  - KDF documentation"
    echo "  - Shell integration and aliases"
    echo ""
    echo "Optional Platform Support:"
    echo "  - Android SDK (use --platforms web,android)"
    echo "  - Linux desktop (use --platforms web,linux)"
    echo "  - Multiple platforms (use --platforms web,android,linux)"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --allow-root)
            ALLOW_ROOT=true
            shift
            ;;
        --debug)
            DEBUG=true
            set -x  # Enable bash debug mode
            shift
            ;;
        --flutter-version)
            if [[ -n "${2:-}" ]]; then
                FLUTTER_VERSION="$2"
                shift 2
            else
                echo "Error: --flutter-version requires a version argument"
                echo "Example: --flutter-version 3.29.3"
                exit 1
            fi
            ;;
        --flutter-version=*)
            FLUTTER_VERSION="${1#*=}"
            if [[ -z "$FLUTTER_VERSION" ]]; then
                echo "Error: --flutter-version requires a version argument"
                echo "Example: --flutter-version=3.29.3"
                exit 1
            fi
            shift
            ;;
        --platforms)
            if [[ -n "${2:-}" ]]; then
                PLATFORMS="$2"
                shift 2
            else
                echo "Error: --platforms requires a comma-separated list argument"
                echo "Example: --platforms web,android,linux"
                exit 1
            fi
            ;;
        --platforms=*)
            PLATFORMS="${1#*=}"
            if [[ -z "$PLATFORMS" ]]; then
                echo "Error: --platforms requires a comma-separated list argument"
                echo "Example: --platforms=web,android,linux"
                exit 1
            fi
            shift
            ;;
        --install-type)
            if [[ -n "${2:-}" ]]; then
                INSTALL_TYPE="${2^^}"
                shift 2
            else
                echo "Error: --install-type requires an argument"
                echo "Example: --install-type KDF"
                exit 1
            fi
            ;;
        --install-type=*)
            INSTALL_TYPE="${1#*=}"
            INSTALL_TYPE="${INSTALL_TYPE^^}"
            if [[ -z "$INSTALL_TYPE" ]]; then
                echo "Error: --install-type requires an argument"
                echo "Example: --install-type=KDF"
                exit 1
            fi
            shift
            ;;
        --no-android)
            PLATFORMS="web"
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Logging functions
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

log_debug() {
    if [[ "$DEBUG" = true ]]; then
        echo -e "${YELLOW}[DEBUG]${NC} $1"
    fi
}

log_step() {
    echo -e "\n${CYAN}${BOLD}=== $1 ===${NC}"
}

# Error handling
handle_error() {
    local exit_code=$?
    local line_no=$1
    log_error "Installation failed at line ${line_no} with exit code ${exit_code}"
    log_error "Last command: $(fc -ln -1)"

    if [[ "$DEBUG" = true ]]; then
        # Print stack trace in debug mode
        local i=0
        local stack_size=${#FUNCNAME[@]}
        log_error "Stack trace:"
        for ((i=1; i<stack_size; i++)); do
            local func="${FUNCNAME[$i]}"
            local line="${BASH_LINENO[$((i-1))]}"
            local src="${BASH_SOURCE[$i]}"
            log_error "  at ${func}() in ${src}:${line}"
        done
    fi

    log_info "For more detailed debugging information, run with --debug flag"
    log_info "To run as root, use the --allow-root flag"

    exit $exit_code
}

trap 'handle_error $LINENO' ERR

# Utility functions
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

get_os() {
    case "$(uname -s)" in
        Darwin) echo "macos" ;;
        Linux) echo "linux" ;;
        CYGWIN*|MINGW*|MSYS*) echo "windows" ;;
        *) echo "unknown" ;;
    esac
}

get_arch() {
    case "$(uname -m)" in
        x86_64|amd64) echo "x64" ;;
        arm64|aarch64) echo "arm64" ;;
        armv7l) echo "arm" ;;
        *) echo "unknown" ;;
    esac
}

get_distro() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        echo "${ID}"
    elif [[ -f /etc/redhat-release ]]; then
        echo "rhel"
    elif [[ -f /etc/debian_version ]]; then
        echo "debian"
    else
        echo "unknown"
    fi
}

version_compare() {
    printf '%s\n%s\n' "$1" "$2" | sort -V | head -n1
}

is_version_greater_equal() {
    [[ "$(version_compare "$1" "$2")" == "$2" ]]
}

# Run a command with error handling
run_command() {
    local cmd=$1
    local error_msg=$2

    log_debug "Running command: $cmd"
    local output
    if ! output=$(eval "$cmd" 2>&1); then
        log_error "$error_msg"
        log_error "Command output: $output"
        return 1
    fi
    return 0
}

# System dependency installation
install_system_deps() {
    local os=$(get_os)
    local distro=$(get_distro)

    log_step "Installing System Dependencies"
    log_info "Detected OS: $os, Distribution: $distro, Architecture: $(get_arch)"

    case "$os" in
        "macos")
            if ! command_exists brew; then
                log_info "Installing Homebrew..."
                if ! run_command "/bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"" "Failed to install Homebrew"; then
                    log_warn "Continuing without Homebrew. Some dependencies may be missing."
                else
                    # Add brew to PATH for current session
                    if [[ -f /opt/homebrew/bin/brew ]]; then
                        eval "$(/opt/homebrew/bin/brew shellenv)"
                    elif [[ -f /usr/local/bin/brew ]]; then
                        eval "$(/usr/local/bin/brew shellenv)"
                    fi
                fi
            fi

            log_info "Installing macOS dependencies..."
            run_command "brew update" "Failed to update Homebrew" || true
            run_command "brew install curl git unzip xz zip" "Failed to install core dependencies" || true
            run_command "brew install python@${REQUIRED_PYTHON_VERSION}" "Failed to install Python ${REQUIRED_PYTHON_VERSION}" || true
            run_command "brew install dart" "Failed to install Dart" || true
            ;;

        "linux")
            case "$distro" in
                "ubuntu"|"debian")
                    log_info "Installing Ubuntu/Debian dependencies..."
                    if ! run_command "sudo apt-get update -qq" "Failed to update apt repositories"; then
                        log_warn "APT update failed. Continuing with installation..."
                    fi

                    # Install core dependencies (minimal set for install script and Python, plus essential tools)
                    log_info "Installing core dependencies..."
                    run_command "sudo apt-get install -y wget python3-pip python3-full unzip curl git" "Failed to install core dependencies" || true

                    # Install Python development dependencies
                    log_info "Installing Python development dependencies..."
                    run_command "sudo apt-get install -y software-properties-common libssl-dev libffi-dev libbz2-dev libreadline-dev libsqlite3-dev llvm libncurses5-dev libncursesw5-dev tk-dev libxml2-dev libxmlsec1-dev liblzma-dev" "Failed to install Python development dependencies" || true

                    # Try to install Python 3.13 from deadsnakes PPA
                    if ! command_exists python${REQUIRED_PYTHON_VERSION}; then
                        log_info "Adding deadsnakes PPA for Python ${REQUIRED_PYTHON_VERSION}..."
                        run_command "sudo add-apt-repository -y ppa:deadsnakes/ppa" "Failed to add deadsnakes PPA" || true
                        run_command "sudo apt-get update -qq" "Failed to update apt after adding PPA" || true

                        # Install Python packages (distutils only for versions < 3.12)
                        local python_packages="python${REQUIRED_PYTHON_VERSION} python${REQUIRED_PYTHON_VERSION}-dev python${REQUIRED_PYTHON_VERSION}-venv"
                        if [[ "${REQUIRED_PYTHON_VERSION}" < "3.12" ]]; then
                            python_packages="${python_packages} python${REQUIRED_PYTHON_VERSION}-distutils"
                        fi
                        run_command "sudo apt-get install -y ${python_packages}" "Failed to install Python ${REQUIRED_PYTHON_VERSION}" || true
                    fi

                    # Note: Dart SDK and other system dependencies (curl, git, unzip, etc.)
                    # are now handled by the Python CLI program for better consistency
                    ;;

                "fedora"|"rhel"|"centos")
                    log_info "Installing Fedora/RHEL dependencies..."
                    # Install Python and development dependencies, plus essential tools
                    run_command "sudo dnf install -y python3-pip python3-devel wget unzip curl git gcc openssl-devel bzip2-devel libffi-devel readline-devel sqlite-devel llvm ncurses-devel tk-devel libxml2-devel xmlsec1-devel xz-devel" "Failed to install dependencies" || true

                    # Note: curl, git, unzip, xz, zip, mesa-libGLU, and dart are now handled by the Python CLI program
                    ;;

                "arch"|"manjaro")
                    log_info "Installing Arch dependencies..."
                    # Install Python and development dependencies, plus essential tools
                    run_command "sudo pacman -Sy --noconfirm python-pip python-setuptools wget unzip curl git base-devel openssl bzip2 libffi readline sqlite llvm ncurses tk libxml2 xmlsec xz" "Failed to install dependencies" || true

                    # Note: curl, git, unzip, xz, zip, glu, and dart are now handled by the Python CLI program
                    ;;

                *)
                    log_warn "Unknown Linux distribution: $distro"
                    log_warn "Please ensure the following packages are installed:"
                    log_warn "python3-pip, python3-dev, wget, and basic development tools"
                    log_warn "Other dependencies (curl, git, unzip, etc.) will be handled by the Python CLI program"
                    ;;
            esac
            ;;

        *)
            log_error "Unsupported operating system: $os"
            return 1
            ;;
    esac

    # Verify essential tools are available
    for tool in curl git unzip; do
        if ! command_exists "$tool"; then
            log_error "Essential tool '$tool' is not available. Installation cannot continue."
            return 1
        else
            log_debug "Found essential tool: $tool at $(which $tool)"
        fi
    done

    log_success "System dependencies installed"
    return 0
}

# Setup /opt directory for Android SDK installation
setup_opt_directory() {
    log_step "Setting up /opt directory for Android SDK"

    local os=$(get_os)

    # Only needed on Linux systems
    if [[ "$os" != "linux" ]]; then
        log_info "Skipping /opt setup on $os"
        return 0
    fi

    # Check if /opt exists and is writable
    if [[ -w /opt ]]; then
        log_info "/opt directory is already writable"
        return 0
    fi

    # Create /opt if it doesn't exist and make it writable by current user
    if [[ ! -d /opt ]]; then
        log_info "Creating /opt directory..."
        if ! run_command "sudo mkdir -p /opt" "Failed to create /opt directory"; then
            log_error "Failed to create /opt directory"
            return 1
        fi
    fi

    # Make /opt writable by current user (following dockerfile pattern)
    log_info "Setting up /opt directory permissions for user: $(whoami)"
    if ! run_command "sudo chown -R $(whoami):$(id -gn) /opt" "Failed to set /opt permissions"; then
        log_warn "Failed to set /opt permissions. Android SDK installation may require sudo."
        return 1
    fi

    log_success "/opt directory setup completed"
    return 0
}

# UV package manager installation
install_uv() {
    log_step "Installing UV Package Manager"

    if command_exists uv; then
        log_info "UV already installed: $(uv --version)"
        return 0
    fi

    log_info "Installing UV..."
    if ! run_command "curl -LsSf https://astral.sh/uv/install.sh | sh" "Failed to install UV"; then
        log_error "UV installation failed. Attempting fallback to pip..."

        # Ensure we have Python and pip
        if ! command_exists python3 && ! command_exists python; then
            log_error "No Python installation found. Cannot install dependencies."
            return 1
        fi

        local python_cmd="python3"
        if ! command_exists python3; then
            python_cmd="python"
        fi

        # Ensure pip is available
        if ! "$python_cmd" -m pip --version >/dev/null 2>&1; then
            log_info "Installing pip via system package manager..."
            local os=$(get_os)
            local distro=$(get_distro)

            case "$os" in
                "linux")
                    case "$distro" in
                        "ubuntu"|"debian")
                            run_command "sudo apt-get install -y python3-pip" "Failed to install pip via apt" || true
                            ;;
                        "fedora"|"rhel"|"centos")
                            run_command "sudo dnf install -y python3-pip" "Failed to install pip via dnf" || true
                            ;;
                        "arch"|"manjaro")
                            run_command "sudo pacman -Sy --noconfirm python-pip" "Failed to install pip via pacman" || true
                            ;;
                    esac
                    ;;
            esac

            # If system pip installation failed, try get-pip.py with --break-system-packages
            if ! "$python_cmd" -m pip --version >/dev/null 2>&1; then
                log_info "System pip installation failed, trying get-pip.py..."
                if ! run_command "curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py" "Failed to download pip installer"; then
                    log_error "Failed to download pip installer."
                    return 1
                fi
                if ! run_command "$python_cmd get-pip.py --break-system-packages" "Failed to install pip"; then
                    log_error "Pip installation failed."
                    return 1
                fi
                rm -f get-pip.py
            fi
        fi

        # Install uv using pip
        log_info "Installing UV using pip..."
        if ! run_command "$python_cmd -m pip install --user uv" "Failed to install UV with pip"; then
            # Try with --break-system-packages if user install fails
            log_info "User pip install failed, trying with --break-system-packages..."
            if ! run_command "$python_cmd -m pip install --break-system-packages uv" "Failed to install UV with pip (break-system-packages)"; then
                log_error "All UV installation methods failed."
                log_info "Please install UV manually: https://github.com/astral-sh/uv"
                return 1
            fi
        fi
    fi

    # Add UV to current PATH
    export PATH="$HOME/.local/bin:$PATH"

    # Check if uv is available
    if ! command_exists uv; then
        log_error "UV installation appeared to succeed but command not found."
        log_info "Please check that ~/.local/bin is in your PATH and try again."
        log_info "You can add it with: export PATH=\"$HOME/.local/bin:\$PATH\""
        return 1
    fi

    log_success "UV installed: $(uv --version)"
    return 0
}

# Project setup
setup_project() {
    log_step "Setting up Komodo Codex Environment"

    # Remove existing installation
    if [[ -d "$INSTALL_DIR" ]]; then
        log_info "Removing existing installation..."
        rm -rf "$INSTALL_DIR"
    fi

    # Clone repository
    log_info "Cloning repository..."
    if ! run_command "git clone \"$REPO_URL\" \"$INSTALL_DIR\"" "Failed to clone repository"; then
        log_error "Repository cloning failed."
        return 1
    fi

    cd "$INSTALL_DIR" || {
        log_error "Failed to change directory to $INSTALL_DIR"
        return 1
    }

    # Install Python dependencies with UV
    log_info "Installing Python dependencies..."
    if ! run_command "uv sync --dev" "Failed to install Python dependencies"; then
        log_warn "UV dependency installation failed. Attempting fallback with pip..."

        # Get Python command from config
        local python_cmd=""
        if [[ -f "${INSTALL_DIR}/.python_config" ]]; then
            source "${INSTALL_DIR}/.python_config"
            python_cmd="$KOMODO_PYTHON_CMD"
        else
            python_cmd="python3"
            if ! command_exists python3; then
                python_cmd="python"
            fi
        fi

        # Create and activate virtual environment
        log_info "Creating virtual environment..."
        if ! run_command "$python_cmd -m venv .venv" "Failed to create virtual environment"; then
            log_error "Virtual environment creation failed."
            return 1
        fi

        # Activate virtual environment
        source .venv/bin/activate || {
            log_error "Failed to activate virtual environment."
            return 1
        }

        # Install dependencies with pip
        log_info "Installing dependencies with pip..."
        if ! run_command "pip install -e ." "Failed to install dependencies with pip"; then
            log_error "Dependency installation failed."
            return 1
        fi
    fi

    # Verify installation with multiple methods
    log_info "Verifying installation..."

    # Method 1: Try uv run with entry point
    if command_exists uv; then
        log_debug "Attempting verification with: uv run komodo-codex-env --version"
        if uv run komodo-codex-env --version >/dev/null 2>&1; then
            log_success "Installation verified successfully (uv entry point)"
            return 0
        else
            log_debug "Entry point verification failed, trying alternative methods..."
        fi
    fi

    # Method 2: Try direct module execution with uv
    if command_exists uv; then
        log_debug "Attempting verification with: uv run python -m komodo_codex_env.cli --version"
        if uv run python -m komodo_codex_env.cli --version >/dev/null 2>&1; then
            log_success "Installation verified successfully (uv module)"
            return 0
        else
            log_debug "UV module verification failed, trying venv activation..."
        fi
    fi

    # Method 3: Try with activated virtual environment
    if [[ -d .venv ]]; then
        log_debug "Attempting verification with activated venv"
        if bash -c "source .venv/bin/activate && python -m komodo_codex_env.cli --version" >/dev/null 2>&1; then
            log_success "Installation verified successfully (activated venv)"
            return 0
        else
            log_debug "Activated venv verification failed, trying direct path..."
        fi
    fi

    # Method 4: Try direct execution from venv
    if [[ -f .venv/bin/python ]]; then
        log_debug "Attempting verification with: .venv/bin/python -m komodo_codex_env.cli --version"
        if .venv/bin/python -m komodo_codex_env.cli --version >/dev/null 2>&1; then
            log_success "Installation verified successfully (direct venv)"
            return 0
        else
            log_debug "Direct venv verification failed"
        fi
    fi

    # All methods failed
    log_error "Installation verification failed with all methods"
    log_info "Trying to diagnose the issue..."

    # Diagnostic information
    if [[ -d .venv ]]; then
        log_info "Virtual environment exists at: $(pwd)/.venv"
        if [[ -f .venv/bin/python ]]; then
            log_info "Python executable found in venv"
            # Try to show what happens when we run it
            log_debug "Attempting to run with verbose output..."
            .venv/bin/python -m komodo_codex_env.cli --version 2>&1 | head -10 | while read line; do
                log_debug "Output: $line"
            done
        else
            log_error "Python executable not found in venv"
        fi
    else
        log_error "Virtual environment directory not found"
    fi

    return 1
}

# Shell integration
setup_shell_integration() {
    log_step "Setting up Shell Integration"

    local shell_rc=""
    local shell_name=$(basename "$SHELL")

    case "$shell_name" in
        "bash")
            shell_rc="$HOME/.bashrc"
            [[ -f "$HOME/.bash_profile" ]] && shell_rc="$HOME/.bash_profile"
            ;;
        "zsh")
            shell_rc="$HOME/.zshrc"
            ;;
        "fish")
            shell_rc="$HOME/.config/fish/config.fish"
            ;;
        *)
            log_warn "Unknown shell: $shell_name"
            shell_rc="$HOME/.profile"
            ;;
    esac

    # Create alias and path setup
    local setup_script="${INSTALL_DIR}/setup_env.sh"
    cat > "$setup_script" << 'EOF'
#!/bin/bash
# Komodo Codex Environment Setup

# Add UV to PATH if not already there
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    export PATH="$HOME/.local/bin:$PATH"
fi

# Add pub-cache bin to PATH for FVM
if [[ -d "$HOME/.pub-cache/bin" ]] && [[ ":$PATH:" != *":$HOME/.pub-cache/bin:"* ]]; then
    export PATH="$PATH:$HOME/.pub-cache/bin"
fi

# Add FVM default Flutter to PATH if it exists
if [[ -d "$HOME/.fvm/default/bin" ]] && [[ ":$PATH:" != *":$HOME/.fvm/default/bin:"* ]]; then
    export PATH="$PATH:$HOME/.fvm/default/bin"
fi

# Add pyenv to PATH if it exists
if [[ -d "$HOME/.pyenv/bin" ]]; then
    export PATH="$HOME/.pyenv/bin:$PATH"
    eval "$(pyenv init -)"
fi

# Load Python configuration
if [[ -f "$HOME/.komodo-codex-env/.python_config" ]]; then
    source "$HOME/.komodo-codex-env/.python_config"
fi

# Virtual environment
if [[ -d "$HOME/.komodo-codex-env/.venv" ]]; then
    source "$HOME/.komodo-codex-env/.venv/bin/activate"
fi

# Komodo Codex Environment aliases
if command -v uv >/dev/null 2>&1; then
    alias komodo-codex-env="cd $HOME/.komodo-codex-env && PYTHONPATH=src uv run python -m komodo_codex_env.cli"
else
    alias komodo-codex-env="cd $HOME/.komodo-codex-env && PYTHONPATH=src python -m komodo_codex_env.cli"
fi

alias kce="komodo-codex-env"
alias kce-setup="komodo-codex-env setup"
alias kce-status="komodo-codex-env flutter-status"
alias kce-docs="komodo-codex-env fetch-docs"
alias kce-deps="komodo-codex-env check-deps"
alias kce-update="cd $HOME/.komodo-codex-env && git pull && (uv sync --dev || pip install -e .)"

# FVM Flutter aliases (after setup)
alias kce-fvm-list="komodo-codex-env fvm-list"
alias kce-fvm-install="komodo-codex-env fvm-install"
alias kce-fvm-use="komodo-codex-env fvm-use"
alias kce-fvm-releases="komodo-codex-env fvm-releases"
alias flutter="fvm flutter"
alias dart="fvm dart"

# Function for easy setup with all options (uses FVM)
# This function runs the CLI setup with default values including:
# - Configurable platform support (web by default)
# - KDF documentation download
# - Verbose output for debugging
kce-full-setup() {
    local flutter_version="${1:-$FLUTTER_VERSION}"
    komodo-codex-env setup \
        --flutter-version "$flutter_version" \
        --install-method precompiled \
        --install-type "$INSTALL_TYPE" \
        --platforms "$PLATFORMS" \
        --kdf-docs \
        --verbose
}

# Convenience function for web-only setup
kce-web-setup() {
    local flutter_version="${1:-$FLUTTER_VERSION}"
    komodo-codex-env setup \
        --flutter-version "$flutter_version" \
        --install-method precompiled \
        --install-type "$INSTALL_TYPE" \
        --platforms web \
        --kdf-docs \
        --verbose
}

# Convenience function for full mobile setup (web + android)
kce-mobile-setup() {
    local flutter_version="${1:-$FLUTTER_VERSION}"
    komodo-codex-env setup \
        --flutter-version "$flutter_version" \
        --install-method precompiled \
        --install-type "$INSTALL_TYPE" \
        --platforms web,android \
        --kdf-docs \
        --verbose
}

# Convenience function for all platforms setup
kce-all-platforms-setup() {
    local flutter_version="${1:-$FLUTTER_VERSION}"
    komodo-codex-env setup \
        --flutter-version "$flutter_version" \
        --install-method precompiled \
        --install-type "$INSTALL_TYPE" \
        --platforms web,android,linux \
        --kdf-docs \
        --verbose
}

# FVM helper functions
kce-flutter() {
    fvm flutter "$@"
}

kce-dart() {
    fvm dart "$@"
}
EOF

    # Add source line to shell rc if not already there
    local source_line="source \"${setup_script}\""
    if [[ -f "$shell_rc" ]] && ! grep -q "setup_env.sh" "$shell_rc"; then
        echo "" >> "$shell_rc"
        echo "# Komodo Codex Environment" >> "$shell_rc"
        echo "$source_line" >> "$shell_rc"
        log_success "Added to $shell_rc"
    elif [[ ! -f "$shell_rc" ]]; then
        echo "$source_line" > "$shell_rc"
        log_success "Created $shell_rc"
    else
        log_info "Shell integration already exists in $shell_rc"
    fi

    # Make setup script executable
    chmod +x "$setup_script"
    return 0
}

# Install FVM (Flutter Version Management) for the specified user
install_fvm_for_user() {
    local target_user="${1:-${USER:-$(whoami 2>/dev/null || echo 'root')}}"
    local user_home="${2:-$HOME}"

    log_info "Installing FVM for user: $target_user"

    # Check if FVM is already installed for this user
    if sudo -u "$target_user" bash -c "command -v fvm >/dev/null 2>&1"; then
        log_info "FVM already installed for user $target_user"
        return 0
    fi

    # Use the official FVM install script which handles all dependencies
    log_info "Installing FVM using official install script..."
    if sudo -u "$target_user" bash -c "cd '$user_home' && curl -fsSL https://fvm.app/install.sh | bash"; then
        log_success "FVM installed successfully for user $target_user"

        # Ensure FVM is in PATH for the user's shell profiles
        local shell_profiles=("$user_home/.bashrc" "$user_home/.zshrc" "$user_home/.profile")
        local path_line='export PATH="$PATH:$HOME/.pub-cache/bin"'

        for profile in "${shell_profiles[@]}"; do
            if [[ -f "$profile" ]] && ! grep -q ".pub-cache/bin" "$profile"; then
                echo "" | sudo -u "$target_user" tee -a "$profile" >/dev/null
                echo "# Added by Komodo Codex Environment - FVM support" | sudo -u "$target_user" tee -a "$profile" >/dev/null
                echo "$path_line" | sudo -u "$target_user" tee -a "$profile" >/dev/null
            fi
        done

        return 0
    else
        log_warn "FVM installation failed for user $target_user using official script"
        return 1
    fi
}

# Install FVM for both komodo user and root user
install_fvm() {
    log_step "Installing FVM (Flutter Version Management)"

    # Get current user, fallback to whoami or default
    local current_user="${USER:-$(whoami 2>/dev/null || echo 'root')}"

    # Install FVM for current user
    install_fvm_for_user "$current_user" "$HOME"

    # If running as root or with root privileges, also install for komodo user
    if [[ $EUID -eq 0 ]] || sudo -n true 2>/dev/null; then
        if id "komodo" &>/dev/null; then
            local komodo_home
            komodo_home=$(eval echo "~komodo")
            install_fvm_for_user "komodo" "$komodo_home"
        fi

        # If allow-root flag is set and we're root, ensure FVM is available for root too
        if [[ "$ALLOW_ROOT" = true ]] && [[ $EUID -eq 0 ]]; then
            install_fvm_for_user "root" "/root"
        fi
    fi

    return 0
}

# Create non-root user for installation
create_non_root_user() {
    log_step "Creating non-root user for installation"

    local username="komodo"

    # Check if user already exists
    if id "$username" &>/dev/null; then
        log_info "User $username already exists, skipping creation"
        return 0
    fi

    log_info "Creating user $username..."
    if ! run_command "useradd -m -s /bin/bash \"$username\"" "Failed to create user $username"; then
        log_error "User creation failed."
        return 1
    fi

    # Add user to sudo group if it exists
    if getent group sudo >/dev/null; then
        run_command "usermod -aG sudo \"$username\"" "Failed to add user to sudo group" || true
    elif getent group wheel >/dev/null; then
        run_command "usermod -aG wheel \"$username\"" "Failed to add user to wheel group" || true
    fi

    # Allow passwordless sudo
    echo "$username ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/$username
    chmod 0440 /etc/sudoers.d/$username

    log_success "User $username created"
    return 0
}

# Check for alternative non-root users and switch to them
check_and_switch_user() {
    # List of preferred non-root users to check for
    local preferred_users=("ubuntu" "ec2-user" "centos" "fedora" "admin" "user")

    for user in "${preferred_users[@]}"; do
        if id "$user" &>/dev/null; then
            log_info "Found non-root user: $user"
            log_info "Switching to user $user for installation..."

            # Set up environment for the target user
            local user_home=$(eval echo "~$user")
            local user_install_dir="${user_home}/.komodo-codex-env"

            # Export variables for the switched user
            export INSTALL_DIR="$user_install_dir"
            export HOME="$user_home"
            export USER="$user"

            # Re-execute this script as the target user
            exec sudo -u "$user" -H bash -c "
                export INSTALL_DIR='$user_install_dir'
                export HOME='$user_home'
                export USER='$user'
                export FLUTTER_VERSION='$FLUTTER_VERSION'
                export INSTALL_TYPE='$INSTALL_TYPE'
                export ALLOW_ROOT='$ALLOW_ROOT'
                export DEBUG='$DEBUG'
                $(cat "$0")
            "
        fi
    done

    # If no preferred user found, continue as current user
    return 0
}

# Main installation function
main() {
    log_step "Komodo Codex Environment Installer"
    log_info "OS: $(get_os) $(get_arch)"

    # Check if running as root and try to switch to a non-root user
    if [[ $EUID -eq 0 ]]; then
        if [[ "$ALLOW_ROOT" = true ]]; then
            log_warn "Running as root with --allow-root flag"
        else
            log_info "Detected root user - checking for alternative non-root users..."
            check_and_switch_user

            # If we reach here, no alternative user was found
            log_error "This script should not be run as root"
            log_info "Consider creating a non-root user (e.g., ubuntu, ec2-user) or use --allow-root to bypass this check"
            log_info "Available options:"
            log_info "  1. Create a user: sudo useradd -m -s /bin/bash ubuntu"
            log_info "  2. Run with: --allow-root flag"
            exit 1
        fi
    fi

    log_info "Install directory: $INSTALL_DIR"

    # Create install directory
    mkdir -p "$INSTALL_DIR"

    # Track installation steps for resume capability
    local install_steps=(
        "install_system_deps"
        "setup_opt_directory"
        "install_uv"
        "setup_project"
        "setup_shell_integration"
    )

    # Run installation steps with error handling
    local failed_step=""
    for step in "${install_steps[@]}"; do
        log_info "Running step: $step"
        if ! $step; then
            failed_step="$step"
            log_error "Step $step failed. Installation may be incomplete."
            break
        fi
    done

    if [[ -n "$failed_step" ]]; then
        log_step "Installation Failed"
        log_error "Installation failed at step: $failed_step"
        log_info "You may need to fix the issues and try again."
        log_info "For debugging, run with: bash $0 --debug"
        exit 1
    else
        log_step "Installation Complete!"
        log_success "Komodo Codex Environment has been installed successfully!"

        echo ""
        log_info "Quick start:"
        log_info "1. Restart your terminal or run: source ~/.$(basename $SHELL)rc"
        log_info "2. Run full setup: kce-full-setup"
        log_info "3. Check status: kce-status"
        echo ""
        log_info "Installation completed successfully!"
        log_info ""
        log_info "Available commands:"
        log_info "  kce                 - Run komodo-codex-env"
        log_info "  kce-setup          - Run basic setup"
        log_info "  kce-full-setup [version] - Run setup with configured platforms (with FVM)"
        log_info "  kce-web-setup [version] - Run web-only setup (fastest)"
        log_info "  kce-mobile-setup [version] - Run web + Android setup"
        log_info "  kce-all-platforms-setup [version] - Run setup with web + Android + Linux"
        log_info "  kce-status         - Check Flutter status"
        log_info "  kce-docs           - Fetch documentation"
        log_info "  kce-deps           - Check dependencies"
        log_info "  kce-update         - Update the tool"
        log_info ""
        log_info "FVM Flutter commands:"
        log_info "  kce-fvm-list       - List installed Flutter versions"
        log_info "  kce-fvm-install    - Install Flutter version"
        log_info "  kce-fvm-use        - Switch Flutter version"
        log_info "  kce-fvm-releases   - List available Flutter releases"
        log_info "  flutter / dart     - Use FVM Flutter/Dart (after setup)"
        echo ""
        log_info "For help: kce --help"
        log_info ""
        log_info "Flutter version management:"
        log_info "  Current version: $FLUTTER_VERSION"
        log_info "  Current platforms: $PLATFORMS"
        log_info "  Examples:"
        log_info "    kce-web-setup 3.29.3         - Web only (fastest)"
        log_info "    kce-mobile-setup 3.29.3      - Web + Android"
        log_info "    kce-all-platforms-setup 3.29.3 - Web + Android + Linux"
        log_info "    kce-full-setup 3.29.3        - Use configured platforms"
        log_info "  List versions: kce-fvm-releases"

        # FVM verification note
        echo ""
        log_info "Note: FVM (Flutter Version Management) has been installed for all users."
        log_info "To verify FVM installation: python3 ~/.komodo-codex-env/scripts/verify_fvm.py"
        log_info "If FVM is not found, restart your terminal and run the setup."

        # Offer to run setup immediately
        echo ""
        read -p "Do you want to run the full setup now? This will install Flutter $FLUTTER_VERSION with platforms: $PLATFORMS. (Y/n): " -n 1 -r
        echo
        if [[ -z "$REPLY" ]] || [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Running full setup with Flutter version $FLUTTER_VERSION..."
            log_info "This includes: Flutter $FLUTTER_VERSION, platforms ($PLATFORMS), and KDF docs"
            source "${INSTALL_DIR}/setup_env.sh"
            kce-full-setup "$FLUTTER_VERSION"
        else
            log_info "You can run the setup later with: kce-full-setup [flutter-version]"
        fi
    fi
}

# Run main function
main "$@"
