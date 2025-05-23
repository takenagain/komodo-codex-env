#!/bin/bash

# Komodo Codex Environment - One-Line Installer with FVM
# Usage: curl -fsSL https://raw.githubusercontent.com/KomodoPlatform/komodo-codex-env/main/install.sh | bash
# Or: bash <(curl -fsSL https://raw.githubusercontent.com/KomodoPlatform/komodo-codex-env/main/install.sh)
# This script installs FVM (Flutter Version Management) for better Flutter version control

set -euo pipefail

# Colors and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Configuration
REPO_URL="https://github.com/KomodoPlatform/komodo-codex-env.git"
INSTALL_DIR="${HOME}/.komodo-codex-env"
PYTHON_MIN_VERSION="3.11"
REQUIRED_PYTHON_VERSION="3.13"

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

log_step() {
    echo -e "\n${CYAN}${BOLD}=== $1 ===${NC}"
}

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

# System dependency installation
install_system_deps() {
    local os=$(get_os)
    local distro=$(get_distro)
    
    log_step "Installing System Dependencies"
    
    case "$os" in
        "macos")
            if ! command_exists brew; then
                log_info "Installing Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                
                # Add brew to PATH for current session
                if [[ -f /opt/homebrew/bin/brew ]]; then
                    eval "$(/opt/homebrew/bin/brew shellenv)"
                elif [[ -f /usr/local/bin/brew ]]; then
                    eval "$(/usr/local/bin/brew shellenv)"
                fi
            fi
            
            log_info "Installing macOS dependencies..."
            brew update
            brew install curl git unzip xz zip python@${REQUIRED_PYTHON_VERSION} dart || true
            ;;
            
        "linux")
            case "$distro" in
                "ubuntu"|"debian")
                    log_info "Installing Ubuntu/Debian dependencies..."
                    sudo apt-get update -qq
                    sudo apt-get install -y \
                        curl \
                        git \
                        unzip \
                        xz-utils \
                        zip \
                        libglu1-mesa \
                        software-properties-common \
                        build-essential \
                        libssl-dev \
                        libffi-dev \
                        libbz2-dev \
                        libreadline-dev \
                        libsqlite3-dev \
                        wget \
                        llvm \
                        libncurses5-dev \
                        libncursesw5-dev \
                        tk-dev \
                        libxml2-dev \
                        libxmlsec1-dev \
                        liblzma-dev
                    
                    # Try to install Python 3.13 from deadsnakes PPA
                    if ! command_exists python${REQUIRED_PYTHON_VERSION}; then
                        log_info "Adding deadsnakes PPA for Python ${REQUIRED_PYTHON_VERSION}..."
                        sudo add-apt-repository -y ppa:deadsnakes/ppa || true
                        sudo apt-get update -qq
                        sudo apt-get install -y python${REQUIRED_PYTHON_VERSION} python${REQUIRED_PYTHON_VERSION}-dev python${REQUIRED_PYTHON_VERSION}-venv || true
                    fi
                    
                    # Install Dart SDK for FVM
                    if ! command_exists dart; then
                        log_info "Installing Dart SDK..."
                        sudo apt-get install -y dart || true
                    fi
                    ;;
                    
                "fedora"|"rhel"|"centos")
                    log_info "Installing Fedora/RHEL dependencies..."
                    sudo dnf install -y \
                        curl \
                        git \
                        unzip \
                        xz \
                        zip \
                        mesa-libGLU \
                        gcc \
                        openssl-devel \
                        bzip2-devel \
                        libffi-devel \
                        readline-devel \
                        sqlite-devel \
                        wget \
                        llvm \
                        ncurses-devel \
                        tk-devel \
                        libxml2-devel \
                        xmlsec1-devel \
                        xz-devel \
                        dart || true
                    ;;
                    
                "arch"|"manjaro")
                    log_info "Installing Arch dependencies..."
                    sudo pacman -Sy --noconfirm \
                        curl \
                        git \
                        unzip \
                        xz \
                        zip \
                        glu \
                        base-devel \
                        openssl \
                        bzip2 \
                        libffi \
                        readline \
                        sqlite \
                        wget \
                        llvm \
                        ncurses \
                        tk \
                        libxml2 \
                        xmlsec \
                        xz \
                        dart || true
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
            exit 1
            ;;
    esac
    
    log_success "System dependencies installed"
}

