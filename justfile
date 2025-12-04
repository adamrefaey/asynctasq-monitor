# Async TasQ Monitor - Unified Justfile
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
    uv run python -m asynctasq_monitor --reload --log-level debug

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
    @echo "✅ Frontend built to src/asynctasq_monitor/static/"

# Build Python package (wheel and sdist)
build-python:
    uv build
    @echo "✅ Python package built to dist/"

# Preview frontend build locally
preview-frontend:
    cd frontend && pnpm preview

# Clean build artifacts
clean: clean-python clean-frontend
    @echo "✅ Cleaned all build artifacts"

# Clean Python build artifacts
clean-python:
    rm -rf dist/
    rm -rf src/asynctasq_monitor/static/assets/
    rm -f src/asynctasq_monitor/static/index.html
    rm -f src/asynctasq_monitor/static/vite.svg
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name ".coverage" -delete 2>/dev/null || true

# Clean frontend build artifacts
clean-frontend:
    cd frontend && rm -rf dist/ node_modules/.vite

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

# Run all checks (format, lint, typecheck) for both backend and frontend
check: format lint typecheck typecheck-frontend
    @echo "✅ All checks passed"

# Run frontend check (format + lint + typecheck combined)
check-frontend:
    cd frontend && pnpm check

# =============================================================================
# Testing
# =============================================================================

# Run all tests (Python + Frontend)
test: test-backend test-frontend
    @echo "✅ All tests passed"

# Run all Python tests
test-backend:
    uv run pytest

# Run frontend tests (when available)
test-frontend:
    cd frontend && pnpm test

# Run frontend tests in watch mode
test-frontend-watch:
    cd frontend && pnpm test:watch

# Run frontend tests with coverage
test-frontend-coverage:
    cd frontend && pnpm test:coverage
# Run unit tests only
test-unit:
    uv run pytest -m unit

# Run integration tests only
test-integration:
    uv run pytest -m integration

# Run backend tests with coverage report
test-cov:
    uv run pytest --cov=asynctasq_monitor --cov-branch --cov-report=term-missing --cov-report=html

# Run frontend tests with coverage (when available)
test-cov-frontend:
    @echo "⚠️  Frontend test coverage not yet configured"
    @echo "Add test framework (Vitest) and update this command"

# Show test coverage in browser
coverage-html: test-cov
    open htmlcov/index.html || xdg-open htmlcov/index.html

# Profile tests (show slowest tests)
test-profile:
    uv run pytest --durations=10

# =============================================================================
# CI/CD
# =============================================================================

# Run all CI checks locally (Python + Frontend)
ci: format lint typecheck typecheck-frontend test
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
    uv run bandit -r src/asynctasq_monitor -ll

# Run dependency security audit (Python + Frontend)
audit: audit-python audit-frontend
    @echo "✅ All security audits complete"

# Run Python dependency security audit
audit-python:
    uv run pip-audit

# Run frontend dependency security audit
audit-frontend:
    cd frontend && pnpm audit

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
    @echo "Project: asynctasq-monitor"
    @echo "Python: $(uv run python --version)"
    @echo "UV: $(uv --version)"
    @echo "Node: $(node --version)"
    @echo "pnpm: $(pnpm --version)"
    @echo ""
    @echo "Run 'just --list' to see all available commands"

# Show outdated dependencies (Python + Frontend)
outdated: outdated-python outdated-frontend

# Show outdated Python dependencies
outdated-python:
    @echo "Python dependencies:"
    uv pip list --outdated

# Show outdated frontend dependencies
outdated-frontend:
    @echo ""
    @echo "Frontend dependencies:"
    cd frontend && pnpm outdated
