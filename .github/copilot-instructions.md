# GitHub Copilot Instructions for asynctasq-monitor

---

## Project Overview

Real-time monitoring UI for asynctasq task queues with dual interfaces: **Web Dashboard** (FastAPI + React 19) and **TUI** (Textual). Features live metrics, WebSocket streaming, and comprehensive task/worker/queue management.

**Stack:**
- **Backend:** Python 3.12+, FastAPI, Redis Pub/Sub, msgpack, Pydantic
- **Frontend:** React 19 (Compiler mode), TailwindCSS 4, React Aria, Tanstack Query, Recharts
- **TUI:** Textual 3.3+ with snapshot testing
- **Build:** Vite 7, Biome 2.3, TypeScript 5.9

**Architecture:**
- Event-driven: Redis Pub/Sub for real-time streaming
- Multi-interface: Web (browser) + TUI (terminal) with shared backend services
- Type-safe: Full Python type hints (pyright standard) + TypeScript strict mode
- Async-first: All I/O operations use asyncio

## Essential Commands

```bash
just ci                # MANDATORY before commit: Format + Lint + Typecheck + Test (backend + frontend)
just check             # Quick validation (format + lint + typecheck only)
just test              # Run all tests (Python + TypeScript)
just dev-backend       # Start FastAPI server (http://localhost:8000)
just dev-frontend      # Start Vite dev server (http://localhost:5173)
just build             # Build frontend into Python package static dir + wheel
just init              # Initial setup (install all deps + hooks)
```

---

## Development Boundaries

### ✅ ALWAYS DO (No Permission Needed)
- Research the web for the latest best practices for all languages/tools/libraries/packages/patterns used before implementing
- Run `just ci` before committing
- Add type hints to all Python public APIs (`-> ReturnType`)
- Use TypeScript strict mode (no `any` without justification)
- Write tests for new code (aim for >90% coverage)
- Use `async def` / `await` for all I/O in Python
- Mock external I/O in unit tests (`AsyncMock` for Python, `vi.mock` for TypeScript)
- Follow async-first principles (no blocking calls)
- Use environment variables for configuration (prefix: `MONITOR_`)
- Add docstrings for public Python APIs (Google style)
- Keep functions focused and under 50 lines
- Use descriptive variable names
- Use React 19 Compiler patterns (avoid manual `useMemo`/`useCallback` unless necessary)
- Use React Aria Components for accessible UI primitives
- Use Tanstack Query for server state management
- Implement proper keyboard navigation and ARIA labels

### ⚠️ ASK FIRST (Breaking Changes)
- Modifying public API signatures (FastAPI endpoints, WebSocket protocol)
- Changing service interfaces (`TaskService`, `QueueService`, `WorkerService`)
- Altering event format (breaks real-time streaming)
- Adding new dependencies to `pyproject.toml` or `package.json`
- Changing configuration structure (`Settings` dataclass)
- Modifying WebSocket protocol or message format
- Breaking backward compatibility with asynctasq core
- Major UI/UX changes affecting navigation or layout

### 🚫 NEVER DO (Project Standards)
- Commit without `just ci` passing (backend + frontend)
- Use `Any` type in Python without justification
- Use `any` type in TypeScript without justification
- Block event loop with sync I/O in async context
- Skip writing tests ("I'll add them later")
- Hardcode secrets or configuration
- Mix async/sync code incorrectly
- Use `from module import *` (wildcard imports)
- Ignore security warnings (`just security`, `just audit`)
- Copy-paste code (extract to shared functions/components)
- Push directly to `main` branch (use PRs)
- Use manual `useMemo`/`useCallback` in React (Compiler handles it)
- Use inline styles (use TailwindCSS classes)
- Skip accessibility attributes (ARIA labels, keyboard nav)

---

## Key Architecture Patterns

### Backend (Python)
- **Services**: `TaskService`, `QueueService`, `WorkerService` - async methods wrapping asynctasq drivers
- **Events**: Redis Pub/Sub broadcasting (task lifecycle, metrics updates)
- **WebSocket**: `EventConsumer` for real-time streaming to frontend
- **FastAPI**: RESTful API + WebSocket endpoints
- **Config**: Pydantic Settings with `MONITOR_` prefix env vars

