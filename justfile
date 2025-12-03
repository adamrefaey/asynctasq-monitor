# Async Task Q Monitor - Unified Justfile
# Commands for both backend (Python) and frontend (TypeScript/React)

# Default recipe to display help
default:
    @just --list

# =============================================================================
# Project Setup
# =============================================================================

# Initialize project (install all deps + setup hooks)
init: install install-frontend setup-hooks
    @echo "✅ Project initialized successfully!"
    @echo "Run 'just dev' to start development servers"
    @echo "Run 'just test' to run tests"

# Install Python package with dev dependencies
install:
    uv sync --all-extras

# Install frontend dependencies
install-frontend:
    cd frontend && pnpm install

# Setup pre-commit hooks
setup-hooks:
    uv run pre-commit install
    @echo "✅ Pre-commit hooks installed successfully!"

# =============================================================================
# Development
# =============================================================================

# Run both backend and frontend in development mode (requires tmux or run separately)
dev:
    @echo "Starting development servers..."
    @echo "Backend: http://localhost:8000"
    @echo "Frontend: http://localhost:5173"
    @echo ""
    @echo "Run in separate terminals:"
    @echo "  just dev-backend"
    @echo "  just dev-frontend"

# Run backend server in development mode
dev-backend:
    uv run python -m async_task_q_monitor --reload --log-level debug

# Run frontend dev server with hot reload
dev-frontend:
    cd frontend && pnpm dev

# =============================================================================
# Build
# =============================================================================

# Build both frontend and Python package
build: build-frontend build-python
    @echo "✅ Build complete!"

# Build frontend into Python package static directory
build-frontend:
    cd frontend && pnpm build
    @echo "✅ Frontend built to src/async_task_q_monitor/static/"

# Build Python package (wheel and sdist)
build-python:
    uv build
    @echo "✅ Python package built to dist/"

# Clean build artifacts
clean:
    rm -rf dist/
    rm -rf src/async_task_q_monitor/static/assets/
    rm -f src/async_task_q_monitor/static/index.html
    rm -f src/async_task_q_monitor/static/vite.svg
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name ".coverage" -delete 2>/dev/null || true
    @echo "✅ Cleaned build artifacts"

# =============================================================================
# Linting & Formatting
# =============================================================================

# Format all code (Python + TypeScript)
format: format-python format-frontend
    @echo "✅ All code formatted"

# Format Python code with Ruff
format-python:
    uv run ruff format .

# Format frontend code with Biome
format-frontend:
    cd frontend && pnpm format

# Lint all code (Python + TypeScript)
lint: lint-python lint-frontend
    @echo "✅ All linting passed"

# Lint Python code
lint-python:
    uv run ruff check .

# Auto-fix Python linting issues
lint-fix:
    uv run ruff check --fix .

# Lint frontend code with Biome
lint-frontend:
    cd frontend && pnpm lint

# Fix frontend linting issues
lint-fix-frontend:
    cd frontend && pnpm lint:fix

# Type check Python with Pyright
typecheck:
    uv run pyright

# Type check frontend with TypeScript
typecheck-frontend:
    cd frontend && pnpm typecheck

# Run all checks (format, lint, typecheck)
check: format lint typecheck typecheck-frontend
    @echo "✅ All checks passed"

# =============================================================================
# Testing
# =============================================================================

# Run all Python tests
test:
    uv run pytest

# Run unit tests only
test-unit:
    uv run pytest -m unit

# Run integration tests only
test-integration:
    uv run pytest -m integration

# Run tests with coverage report
test-cov:
    uv run pytest --cov=async_task_q_monitor --cov-branch --cov-report=term-missing --cov-report=html

# Show test coverage in browser
coverage-html: test-cov
    open htmlcov/index.html || xdg-open htmlcov/index.html

# Profile tests (show slowest tests)
test-profile:
    uv run pytest --durations=10

# =============================================================================
# CI/CD
# =============================================================================

# Run all CI checks locally
ci: format lint typecheck test
    @echo "✅ All CI checks passed!"

# Run pre-commit on all files
pre-commit:
    uv run pre-commit run --all-files

# Update pre-commit hooks
pre-commit-update:
    uv run pre-commit autoupdate

# =============================================================================
# Security
# =============================================================================

# Run security checks with bandit
security:
    uv run bandit -r src/async_task_q_monitor -ll

# Run dependency security audit
audit:
    uv run pip-audit

# =============================================================================
# Publishing
# =============================================================================

# Full release build (clean, build frontend, build package)
release: clean build-frontend build-python
    @echo "✅ Release build complete!"
    @echo "Package ready in dist/"

# Publish to PyPI (requires credentials)
publish: release
    uv run python -m pip install --upgrade twine
    uv run python -m twine check dist/*
    uv publish

# Publish to Test PyPI
publish-test: release
    uv run python -m pip install --upgrade twine
    uv run python -m twine check dist/*
    uv publish --index-url https://test.pypi.org/legacy/

# Create and push a git tag (usage: just tag v1.2.3)
tag TAG:
    @if [ "$(printf '%s' '{{TAG}}' | cut -c1)" != "v" ]; then \
        echo "Tag should start with 'v', e.g. v1.2.3"; exit 1; \
    fi
    git tag {{TAG}}
    git push origin {{TAG}}
    @echo "✅ Pushed {{TAG}}"

# =============================================================================
# Utilities
# =============================================================================

# Show project info
info:
    @echo "Project: async-task-q-monitor"
    @echo "Python: $(uv run python --version)"
    @echo "UV: $(uv --version)"
    @echo "Node: $(node --version)"
    @echo "pnpm: $(pnpm --version)"
    @echo ""
    @echo "Run 'just --list' to see all available commands"

# Show outdated dependencies
outdated:
    @echo "Python dependencies:"
    uv pip list --outdated
    @echo ""
    @echo "Frontend dependencies:"
    cd frontend && pnpm outdated
