# Async TasQ Monitor

[![Tests](https://raw.githubusercontent.com/adamrefaey/asynctasq-monitor/main/.github/tests.svg)](https://github.com/adamrefaey/asynctasq-monitor/actions/workflows/ci.yml)
[![Coverage](https://raw.githubusercontent.com/adamrefaey/asynctasq-monitor/main/.github/coverage.svg)](https://raw.githubusercontent.com/adamrefaey/asynctasq-monitor/main/.github/coverage.svg)
[![Python Version](https://raw.githubusercontent.com/adamrefaey/asynctasq-monitor/main/.github/python-version.svg)](https://www.python.org/downloads/)
[![PyPI Version](https://img.shields.io/pypi/v/asynctasq-monitor)](https://pypi.org/project/asynctasq-monitor/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Real-time monitoring UI for [asynctasq](https://github.com/adamrefaey/asynctasq) task queues. Available as both a **web dashboard** (browser-based) and a **TUI** (terminal-based) interface.

## Requirements

- **Python 3.12+**
- **Redis Server**: A running Redis server is **required** for real-time event streaming via Pub/Sub

## Features

### Web Interface (Browser-based)
- 📊 **Real-time Dashboard** - Live task, worker, and queue metrics with auto-refresh
- 📋 **Task Management** - View, filter, search, retry, and cancel tasks
- 👷 **Worker Monitoring** - Track worker status, health, and performance
- 📈 **Queue Analytics** - Monitor queue depths, throughput, and processing rates
- 📉 **Metrics & Charts** - Visualize trends with Recharts-powered graphs
- 🔌 **WebSocket Updates** - Automatic real-time updates via WebSocket connections
- ⌨️ **Keyboard Shortcuts** - Navigate efficiently with keyboard controls
- 🎨 **Modern UI** - Built with React 19, TailwindCSS 4, React Aria, and Tanstack Query
- 🌗 **Dark/Light Theme** - Toggle between themes for comfortable viewing

### TUI Interface (Terminal-based)
- 🖥️ **Terminal Dashboard** - Full monitoring in your terminal, perfect for SSH sessions
- ⌨️ **Keyboard-driven** - Navigate with vim-style keybindings
- 📊 **Real-time Updates** - Live event streaming directly in the terminal
- 🎨 **Rich UI** - Built with Textual framework for beautiful terminal graphics

## Installation

The monitor is available in three installation variants:

```bash
# Core package (required)
uv add asynctasq-monitor        # or: pip install asynctasq-monitor

# With web UI (FastAPI + React dashboard)
uv add "asynctasq-monitor[web]" # or: pip install "asynctasq-monitor[web]"

# With TUI (terminal interface)
uv add "asynctasq-monitor[tui]" # or: pip install "asynctasq-monitor[tui]"

# Everything included
uv add "asynctasq-monitor[all]" # or: pip install "asynctasq-monitor[all]"
```

Alternatively, install as an extra from the core `asynctasq` package:

```bash
uv add "asynctasq[monitor]"     # or: pip install "asynctasq[monitor]"
```

> **Note**: All installation methods include `redis[hiredis]` for high-performance Redis Pub/Sub communication.

## Quick Start

### Prerequisites

1. **Redis Server**: Ensure Redis is running and accessible (default: `redis://localhost:6379`)

### Configure Your Workers

Configure your task workers to emit events to Redis:

```python
from asynctasq import set_global_config

# Option 1: Use Redis as queue driver (events enabled automatically)
set_global_config(driver="redis", redis_url="redis://localhost:6379")

# Option 2: Use another driver but still emit events to Redis
set_global_config(driver="postgres", redis_url="redis://localhost:6379")
```

### Run the Web Monitor

```bash
# Start the web monitor server
asynctasq-monitor web

# With custom options
asynctasq-monitor web --host 0.0.0.0 --port 8080

# With auto-reload for development
asynctasq-monitor web --reload --log-level debug
```

Then open http://localhost:8000 in your browser.

### Run the TUI Monitor

```bash
# Start the terminal UI
asynctasq-monitor tui

# With custom Redis URL
asynctasq-monitor tui --redis-url redis://localhost:6379

# With custom refresh rate
asynctasq-monitor tui --refresh-rate 0.5
```

### Embed in Your FastAPI App

```python
from fastapi import FastAPI
from asynctasq_monitor import create_monitoring_app

# Create a standalone monitoring app
monitor_app = create_monitoring_app()

# Or mount it in your existing app
app = FastAPI()
app.mount("/monitor", create_monitoring_app())
```

## CLI Reference

The CLI uses subcommands for different interfaces:

```
asynctasq-monitor [OPTIONS] COMMAND [ARGS]

Global Options:
  -v, --verbose         Enable verbose output
  --config PATH         Path to config file (TOML)
  --help                Show help message

Commands:
  web                   Start the web-based monitor UI
  tui                   Start the terminal-based monitor UI
```

### Web Command

```
asynctasq-monitor web [OPTIONS]

Options:
  --host TEXT           Host to bind to (default: 127.0.0.1)
                        Env: MONITOR_HOST
  --port INTEGER        Port to bind to (default: 8000)
                        Env: MONITOR_PORT
  --reload              Enable auto-reload for development
  --workers INTEGER     Number of worker processes (default: 1)
  --log-level TEXT      Log level: debug, info, warning, error, critical
```

### TUI Command

```
asynctasq-monitor tui [OPTIONS]

Options:
  --redis-url TEXT      Redis connection URL (default: redis://localhost:6379)
                        Env: ASYNCTASQ_REDIS_URL
  --theme TEXT          Color theme: dark or light (default: dark)
  --refresh-rate FLOAT  Refresh rate in seconds (default: 1.0, range: 0.1-60.0)
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONITOR_HOST` | Host address for the web server | `127.0.0.1` |
| `MONITOR_PORT` | Port for the web server | `8000` |
| `MONITOR_DEBUG` | Enable debug mode | `false` |
| `MONITOR_CORS_ORIGINS` | Comma-separated CORS origins | `*` |
| `MONITOR_ENABLE_AUTH` | Enable JWT authentication | `false` |
| `MONITOR_SECRET_KEY` | Secret key for JWT (min 32 chars) | - |
| `MONITOR_POLLING_INTERVAL_SECONDS` | Metric polling interval | `5` |
| `MONITOR_WEBSOCKET_HEARTBEAT_SECONDS` | WebSocket ping interval | `30` |
| `MONITOR_METRICS_RETENTION_DAYS` | Historical metrics retention | `90` |
| `MONITOR_LOG_LEVEL` | Logging level | `INFO` |
| `ATQ_REDIS_URL` | Redis URL for event consumer | `redis://localhost:6379` |
| `ATQ_EVENTS_CHANNEL` | Redis Pub/Sub channel | `asynctasq:events` |

## API Documentation

When running the web monitor, interactive API documentation is available at:

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### REST API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/dashboard/summary` | Dashboard overview with key metrics |
| `GET /api/tasks` | List tasks with filtering and pagination |
| `GET /api/tasks/{id}` | Get task details |
| `POST /api/tasks/{id}/retry` | Retry a failed task |
| `POST /api/tasks/{id}/cancel` | Cancel a pending task |
| `GET /api/workers` | List workers with status |
| `GET /api/workers/{id}` | Get worker details |
| `GET /api/queues` | List queues with metrics |
| `GET /api/metrics` | Get detailed metrics |

### WebSocket API

Connect to `ws://localhost:8000/ws` for real-time updates.

**Room Subscriptions:**
```
ws://localhost:8000/ws?rooms=global           # Dashboard updates
ws://localhost:8000/ws?rooms=tasks&rooms=workers  # Multiple rooms
ws://localhost:8000/ws?rooms=task:abc123      # Specific task updates
```

**Available Rooms:**
- `global` - Dashboard overview updates
- `tasks` - Task list updates (new, completed, failed)
- `task:{id}` - Specific task updates
- `workers` - Worker list updates
- `worker:{id}` - Specific worker updates
- `queues` - Queue list updates
- `queue:{name}` - Specific queue updates

**Client Commands:**
```json
{"action": "subscribe", "room": "task:abc123"}
{"action": "unsubscribe", "room": "task:abc123"}
{"action": "ping"}
```

## Development

### Prerequisites

- Python 3.12+
- Node.js 24+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- [pnpm](https://pnpm.io/) (Frontend package manager)
- [just](https://github.com/casey/just) (Command runner)

### Setup

```bash
# Clone the repository
git clone https://github.com/adamrefaey/asynctasq-monitor.git
cd asynctasq-monitor

# Initialize the project (installs all dependencies + pre-commit hooks)
just init

# Or manually:
uv sync --all-extras          # Python dependencies
cd frontend && pnpm install   # Frontend dependencies
```

### Development Servers

```bash
# Run backend with auto-reload (http://localhost:8000)
just dev-backend

# Run frontend with hot-reload (http://localhost:5173)
just dev-frontend
```

### Available Commands

Run `just` to see all available commands. Key commands:

```bash
# Development
just dev-backend          # Start backend with auto-reload
just dev-frontend         # Start frontend with hot-reload

# Building
just build-frontend       # Build frontend into Python package
just build                # Build both frontend and Python package
just release              # Full release build (clean + build)

# Testing
just test                 # Run all tests (backend + frontend)
just test-backend         # Run Python tests
just test-frontend        # Run frontend tests
just test-unit            # Run unit tests only
just test-cov             # Run tests with coverage report

# Code Quality
just format               # Format all code (Python + TypeScript)
just lint                 # Lint all code
just lint-fix             # Auto-fix linting issues
just typecheck            # Type check Python with Pyright
just typecheck-frontend   # Type check frontend with TypeScript
just check                # Run all checks (format, lint, typecheck)

# Security
just security             # Run Bandit security scanner
just audit                # Audit dependencies for vulnerabilities

# Docker (for integration tests)
just docker-up            # Start test services (Redis, etc.)
just docker-down          # Stop test services

# Publishing
just publish              # Publish to PyPI
just publish-test         # Publish to Test PyPI
just tag v1.2.3           # Create and push a git tag
```

## Architecture

```
asynctasq-monitor/
├── src/
│   └── asynctasq_monitor/        # Python package
│       ├── __init__.py           # Package exports (create_monitoring_app)
│       ├── __main__.py           # CLI entry point
│       ├── config.py             # Pydantic Settings configuration
│       ├── cli/                  # Typer CLI commands
│       │   ├── main.py           # Main CLI app with subcommands
│       │   ├── web.py            # Web server command
│       │   └── tui.py            # TUI command
│       ├── api/                  # FastAPI application
│       │   ├── main.py           # App factory with lifespan
│       │   ├── dependencies.py   # Dependency injection
│       │   └── routes/           # API route modules
│       │       ├── dashboard.py  # Dashboard endpoints
│       │       ├── tasks.py      # Task endpoints
│       │       ├── workers.py    # Worker endpoints
│       │       ├── queues.py     # Queue endpoints
│       │       ├── metrics.py    # Metrics endpoints
│       │       └── websocket.py  # WebSocket endpoint
│       ├── models/               # Pydantic models
│       │   ├── task.py           # Task models
│       │   ├── worker.py         # Worker models
│       │   └── queue.py          # Queue models
│       ├── services/             # Business logic
│       │   ├── event_consumer.py # Redis Pub/Sub consumer
│       │   ├── metrics_collector.py
│       │   ├── prometheus.py     # Prometheus exporter
│       │   ├── task_service.py
│       │   ├── worker_service.py
│       │   └── queue_service.py
│       ├── websocket/            # WebSocket handling
│       │   ├── manager.py        # Connection management
│       │   └── broadcaster.py    # Event broadcasting
│       ├── tui/                  # Textual TUI application
│       │   ├── app.py            # Main TUI app
│       │   ├── event_handler.py  # Event consumption
│       │   ├── screens/          # TUI screens
│       │   ├── widgets/          # Custom widgets
│       │   └── styles/           # TCSS stylesheets
│       └── static/               # Built frontend (generated)
├── frontend/                     # React frontend source
│   ├── src/
│   │   ├── main.tsx              # App entry point
│   │   ├── router.tsx            # React Router configuration
│   │   ├── pages/                # Page components
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Tasks.tsx
│   │   │   ├── Workers.tsx
│   │   │   ├── Queues.tsx
│   │   │   ├── Metrics.tsx
│   │   │   └── Settings.tsx
│   │   ├── components/           # Reusable components
│   │   ├── hooks/                # Custom React hooks
│   │   │   ├── useDashboard.ts
│   │   │   ├── useTasks.ts
│   │   │   ├── useWorkers.ts
│   │   │   ├── useWebSocket.ts   # WebSocket with auto-reconnect
│   │   │   └── useKeyboardShortcuts.ts
│   │   └── lib/                  # Utilities
│   │       ├── api.ts            # Type-safe API client
│   │       └── types.ts          # TypeScript types
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── biome.json                # Linting/formatting config
├── tests/                        # Python tests
│   ├── unit/
│   ├── integration/
│   └── infrastructure/           # Docker compose for tests
├── pyproject.toml
└── justfile                      # Command runner recipes
```

## Tech Stack

### Backend
- **Python 3.12+** - Modern Python with type hints
- **FastAPI** - High-performance async web framework
- **Typer** - CLI framework with Rich support
- **Pydantic** - Data validation and settings management
- **Redis** - Event streaming via Pub/Sub
- **Textual** - Modern TUI framework

### Frontend
- **React 19** - UI library with new compiler
- **TypeScript 5.9** - Type-safe JavaScript
- **Vite 7** - Next-generation build tool
- **TailwindCSS 4** - Utility-first CSS
- **Tanstack Query** - Async state management
- **Tanstack Table** - Headless table component
- **React Aria** - Accessible UI components
- **Recharts** - Composable charting library
- **React Router 6** - Client-side routing
- **Zustand** - Lightweight state management
- **Vitest** - Fast unit testing
- **Biome** - Fast linting and formatting

## License

MIT License - see [LICENSE](LICENSE) for details.