### Frontend (TypeScript/React)
- **State Management**: Tanstack Query (server state) + Zustand (UI state)
- **UI Framework**: React Aria Components (accessible primitives)
- **Styling**: TailwindCSS 4 + `tailwind-variants` for component variants
- **Charts**: Recharts for metrics visualization
- **Forms**: React Hook Form + Zod validation
- **Routing**: React Router 6
- **Build**: Vite 7 with React Compiler plugin

### TUI (Python/Textual)
- **Screens**: Dashboard, Tasks, Workers, Queues, Help
- **Components**: Custom Textual widgets with vim-style keybindings
- **Testing**: Snapshot testing with `pytest-textual-snapshot`

---

## Workflow

1. Create feature branch
2. Make changes following code standards below
3. **Run `just ci`** (MUST pass - backend + frontend)
4. Commit and create PR

---

## Testing

### Python
- **Framework**: pytest 9.0.1 with `asyncio_mode="strict"`
- **Markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.snapshot`
- **Pattern**: AAA (Arrange, Act, Assert)
- **Async**: Use `@pytest.mark.asyncio` + `AsyncMock` for async code
- **Unit tests**: Mock all I/O. Fast (<1s per test)
- **Integration tests**: Real Redis for event testing
- **TUI**: Snapshot tests with `pytest-textual-snapshot`
- **Never**: Make real API calls in tests

### TypeScript/Frontend
- **Framework**: Vitest 4 with React Testing Library
- **Pattern**: User-centric testing (test behavior, not implementation)
- **Coverage**: Use `just test-frontend-coverage`
- **Commands**: `just test-frontend` (run), `just test-frontend-watch` (watch mode)

---

## Code Standards & Conventions

### Python Backend

#### Type Safety
- Full type hints on all public APIs (MUST pass `just typecheck`)
- Use `list[str]`, `dict[str, Any]`, `X | Y` (Python 3.12 syntax)
- Avoid `Any` - use `object` or specific Union types
- Use `from __future__ import annotations` for forward references

#### Code Style
- **Formatter**: ruff (line-length: 100)
- **Linter**: ruff with E, F, I, B, C4, UP rules
- **Docstrings**: Google style for public APIs
- **Complexity**: Max McCabe = 10

#### Async-First
- Use `async def`/`await` for all I/O - NO blocking calls
- Use `await asyncio.sleep()` NOT `time.sleep()`
- Offload CPU-bound work to `ThreadPoolExecutor`
- Use `asyncio.Semaphore` for concurrency control
- Always await coroutines

#### Error Handling
- Raise specific exceptions with context (task_id, queue, error details)
- Use structured logging with `extra={}`
- Implement proper WebSocket error handling and reconnection

### TypeScript/React Frontend

#### Type Safety
- Enable TypeScript strict mode (MUST pass `just typecheck-frontend`)
- Use explicit types for props, state, API responses
- Avoid `any` - use `unknown` or specific types
- Use type imports: `import type { ... }`

#### Code Style
- **Formatter/Linter**: Biome 2.3 (line-width: 100, tab-width: 2)
- **Rules**: Recommended + accessibility + performance rules
- **Imports**: Auto-organize with Biome (use `just format-frontend`)

#### React Best Practices
- Use React 19 Compiler (no manual memoization unless necessary)
- Prefer React Aria Components for UI primitives
- Use Tanstack Query for server state (`useQuery`, `useMutation`)
- Use Zustand for global UI state (theme, filters, etc.)
- Use `tailwind-variants` for component styling
- Always add ARIA labels and keyboard navigation
- Use semantic HTML and proper heading hierarchy

#### Performance
- Leverage React Compiler automatic memoization
- Use `manualChunks` in Vite config (already configured)
- Lazy load routes with `React.lazy()`
- Optimize images and assets

---

## Key Files

### Backend
- `src/asynctasq_monitor/config.py` - Pydantic Settings with env vars
- `src/asynctasq_monitor/services/` - Business logic services
- `src/asynctasq_monitor/api/` - FastAPI endpoints
- `src/asynctasq_monitor/websocket/` - WebSocket event streaming
- `src/asynctasq_monitor/models/` - Pydantic models (Task, Queue, Worker)
- `src/asynctasq_monitor/tui/` - Textual TUI screens and components
- `src/asynctasq_monitor/cli/main.py` - Typer CLI entry point

### Frontend
- `frontend/src/api/` - API client and React Query hooks
- `frontend/src/components/` - Reusable UI components
- `frontend/src/pages/` - Route pages (Dashboard, Tasks, Workers, Queues)
- `frontend/src/stores/` - Zustand stores
- `frontend/src/types/` - TypeScript type definitions
- `frontend/vite.config.ts` - Build configuration
- `frontend/biome.json` - Linter/formatter config

---

## Configuration

### Backend (Python)
All env vars use `MONITOR_` prefix. See `src/asynctasq_monitor/config.py`.

**Key settings:**
- `MONITOR_DEBUG` - Enable debug mode (default: false)
- `MONITOR_HOST` - API server host (default: "0.0.0.0")
- `MONITOR_PORT` - API server port (default: 8000)
- `MONITOR_CORS_ORIGINS` - Comma-separated CORS origins
- `MONITOR_POLLING_INTERVAL_SECONDS` - Metrics polling interval (default: 5)
- `MONITOR_WEBSOCKET_HEARTBEAT_SECONDS` - WebSocket ping interval (default: 30)

### Frontend (TypeScript)
Vite dev server runs on port 5173 with API proxy to backend (localhost:8000).

---

## Before Committing

**MANDATORY: Run `just ci` - MUST pass with zero errors (backend + frontend)**

Then verify:
- ✅ Tests added (unit + integration if needed, >90% coverage)
- ✅ Type hints on all Python public APIs (`just typecheck` passes)
- ✅ TypeScript strict mode passes (`just typecheck-frontend` passes)
- ✅ Docstrings for public Python functions/classes
- ✅ ARIA labels and keyboard navigation for new UI components
- ✅ No console.log or print statements (use structured logging)
- ✅ No secrets in code (use env vars)
- ✅ Works with both web and TUI interfaces (if applicable)

---

## Troubleshooting

### Backend (Python)
- **Ruff issues**: Run `just format-python`
- **Type errors**: Add type hints, use `from __future__ import annotations`
- **Test failures**: Check Redis is running, run individual tests with `-v` flag
- **Import errors**: Run `just init` or `uv sync --all-extras --group dev`

### Frontend (TypeScript)
- **Biome issues**: Run `just format-frontend` or `just lint-fix-frontend`
- **Type errors**: Add explicit types, check `tsconfig.json` settings
- **Build errors**: Clear `node_modules/.vite` cache with `just clean-frontend`
- **Dependency errors**: Run `cd frontend && pnpm install`

---

## Best Practices

### ✅ DO:
- Run `just ci` before committing (non-negotiable)
- Write tests for all new code (>90% coverage)
- Use type hints on all public APIs (Python + TypeScript)
- Follow async-first principles (Python)
- Use React Compiler patterns (React)
- Add ARIA labels and keyboard navigation (Frontend)
- Use Tanstack Query for server state (Frontend)
- Log with structured context (Python)
- Keep components small and focused (Frontend)
- Test user behavior, not implementation details (Frontend)

### ❌ DON'T:
- Block event loop with sync I/O (Python)
- Use `Any` or `any` without justification (Python/TypeScript)
- Skip tests
- Hardcode secrets
- Break backward compatibility without major version bump
- Use inline styles (use TailwindCSS)
- Skip accessibility features
- Use manual memoization without reason (React Compiler handles it)
- Ignore console warnings (fix them properly)

---

## Build & Deployment

### Build Process
1. Frontend builds into `src/asynctasq_monitor/static/` (Vite)
2. Python package includes static assets via `[tool.hatch.build.artifacts]`
3. Wheel contains both backend code + compiled frontend

### Commands
```bash
just build             # Build both frontend and Python package
just release           # Full release build (clean + build)
just publish           # Publish to PyPI (requires credentials)
just publish-test      # Publish to Test PyPI
```

### Publishing Checklist
- ✅ `just ci` passes
- ✅ Version bumped in `pyproject.toml`
- ✅ CHANGELOG updated
- ✅ Frontend built and bundled
- ✅ All tests pass
- ✅ Security audit clean (`just audit`)

---

## Development Tips

- Use `just dev-backend` and `just dev-frontend` in separate terminals for hot reload
- Frontend dev server proxies API requests to backend (localhost:8000)
- Use `just test-frontend-watch` for TDD workflow
- Use `just test-profile` to identify slow tests
- Use `just info` to check versions and environment
- Use `just outdated` to check for dependency updates
- Use TUI for quick terminal-based monitoring (`asynctasq-monitor tui`)

---
