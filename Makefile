.PHONY: clean clean-pyc clean-build clean-test clean-all test run build publish publish-test publish-manual help install dev-install version bump-patch bump-minor bump-major release docker-build docker-run docker-stop docker-clean docker-test docker-shell docker-push docker-compose-up docker-compose-down docker-help

# Default target
help:
	@echo "Available targets:"
	@echo "  clean          - Remove Python bytecode and basic artifacts"
	@echo "  clean-all      - Deep clean everything (pyc, build, test, cache)"
	@echo "  clean-pyc      - Remove Python bytecode files"
	@echo "  clean-build    - Remove build artifacts"
	@echo "  clean-test     - Remove test artifacts"
	@echo "  install        - Install package in current environment"
	@echo "  dev-install    - Install package in development mode"
	@echo "  test           - Run tests"
	@echo "  test-cov       - Run tests with coverage report"
	@echo "  coverage-report - Show current coverage report"
	@echo "  lint           - Run code linters"
	@echo "  format         - Auto-format code"
	@echo "  typecheck      - Run type checking"
	@echo "  security       - Run security checks"
	@echo "  check          - Run all checks (lint, typecheck, security, test)"
	@echo "  run            - Run the MCP server"
	@echo "  build          - Build the project"
	@echo ""
	@echo "Docker targets:"
	@echo "  docker-help         - Show all Docker targets"
	@echo "  docker-build        - Build Docker image"
	@echo "  docker-run          - Run Docker container"
	@echo "  docker-compose-up   - Start services with docker-compose"
	@echo ""
	@echo "Release targets:"
	@echo "  version        - Show current version"
	@echo "  bump-patch     - Bump patch version (0.0.X)"
	@echo "  bump-minor     - Bump minor version (0.X.0)"
	@echo "  bump-major     - Bump major version (X.0.0)"
	@echo "  publish        - Create tag and trigger automated release"
	@echo "  publish-test   - Upload to TestPyPI for testing"
	@echo "  publish-manual - Manually upload to PyPI (requires PYPI_TOKEN)"
	@echo "  release        - Alias for publish"

# Basic clean - Python bytecode and common artifacts
clean: clean-pyc clean-build
	@echo "Basic clean complete."

# Remove Python bytecode files and __pycache__ directories
clean-pyc:
	@echo "Cleaning Python bytecode files..."
	@find . -type f -name '*.pyc' -delete 2>/dev/null || true
	@find . -type f -name '*.pyo' -delete 2>/dev/null || true
	@find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true

# Remove build artifacts
clean-build:
	@echo "Cleaning build artifacts..."
	@rm -rf build/ dist/ *.egg-info 2>/dev/null || true
	@rm -rf .eggs/ 2>/dev/null || true
	@find . -name '*.egg' -exec rm -f {} + 2>/dev/null || true

# Remove test artifacts
clean-test:
	@echo "Cleaning test artifacts..."
	@rm -rf .pytest_cache/ 2>/dev/null || true
	@rm -rf .coverage 2>/dev/null || true
	@rm -rf htmlcov/ 2>/dev/null || true
	@rm -rf .tox/ 2>/dev/null || true
	@rm -rf .cache/ 2>/dev/null || true
	@find . -name '.coverage.*' -delete 2>/dev/null || true

# Deep clean - everything
clean-all: clean-pyc clean-build clean-test
	@echo "Deep cleaning..."
	@rm -rf .mypy_cache/ 2>/dev/null || true
	@rm -rf .ruff_cache/ 2>/dev/null || true
	@rm -rf .uv/ 2>/dev/null || true
	@rm -rf node_modules/ 2>/dev/null || true
	@find . -name '.DS_Store' -delete 2>/dev/null || true
	@find . -name 'Thumbs.db' -delete 2>/dev/null || true
	@find . -name '*.log' -delete 2>/dev/null || true
	@find . -name '*.tmp' -delete 2>/dev/null || true
	@find . -name '*~' -delete 2>/dev/null || true
	@echo "Deep clean complete."

