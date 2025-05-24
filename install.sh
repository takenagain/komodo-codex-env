#!/bin/bash

# Komodo Codex Environment - One-Line Installer with FVM
# Usage: curl -fsSL https://raw.githubusercontent.com/takenagain/komodo-codex-env/main/install.sh | bash
# Or: bash <(curl -fsSL https://raw.githubusercontent.com/takenagain/komodo-codex-env/main/install.sh)
# This script installs FVM (Flutter Version Management) for better Flutter version control

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

# Parse command line arguments
for arg in "$@"; do
    case "$arg" in
        --allow-root)
            ALLOW_ROOT=true
            ;;
        --debug)
            DEBUG=true
            set -x  # Enable bash debug mode
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
                    
                    # Install core dependencies
                    log_info "Installing core dependencies..."
                    run_command "sudo apt-get install -y curl git unzip xz-utils zip build-essential wget python3-pip python3-full" "Failed to install core dependencies" || true
                    
                    # Install additional dependencies
                    log_info "Installing additional dependencies..."
                    run_command "sudo apt-get install -y libglu1-mesa software-properties-common libssl-dev libffi-dev libbz2-dev libreadline-dev libsqlite3-dev llvm libncurses5-dev libncursesw5-dev tk-dev libxml2-dev libxmlsec1-dev liblzma-dev" "Failed to install additional dependencies" || true
                    
                    # Try to install Python 3.13 from deadsnakes PPA
                    if ! command_exists python${REQUIRED_PYTHON_VERSION}; then
                        log_info "Adding deadsnakes PPA for Python ${REQUIRED_PYTHON_VERSION}..."
                        run_command "sudo add-apt-repository -y ppa:deadsnakes/ppa" "Failed to add deadsnakes PPA" || true
                        run_command "sudo apt-get update -qq" "Failed to update apt after adding PPA" || true
                        run_command "sudo apt-get install -y python${REQUIRED_PYTHON_VERSION} python${REQUIRED_PYTHON_VERSION}-dev python${REQUIRED_PYTHON_VERSION}-venv python${REQUIRED_PYTHON_VERSION}-distutils" "Failed to install Python ${REQUIRED_PYTHON_VERSION}" || true
                    fi
                    
                    # Install Dart SDK for FVM
                    if ! command_exists dart; then
                        log_info "Installing Dart SDK..."
                        run_command "sudo apt-get install -y apt-transport-https" "Failed to install apt-transport-https" || true
                        run_command "wget -qO- https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -" "Failed to add Google's signing key" || true
                        run_command "sudo sh -c 'wget -qO- https://storage.googleapis.com/download.dartlang.org/linux/debian/dart_stable.list > /etc/apt/sources.list.d/dart_stable.list'" "Failed to add Dart repository" || true
                        run_command "sudo apt-get update" "Failed to update apt after adding Dart repository" || true
                        run_command "sudo apt-get install -y dart" "Failed to install Dart" || true
                    fi
                    ;;
                    
                "fedora"|"rhel"|"centos")
                    log_info "Installing Fedora/RHEL dependencies..."
                    run_command "sudo dnf install -y curl git unzip xz zip mesa-libGLU gcc openssl-devel bzip2-devel libffi-devel readline-devel sqlite-devel wget llvm ncurses-devel tk-devel libxml2-devel xmlsec1-devel xz-devel" "Failed to install dependencies" || true
                    
                    # Add Dart repository and install Dart
                    if ! command_exists dart; then
                        log_info "Installing Dart SDK..."
                        run_command "sudo dnf install -y gnupg2" "Failed to install gnupg2" || true
                        run_command "sudo dnf install -y dart" "Failed to install Dart" || true
                    fi
                    ;;
                    
                "arch"|"manjaro")
                    log_info "Installing Arch dependencies..."
                    run_command "sudo pacman -Sy --noconfirm curl git unzip xz zip glu base-devel openssl bzip2 libffi readline sqlite wget llvm ncurses tk libxml2 xmlsec xz" "Failed to install dependencies" || true
                    
                    # Install Dart
                    if ! command_exists dart; then
                        log_info "Installing Dart SDK..."
                        run_command "sudo pacman -Sy --noconfirm dart" "Failed to install Dart" || true
                    fi
                    ;;
                    
                *)
                    log_warn "Unknown Linux distribution: $distro"
                    log_warn "Please ensure the following packages are installed:"
                    log_warn "curl, git, unzip, xz-utils, zip, libglu1-mesa, build tools, dart"
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

