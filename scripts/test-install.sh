#!/bin/bash

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

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Function to cleanup Docker containers
cleanup() {
    if [[ -n "${CONTAINER_ID:-}" ]]; then
        log_info "Cleaning up container: $CONTAINER_ID"
        docker rm -f "$CONTAINER_ID" >/dev/null 2>&1 || true
    fi
}

# Set trap for cleanup
trap cleanup EXIT

main() {
    local test_mode="${1:-basic}"
    
    log_info "Starting Docker-based install script test"
    log_info "Test mode: $test_mode"
    
    # Build the test Docker image
    log_info "Building test Docker image..."
    if ! docker build -t komodo-codex-env-test -f .devcontainer/Dockerfile .; then
        log_error "Failed to build Docker image"
        exit 1
    fi
    
    log_success "Docker image built successfully"
    
    # Run the container
    log_info "Starting test container..."
    CONTAINER_ID=$(docker run -d --name "komodo-test-$(date +%s)" komodo-codex-env-test sleep 3600)
    
    if [[ -z "$CONTAINER_ID" ]]; then
        log_error "Failed to start container"
        exit 1
    fi
    
    log_success "Container started: $CONTAINER_ID"
    
    case "$test_mode" in
        "basic")
            test_basic_install
            ;;
        "root")
            test_root_install
            ;;
        "both")
            test_basic_install
            test_root_install
            ;;
        *)
            log_error "Unknown test mode: $test_mode"
            log_info "Available modes: basic, root, both"
            exit 1
            ;;
    esac
}

test_basic_install() {
    log_info "Testing basic installation (non-root user)..."
    
    # Copy the install script to container
    docker cp install.sh "$CONTAINER_ID:/tmp/install.sh"
    
    # Run the install script
    log_info "Running install script in container..."
    if docker exec -u testuser "$CONTAINER_ID" bash -c "cd /home/testuser && bash /tmp/install.sh --debug"; then
        log_success "Install script completed successfully (non-root)"
        
        # Verify the installation
        log_info "Verifying installation..."
        if docker exec -u testuser "$CONTAINER_ID" bash -c "cd /home/testuser/.komodo-codex-env && source .venv/bin/activate && python -m komodo_codex_env.cli --version"; then
            log_success "Installation verification passed (non-root)"
            return 0
        else
            log_error "Installation verification failed (non-root)"
            return 1
        fi
    else
        log_error "Install script failed (non-root)"
        
        # Get logs for debugging
        log_info "Container logs:"
        docker logs "$CONTAINER_ID" 2>&1 | tail -50
        
        return 1
    fi
}

test_root_install() {
    log_info "Testing root installation..."
    
    # Copy the install script to container
    docker cp install.sh "$CONTAINER_ID:/tmp/install.sh"
    
    # Run the install script as root
    log_info "Running install script in container as root..."
    if docker exec -u root "$CONTAINER_ID" bash -c "cd /root && bash /tmp/install.sh --allow-root --debug"; then
        log_success "Install script completed successfully (root)"
        
        # Verify the installation
        log_info "Verifying installation..."
        if docker exec -u root "$CONTAINER_ID" bash -c "cd /root/.komodo-codex-env && source .venv/bin/activate && python -m komodo_codex_env.cli --version"; then
            log_success "Installation verification passed (root)"
            return 0
        else
            log_error "Installation verification failed (root)"
            return 1
        fi
    else
        log_error "Install script failed (root)"
        
        # Get logs for debugging
        log_info "Container logs:"
        docker logs "$CONTAINER_ID" 2>&1 | tail -50
        
        return 1
    fi
}

# Check if Docker is available
if ! command -v docker >/dev/null 2>&1; then
    log_error "Docker is not installed or not in PATH"
    exit 1
fi

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    log_error "Docker is not running or not accessible"
    exit 1
fi

# Run main function
main "$@"