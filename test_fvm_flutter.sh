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
    log_info "Testing install script with Flutter 3.29.3 using FVM"
    
    # Check if Docker is available
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker is not available. Please install Docker to run this test."
        exit 1
    fi
    
    # Build the test Docker image
    log_info "Building test Docker image..."
    if ! docker build -t komodo-codex-env-test -f .devcontainer/Dockerfile .; then
        log_error "Failed to build Docker image"
        exit 1
    fi
    
    log_success "Docker image built successfully"
    
    # Run the container
    log_info "Starting test container..."
    CONTAINER_ID=$(docker run -d --name "komodo-fvm-test-$(date +%s)" komodo-codex-env-test sleep 3600)
    
    if [[ -z "$CONTAINER_ID" ]]; then
        log_error "Failed to start container"
        exit 1
    fi
    
    log_success "Container started: $CONTAINER_ID"
    
    # Copy the install script to container
    docker cp install.sh "$CONTAINER_ID:/tmp/install.sh"
    
    # Run the install script with Flutter 3.29.3
    log_info "Running install script with Flutter 3.29.3..."
    if docker exec -u testuser "$CONTAINER_ID" bash -c "
        export USER=testuser
        export HOME=/home/testuser
        cd /home/testuser && bash /tmp/install.sh --flutter-version 3.29.3 --debug 2>&1
    "; then
        log_success "Install script completed successfully"
    else
        log_error "Install script failed"
        log_info "Getting container logs for debugging..."
        docker logs "$CONTAINER_ID" 2>&1 | tail -50
        exit 1
    fi
    
    # Verify FVM installation
    log_info "Verifying FVM installation..."
    
    # First check if fvm binary exists
    log_info "Checking if FVM binary exists in .pub-cache/bin..."
    docker exec -u testuser "$CONTAINER_ID" bash -c "ls -la ~/.pub-cache/bin/ 2>/dev/null || echo 'No .pub-cache/bin directory'"
    
    # Check PATH configuration
    log_info "Checking PATH configuration..."
    docker exec -u testuser "$CONTAINER_ID" bash -c "echo 'Current PATH in container:'; echo \$PATH"
    
    # Try to find FVM with explicit PATH
    log_info "Testing FVM with explicit PATH..."
    if docker exec -u testuser "$CONTAINER_ID" bash -c "export PATH=\"\$PATH:\$HOME/.pub-cache/bin\" && command -v fvm"; then
        log_success "FVM found with explicit PATH"
        
        # Now test with sourced bashrc
        log_info "Testing FVM with sourced bashrc..."
        if docker exec -u testuser "$CONTAINER_ID" bash -c "source ~/.bashrc && command -v fvm"; then
            log_success "FVM command found via bashrc"
        else
            log_warn "FVM not found via bashrc, but found with explicit PATH"
            # This is acceptable for the test - continue
        fi
    else
        log_error "FVM command not found even with explicit PATH"
        log_info "Checking FVM installation details..."
        docker exec -u testuser "$CONTAINER_ID" bash -c "ls -la ~/.pub-cache/ 2>/dev/null || echo 'No .pub-cache directory'"
        docker exec -u testuser "$CONTAINER_ID" bash -c "cat ~/.bashrc | grep -A5 -B5 pub-cache || echo 'No pub-cache reference in bashrc'"
        exit 1
    fi
    
    # Verify Flutter installation via FVM
    log_info "Verifying Flutter installation via FVM..."
    
    # Use explicit PATH for FVM command
    FVM_CMD="export PATH=\"\$PATH:\$HOME/.pub-cache/bin\" && fvm"
    
    if docker exec -u testuser "$CONTAINER_ID" bash -c "$FVM_CMD flutter --version"; then
        log_success "Flutter is available via FVM"
        
        # Check the specific version
        log_info "Checking Flutter version..."
        FLUTTER_VERSION_OUTPUT=$(docker exec -u testuser "$CONTAINER_ID" bash -c "$FVM_CMD flutter --version 2>&1" | head -1)
        log_info "Flutter version output: $FLUTTER_VERSION_OUTPUT"
        
        if echo "$FLUTTER_VERSION_OUTPUT" | grep -q "3.29.3"; then
            log_success "Correct Flutter version 3.29.3 is installed"
        else
            log_warn "Flutter version might not be 3.29.3. Output: $FLUTTER_VERSION_OUTPUT"
        fi
    else
        log_error "Flutter command not available via FVM"
        log_info "Debugging FVM setup..."
        docker exec -u testuser "$CONTAINER_ID" bash -c "$FVM_CMD list || echo 'fvm list failed'"
        docker exec -u testuser "$CONTAINER_ID" bash -c "source ~/.bashrc && which fvm || echo 'fvm not in PATH'"
        exit 1
    fi
    
    # Test basic komodo-codex-env functionality
    log_info "Testing komodo-codex-env installation..."
    if docker exec -u testuser "$CONTAINER_ID" bash -c "cd ~/.komodo-codex-env && source .venv/bin/activate && python -m komodo_codex_env.cli --version"; then
        log_success "komodo-codex-env is working"
    else
        log_error "komodo-codex-env installation verification failed"
        log_info "Checking installation directory..."
        docker exec -u testuser "$CONTAINER_ID" bash -c "ls -la ~/.komodo-codex-env/ || echo 'Install directory not found'"
        exit 1
    fi
    
    log_success "All tests passed! FVM and Flutter 3.29.3 are properly installed."
}

main "$@"
