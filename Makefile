.PHONY: help install dev-install test lint format type-check clean check-deps setup dev run-cli update docs
.DEFAULT_GOAL := help

# Colors for output
YELLOW := \033[1;33m
GREEN := \033[0;32m
BLUE := \033[0;34m
RED := \033[0;31m
NC := \033[0m

help: ## Show this help message
	@echo "$(BLUE)Komodo Codex Environment - Development Commands$(NC)"
	@echo ""
	@echo "$(YELLOW)Setup Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E '(setup|install|dev)' | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Development Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E '(test|lint|format|type|clean|run)' | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Utility Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -vE '(setup|install|dev|test|lint|format|type|clean|run)' | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

setup: check-rye install check-deps ## Complete development environment setup
	@echo "$(GREEN)Development environment setup complete!$(NC)"
	@echo "$(YELLOW)Run 'make help' to see available commands$(NC)"

check-rye: ## Check if Rye is installed
	@if ! command -v rye >/dev/null 2>&1; then \
		echo "$(RED)Error: Rye is not installed.$(NC)"; \
		echo "$(YELLOW)Install with: curl -sSf https://rye.astral.sh/get | bash$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✓ Rye is installed$(NC)"

install: check-rye ## Install project dependencies
	@echo "$(YELLOW)Installing dependencies...$(NC)"
	rye sync

dev-install: install ## Install with development dependencies (alias for install)
	@echo "$(GREEN)✓ Development dependencies installed$(NC)"

test: ## Run all tests
	@echo "$(YELLOW)Running tests...$(NC)"
	rye run pytest

test-verbose: ## Run tests with verbose output
	@echo "$(YELLOW)Running tests with verbose output...$(NC)"
	rye run pytest -v

test-coverage: ## Run tests with coverage report
	@echo "$(YELLOW)Running tests with coverage...$(NC)"
	rye run pytest --cov=src/komodo_codex_env --cov-report=html --cov-report=term

lint: ## Run linting checks
	@echo "$(YELLOW)Running linting checks...$(NC)"
	@if command -v ruff >/dev/null 2>&1; then \
		rye run ruff check src/; \
	else \
		echo "$(YELLOW)Ruff not installed, skipping lint check$(NC)"; \
	fi

format: ## Format code
	@echo "$(YELLOW)Formatting code...$(NC)"
	@if command -v ruff >/dev/null 2>&1; then \
		rye run ruff format src/; \
	elif command -v black >/dev/null 2>&1; then \
		rye run black src/; \
	else \
		echo "$(YELLOW)No formatter available, install ruff or black$(NC)"; \
	fi

type-check: ## Run type checking
	@echo "$(YELLOW)Running type checks...$(NC)"
	@if rye show | grep -q mypy; then \
		rye run mypy src/; \
	else \
		echo "$(YELLOW)mypy not installed, skipping type check$(NC)"; \
	fi

check-deps: ## Check system dependencies
	@echo "$(YELLOW)Checking system dependencies...$(NC)"
	rye run python -m komodo_codex_env.cli check-deps

run-cli: ## Run the CLI tool (use ARGS="..." for arguments)
	@echo "$(YELLOW)Running CLI tool...$(NC)"
	rye run python -m komodo_codex_env.cli $(ARGS)

docs: ## Fetch documentation
	@echo "$(YELLOW)Fetching documentation...$(NC)"
	rye run python -m komodo_codex_env.cli fetch-docs

clean: ## Clean up build artifacts and cache
	@echo "$(YELLOW)Cleaning up...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/

dev: setup ## Alias for setup - complete development environment setup

update: ## Update dependencies
	@echo "$(YELLOW)Updating dependencies...$(NC)"
	rye sync --update-all

# Development workflow targets
ci: lint type-check test ## Run all CI checks (lint, type-check, test)

pre-commit: format lint type-check test ## Run pre-commit checks
	@echo "$(GREEN)✓ All pre-commit checks passed$(NC)"

# Quick development commands
quick-test: ## Run tests without coverage (faster)
	rye run pytest -x

debug-test: ## Run tests with debug output
	rye run pytest -v -s

# Build and distribution
build: clean ## Build the package
	@echo "$(YELLOW)Building package...$(NC)"
	rye build

install-local: build ## Install package locally
	@echo "$(YELLOW)Installing package locally...$(NC)"
	pip install dist/*.whl