# Python installation and verification
setup_python() {
    log_step "Setting up Python Environment"
    
    # Check for Python
    local python_cmd=""
    local python_version=""
    
    log_info "Checking for existing Python installation..."
    # Try different Python commands
    for cmd in python${REQUIRED_PYTHON_VERSION} python3.11 python3.10 python3.9 python3 python; do
        if command_exists "$cmd"; then
            log_debug "Found Python command: $cmd"
            if python_version=$($cmd --version 2>&1 | cut -d' ' -f2); then
                log_debug "Python version: $python_version"
                if is_version_greater_equal "$python_version" "$PYTHON_MIN_VERSION"; then
                    python_cmd="$cmd"
                    log_debug "Selected Python command: $python_cmd (version $python_version)"
                    break
                else
                    log_debug "Python version $python_version is too old (need >= $PYTHON_MIN_VERSION)"
                fi
            else
                log_debug "Failed to get version for $cmd"
            fi
        fi
    done
    
    if [[ -z "$python_cmd" ]]; then
        log_warn "Python ${PYTHON_MIN_VERSION}+ not found. Attempting to install..."
        
        # Try pyenv installation as fallback
        if ! command_exists pyenv; then
            log_info "Installing pyenv..."
            if ! run_command "curl https://pyenv.run | bash" "Failed to install pyenv"; then
                log_error "Pyenv installation failed. Please install Python ${PYTHON_MIN_VERSION}+ manually."
                log_info "You can try: sudo apt-get install python3.9 python3.9-venv python3.9-dev"
                log_info "Or visit https://www.python.org/downloads/ for installation instructions."
                return 1
            fi
            
            # Add pyenv to PATH
            export PYENV_ROOT="$HOME/.pyenv"
            [[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
            
            if ! command_exists pyenv; then
                log_error "Pyenv installation succeeded but command not found. Please restart your shell and run the installer again."
                return 1
            fi
            
            if ! run_command "eval \"\$(pyenv init -)\"" "Failed to initialize pyenv"; then
                log_error "Pyenv initialization failed."
                return 1
            fi
        fi
        
        log_info "Installing Python ${REQUIRED_PYTHON_VERSION} via pyenv..."
        if ! run_command "pyenv install ${REQUIRED_PYTHON_VERSION}" "Failed to install Python ${REQUIRED_PYTHON_VERSION}"; then
            log_error "Python installation failed. Attempting fallback to Python 3.9..."
            if ! run_command "pyenv install 3.9.0" "Failed to install Python 3.9.0"; then
                log_error "All Python installation attempts failed."
                return 1
            else
                REQUIRED_PYTHON_VERSION="3.9.0"
                run_command "pyenv global 3.9.0" "Failed to set global Python version to 3.9.0" || true
            fi
        else
            run_command "pyenv global ${REQUIRED_PYTHON_VERSION}" "Failed to set global Python version to ${REQUIRED_PYTHON_VERSION}" || true
        fi
        
        # Try to use the installed python
        if command_exists pyenv; then
            python_cmd="$(pyenv which python)"
            if [[ -z "$python_cmd" ]]; then
                python_cmd="python"  # Fallback
            fi
            python_version="${REQUIRED_PYTHON_VERSION}"
        else
            log_error "Pyenv or Python installation failed."
            return 1
        fi
    fi
    
    # Verify Python installation
    if ! command_exists "$python_cmd"; then
        log_error "Python command '$python_cmd' not found after installation."
        return 1
    fi
    
    # Check Python version
    if ! python_version=$("$python_cmd" --version 2>&1 | cut -d' ' -f2); then
        log_error "Failed to get Python version."
        return 1
    fi
    
    # Ensure pip is available
    log_info "Checking for pip..."
    if ! "$python_cmd" -m pip --version >/dev/null 2>&1; then
        log_info "Installing pip via system package manager..."
        local os=$(get_os)
        local distro=$(get_distro)
        
        case "$os" in
            "linux")
                case "$distro" in
                    "ubuntu"|"debian")
                        if ! run_command "sudo apt-get install -y python3-pip" "Failed to install pip via apt"; then
                            log_warn "Failed to install pip via apt, trying get-pip.py as fallback..."
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
                        ;;
                    "fedora"|"rhel"|"centos")
                        if ! run_command "sudo dnf install -y python3-pip" "Failed to install pip via dnf"; then
                            log_error "Pip installation failed."
                            return 1
                        fi
                        ;;
                    "arch"|"manjaro")
                        if ! run_command "sudo pacman -Sy --noconfirm python-pip" "Failed to install pip via pacman"; then
                            log_error "Pip installation failed."
                            return 1
                        fi
                        ;;
                    *)
                        log_warn "Unknown Linux distribution, trying get-pip.py..."
                        if ! run_command "curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py" "Failed to download pip installer"; then
                            log_error "Failed to download pip installer."
                            return 1
                        fi
                        if ! run_command "$python_cmd get-pip.py --break-system-packages" "Failed to install pip"; then
                            log_error "Pip installation failed."
                            return 1
                        fi
                        rm -f get-pip.py
                        ;;
                esac
                ;;
            "macos")
                log_warn "macOS detected, trying get-pip.py..."
                if ! run_command "curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py" "Failed to download pip installer"; then
                    log_error "Failed to download pip installer."
                    return 1
                fi
                if ! run_command "$python_cmd get-pip.py" "Failed to install pip"; then
                    log_error "Pip installation failed."
                    return 1
                fi
                rm -f get-pip.py
                ;;
        esac
    fi
    
    log_success "Python ${python_version} available at: $(which $python_cmd)"
    echo "export KOMODO_PYTHON_CMD=$python_cmd" > "${INSTALL_DIR}/.python_config"
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