# Install package
install:
	@echo "Installing package..."
	pip install .

# Install package in development mode
dev-install:
	@echo "Installing package in development mode..."
	pip install -e .

# Run tests
test:
	@echo "Running tests..."
	@uv run pytest tests/ -v --tb=short -m "not network"

# Show current coverage report
coverage-report:
	@echo "Coverage Report:"
	@echo "================"
	@python -m coverage report --omit="tests/*" || echo "No coverage data found. Run 'make test-cov' first."

# Run tests with coverage
test-cov coverage:
	@echo "Running tests with coverage..."
	@uv run pytest tests/ --cov=src/chuk_mcp_solver --cov-report=xml --cov-report=html --cov-report=term --cov-fail-under=90 -m "not network"; \
	exit_code=$$?; \
	echo ""; \
	echo "=========================="; \
	echo "Coverage Summary:"; \
	echo "=========================="; \
	uv run coverage report --omit="tests/*" | tail -5; \
	echo ""; \
	echo "HTML coverage report saved to: htmlcov/index.html"; \
	exit $$exit_code

# Run the MCP server
run:
	@echo "Running CHUK MCP Solver server..."
	@PYTHONPATH=src python -m chuk_mcp_solver.server

# Build the project using the pyproject.toml configuration
build: clean-build
	@echo "Building project..."
	@python -m build
	@echo "Build complete. Distributions are in the 'dist' folder."

# ============================================================================
# Version Management and Release Targets
# ============================================================================

# Show current version
version:
	@version=$$(grep '^version = ' pyproject.toml | cut -d'"' -f2); \
	echo "Current version: $$version"

# Bump patch version (0.0.X)
bump-patch:
	@echo "Bumping patch version..."
	@current=$$(grep '^version = ' pyproject.toml | cut -d'"' -f2); \
	major=$$(echo $$current | cut -d. -f1); \
	minor=$$(echo $$current | cut -d. -f2); \
	patch=$$(echo $$current | cut -d. -f3); \
	new_patch=$$(($$patch + 1)); \
	new_version="$$major.$$minor.$$new_patch"; \
	sed -i.bak "s/^version = \"$$current\"/version = \"$$new_version\"/" pyproject.toml && rm pyproject.toml.bak; \
	echo "Version bumped: $$current -> $$new_version"; \
	echo "Review the change, then run 'make publish' to release"

# Bump minor version (0.X.0)
bump-minor:
	@echo "Bumping minor version..."
	@current=$$(grep '^version = ' pyproject.toml | cut -d'"' -f2); \
	major=$$(echo $$current | cut -d. -f1); \
	minor=$$(echo $$current | cut -d. -f2); \
	new_minor=$$(($$minor + 1)); \
	new_version="$$major.$$new_minor.0"; \
	sed -i.bak "s/^version = \"$$current\"/version = \"$$new_version\"/" pyproject.toml && rm pyproject.toml.bak; \
	echo "Version bumped: $$current -> $$new_version"; \
	echo "Review the change, then run 'make publish' to release"

# Bump major version (X.0.0)
bump-major:
	@echo "Bumping major version..."
	@current=$$(grep '^version = ' pyproject.toml | cut -d'"' -f2); \
	major=$$(echo $$current | cut -d. -f1); \
	new_major=$$(($$major + 1)); \
	new_version="$$new_major.0.0"; \
	sed -i.bak "s/^version = \"$$current\"/version = \"$$new_version\"/" pyproject.toml && rm pyproject.toml.bak; \
	echo "Version bumped: $$current -> $$new_version"; \
	echo "Review the change, then run 'make publish' to release"