# Python installation and verification
setup_python() {
    log_step "Setting up Python Environment"
    
    # Check for Python
    local python_cmd=""
    local python_version=""
    
    # Try different Python commands
    for cmd in python${REQUIRED_PYTHON_VERSION} python3 python; do
        if command_exists "$cmd"; then
            python_version=$($cmd --version 2>&1 | cut -d' ' -f2)
            if is_version_greater_equal "$python_version" "$PYTHON_MIN_VERSION"; then
                python_cmd="$cmd"
                break
            fi
        fi
    done
    
    if [[ -z "$python_cmd" ]]; then
        log_error "Python ${PYTHON_MIN_VERSION}+ not found. Attempting to install..."
        
        # Try pyenv installation as fallback
        if ! command_exists pyenv; then
            log_info "Installing pyenv..."
            curl https://pyenv.run | bash
            
            # Add pyenv to PATH
            export PYENV_ROOT="$HOME/.pyenv"
            [[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
            eval "$(pyenv init -)"
        fi
        
        log_info "Installing Python ${REQUIRED_PYTHON_VERSION} via pyenv..."
        pyenv install ${REQUIRED_PYTHON_VERSION}
        pyenv global ${REQUIRED_PYTHON_VERSION}
        python_cmd="python"
        python_version=${REQUIRED_PYTHON_VERSION}
    fi
    
    log_success "Python ${python_version} available at: $(which $python_cmd)"
    echo "export KOMODO_PYTHON_CMD=$python_cmd" > "${INSTALL_DIR}/.python_config"
}

# UV package manager installation
install_uv() {
    log_step "Installing UV Package Manager"
    
    if command_exists uv; then
        log_info "UV already installed: $(uv --version)"
        return
    fi
    
    log_info "Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Add UV to current PATH
    export PATH="$HOME/.local/bin:$PATH"
    
    if ! command_exists uv; then
        log_error "UV installation failed"
        exit 1
    fi
    
    log_success "UV installed: $(uv --version)"
}

# Git configuration
setup_git() {
    log_step "Configuring Git"
    
    if ! command_exists git; then
        log_error "Git not found after installation"
        exit 1
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
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    # Install Python dependencies with UV
    log_info "Installing Python dependencies..."
    uv sync --dev
    
    # Verify installation
    log_info "Verifying installation..."
    if uv run komodo-codex-env --version >/dev/null 2>&1; then
        log_success "Installation verified successfully"
    else
        log_error "Installation verification failed"
        exit 1
    fi
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

# Komodo Codex Environment aliases
alias komodo-codex-env="cd $HOME/.komodo-codex-env && PYTHONPATH=src uv run python -m komodo_codex_env.cli"
alias kce="komodo-codex-env"
alias kce-setup="komodo-codex-env setup"
alias kce-status="komodo-codex-env flutter-status"
alias kce-docs="komodo-codex-env fetch-docs"
alias kce-deps="komodo-codex-env check-deps"
alias kce-update="cd $HOME/.komodo-codex-env && git pull && uv sync"

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
}

# Main installation function
main() {
    log_step "Komodo Codex Environment Installer"
    log_info "OS: $(get_os) $(get_arch)"
    log_info "Install directory: $INSTALL_DIR"
    
    # Check if running as root
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root"
        exit 1
    fi
    
    # Create install directory
    mkdir -p "$INSTALL_DIR"
    
    # Run installation steps
    install_system_deps
    setup_python
    install_uv
    setup_git
    setup_project
    setup_shell_integration
    
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
}

# Trap to cleanup on error
trap 'log_error "Installation failed. Check the output above for errors."' ERR

# Run main function
main "$@"