# Git configuration
setup_git() {
    log_step "Configuring Git"
    
    if ! command_exists git; then
        log_error "Git not found after installation"
        return 1
    fi
    
    # Set basic git configuration if not set
    if [[ -z "$(git config --global user.name 2>/dev/null || true)" ]]; then
        log_info "Setting default git user.name..."
        git config --global user.name "Komodo Developer"
    fi
    
    if [[ -z "$(git config --global user.email 2>/dev/null || true)" ]]; then
        log_info "Setting default git user.email..."
        git config --global user.email "developer@local"
    fi
    
    log_success "Git configured"
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
kce-full-setup() {
    local flutter_version="${1:-3.32.0}"
    komodo-codex-env setup \
        --flutter-version "$flutter_version" \
        --install-method precompiled \
        --platforms web,android,linux \
        --kdf-docs \
        --verbose \
        "$@"
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

# Main installation function
main() {
    log_step "Komodo Codex Environment Installer"
    log_info "OS: $(get_os) $(get_arch)"
    log_info "Install directory: $INSTALL_DIR"
    
    # Check if running as root
    if [[ $EUID -eq 0 ]]; then
        if [[ "$ALLOW_ROOT" = true ]]; then
            log_warn "Running as root with --allow-root flag"
        else
            log_error "This script should not be run as root"
            log_info "You can use --allow-root to bypass this check or create a non-root user"
            exit 1
        fi
    fi
    
    # Create install directory
    mkdir -p "$INSTALL_DIR"
    
    # Track installation steps for resume capability
    local install_steps=(
        "install_system_deps"
        "setup_python"
        "install_uv"
        "setup_git"
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
        log_info "Available commands:"
        log_info "  kce                 - Run komodo-codex-env"
        log_info "  kce-setup          - Run basic setup"
        log_info "  kce-full-setup     - Run setup with all options enabled (with FVM)"
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
        
        # Offer to run setup immediately
        echo ""
        read -p "Would you like to run the full setup now? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Running full setup..."
            source "${INSTALL_DIR}/setup_env.sh"
            kce-full-setup
        else
            log_info "You can run the setup later with: kce-full-setup"
        fi
    fi
}

# Run main function
main "$@"