# Automated release - creates tag and pushes to trigger GitHub Actions
publish:
	@echo "Starting automated release process..."
	@echo ""
	@# Get current version
	@version=$$(grep '^version = ' pyproject.toml | cut -d'"' -f2); \
	tag="v$$version"; \
	echo "Version: $$version"; \
	echo "Tag: $$tag"; \
	echo ""; \
	\
	echo "Pre-flight checks:"; \
	echo "=================="; \
	\
	if git diff --quiet && git diff --cached --quiet; then \
		echo "✓ Working directory is clean"; \
	else \
		echo "✗ Working directory has uncommitted changes"; \
		echo ""; \
		git status --short; \
		echo ""; \
		echo "Please commit or stash your changes before releasing."; \
		exit 1; \
	fi; \
	\
	if git tag -l | grep -q "^$$tag$$"; then \
		echo "✗ Tag $$tag already exists"; \
		echo ""; \
		echo "To delete and recreate:"; \
		echo "  git tag -d $$tag"; \
		echo "  git push origin :refs/tags/$$tag"; \
		exit 1; \
	else \
		echo "✓ Tag $$tag does not exist yet"; \
	fi; \
	\
	current_branch=$$(git rev-parse --abbrev-ref HEAD); \
	echo "✓ Current branch: $$current_branch"; \
	echo ""; \
	\
	echo "This will:"; \
	echo "  1. Create and push tag $$tag"; \
	echo "  2. Trigger GitHub Actions to:"; \
	echo "     - Create a GitHub release with changelog"; \
	echo "     - Run tests on all platforms"; \
	echo "     - Build and publish to PyPI"; \
	echo ""; \
	read -p "Continue? (y/N) " -n 1 -r; \
	echo ""; \
	if [[ ! $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "Aborted."; \
		exit 1; \
	fi; \
	\
	echo ""; \
	echo "Creating and pushing tag..."; \
	git tag -a "$$tag" -m "Release $$tag" && \
	git push origin "$$tag" && \
	echo "" && \
	echo "✓ Tag pushed successfully!" && \
	echo "" && \
	repo_path=$$(git config --get remote.origin.url | sed 's|^https://github.com/||;s|^git@github.com:||;s|\.git$$||'); \
	echo "GitHub Actions workflows triggered:" && \
	echo "  - Release creation: https://github.com/$$repo_path/actions/workflows/release.yml" && \
	echo "  - PyPI publishing: https://github.com/$$repo_path/actions/workflows/publish.yml" && \
	echo "" && \
	echo "Monitor progress at: https://github.com/$$repo_path/actions"

# Alias for publish
release: publish

# ============================================================================
# PyPI Publishing Targets
# ============================================================================

# Upload to TestPyPI for testing
publish-test: build
	@echo "Publishing to TestPyPI..."
	@echo ""
	@version=$$(grep '^version = ' pyproject.toml | cut -d'"' -f2); \
	echo "Version: $$version"; \
	echo ""; \
	python -m twine upload --repository testpypi dist/*; \
	echo ""; \
	echo "✓ Uploaded to TestPyPI!"; \
	echo ""; \
	echo "Install with:"; \
	echo "  pip install --index-url https://test.pypi.org/simple/ chuk-mcp-solver==$$version"

# Manual publish to PyPI (requires PYPI_TOKEN environment variable)
publish-manual: build
	@echo "Manual PyPI Publishing"
	@echo "======================"
	@echo ""
	@version=$$(grep '^version = ' pyproject.toml | cut -d'"' -f2); \
	tag="v$$version"; \
	echo "Version: $$version"; \
	echo "Tag: $$tag"; \
	echo ""; \
	\
	echo "Pre-flight checks:"; \
	echo "=================="; \
	\
	if git diff --quiet && git diff --cached --quiet; then \
		echo "✓ Working directory is clean"; \
	else \
		echo "✗ Working directory has uncommitted changes"; \
		echo ""; \
		git status --short; \
		echo ""; \
		echo "Please commit or stash your changes before publishing."; \
		exit 1; \
	fi; \
	\
	if git tag -l | grep -q "^$$tag$$"; then \
		echo "✓ Tag $$tag exists"; \
	else \
		echo "⚠ Tag $$tag does not exist yet"; \
		echo ""; \
		read -p "Create tag now? (y/N) " -n 1 -r; \
		echo ""; \
		if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
			git tag -a "$$tag" -m "Release $$tag"; \
			echo "✓ Tag created locally"; \
		else \
			echo "Continuing without creating tag..."; \
		fi; \
	fi; \
	\
	echo ""; \
	echo "This will upload version $$version to PyPI"; \
	echo ""; \
	read -p "Continue? (y/N) " -n 1 -r; \
	echo ""; \
	if [[ ! $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "Aborted."; \
		exit 1; \
	fi; \
	\
	echo ""; \
	echo "Uploading to PyPI..."; \
	if [ -n "$$PYPI_TOKEN" ]; then \
		python -m twine upload --username __token__ --password "$$PYPI_TOKEN" dist/*; \
	else \
		python -m twine upload dist/*; \
	fi; \
	echo ""; \
	echo "✓ Published to PyPI!"; \
	echo ""; \
	if git tag -l | grep -q "^$$tag$$"; then \
		echo "Push tag with: git push origin $$tag"; \
	fi; \
	echo "Install with: pip install chuk-mcp-solver==$$version"

# Check code quality
lint:
	@echo "Running linters..."
	@uv run ruff check src/ tests/
	@uv run ruff format --check src/ tests/

# Fix code formatting
format:
	@echo "Formatting code..."
	@uv run ruff format src/ tests/
	@uv run ruff check --fix src/ tests/

# Type checking
typecheck:
	@echo "Running type checker..."
	@uv run mypy src/

# Security checks
security:
	@echo "Running security checks..."
	@bandit -r src/ -ll

# Run all checks
check: lint typecheck security test
	@echo "All checks completed."

# ============================================================================
# Docker Targets
# ============================================================================

.PHONY: docker-build docker-run docker-stop docker-clean docker-test docker-shell docker-push docker-compose-up docker-compose-down docker-help

# Docker help
docker-help:
	@echo "Docker targets:"
	@echo "  docker-build        - Build Docker image"
	@echo "  docker-run          - Run Docker container"
	@echo "  docker-stop         - Stop running container"
	@echo "  docker-clean        - Remove container and image"
	@echo "  docker-test         - Run tests in Docker container"
	@echo "  docker-shell        - Open shell in running container"
	@echo "  docker-push         - Push image to registry"
	@echo "  docker-compose-up   - Start services with docker-compose"
	@echo "  docker-compose-down - Stop services with docker-compose"

# Build Docker image
docker-build:
	@echo "Building Docker image..."
	docker build -t chuk-mcp-solver:latest .

# Run Docker container
docker-run:
	@echo "Running Docker container..."
	docker run -d -p 8000:8000 --name chuk-mcp-solver chuk-mcp-solver:latest

# Stop Docker container
docker-stop:
	@echo "Stopping Docker container..."
	docker stop chuk-mcp-solver 2>/dev/null || true
	docker rm chuk-mcp-solver 2>/dev/null || true

# Clean Docker artifacts
docker-clean: docker-stop
	@echo "Cleaning Docker artifacts..."
	docker rmi chuk-mcp-solver:latest 2>/dev/null || true

# Run tests in Docker
docker-test:
	@echo "Running tests in Docker container..."
	docker run --rm chuk-mcp-solver:latest pytest tests/ -v

# Open shell in running container
docker-shell:
	@echo "Opening shell in container..."
	docker exec -it chuk-mcp-solver /bin/bash

# Push to registry
docker-push:
	@echo "Pushing Docker image to registry..."
	@echo "Note: Update image tag first (e.g., docker tag chuk-mcp-solver:latest your-registry/chuk-mcp-solver:0.1.1)"
	@echo "Then run: docker push your-registry/chuk-mcp-solver:0.1.1"

# Docker Compose - Start services
docker-compose-up:
	@echo "Starting services with docker-compose..."
	docker-compose up -d

# Docker Compose - Stop services
docker-compose-down:
	@echo "Stopping services with docker-compose..."
	docker-compose down

# Rebuild and restart with docker-compose
docker-compose-rebuild:
	@echo "Rebuilding and restarting services..."
	docker-compose up -d --build
