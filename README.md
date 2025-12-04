# Async Task Q Monitor

Web-based monitoring UI for [async-task-q](https://github.com/adamrefaey/async-task-q) task queues.

## Requirements

- **Redis Server**: A running Redis server is **required** for the monitor to function. The monitor uses Redis Pub/Sub to receive real-time events from task workers.

## Features

- 📊 **Real-time Dashboard** - Live task, worker, and queue metrics
- 📋 **Task Management** - View, filter, retry, and cancel tasks
- 👷 **Worker Monitoring** - Track worker status and performance
- 📈 **Queue Analytics** - Monitor queue depths and throughput
- 🔌 **WebSocket Updates** - Real-time updates via WebSocket connections
- 🎨 **Modern UI** - Built with React, TailwindCSS, and React Aria

## Installation

```bash
# Install as standalone package
pip install async-task-q-monitor

# Or install with the core package (recommended)
pip install async-task-q[monitor]
```

> **Note**: Both installation methods include the `redis[hiredis]` package required for Redis Pub/Sub communication.

## Quick Start

### Prerequisites

1. **Redis Server**: Ensure Redis is running and accessible (default: `redis://localhost:6379`)

### Configure Your Workers

Configure your task workers to use Redis as the driver or ensure `redis_url` is set for event emission:

```python
from async_task_q import set_global_config

# Option 1: Use Redis as queue driver (events enabled automatically)
set_global_config(driver="redis", redis_url="redis://localhost:6379")

# Option 2: Use another driver but still emit events to Redis
# Events will use the redis_url from config for Pub/Sub
set_global_config(driver="postgres", redis_url="redis://localhost:6379")
```

### Run the Monitor Server

```bash
# Start the monitor server
async-task-q-monitor

# Or with custom options
async-task-q-monitor --host 0.0.0.0 --port 8080

# With auto-reload for development
async-task-q-monitor --reload --log-level debug
```

### Embed in Your FastAPI App

```python
from fastapi import FastAPI
from async_task_q_monitor import create_monitoring_app

# Create a standalone monitoring app
monitor_app = create_monitoring_app()

# Or mount it in your existing app
app = FastAPI()
app.mount("/monitor", create_monitoring_app())
```

## CLI Options

```
async-task-q-monitor [OPTIONS]

Options:
  --host TEXT           Host to bind to (default: 127.0.0.1)
  --port INTEGER        Port to bind to (default: 8000)
  --reload              Enable auto-reload for development
  --workers INTEGER     Number of worker processes (default: 1)
  --log-level TEXT      Log level: debug, info, warning, error, critical
  -h, --help            Show this help message
```

## Development

### Prerequisites

- Python 3.11+
- Node.js 20+ (for frontend development)
- pnpm (for frontend package management)
- uv (for Python package management)

### Setup

```bash
# Clone the repository
git clone https://github.com/adamrefaey/async-task-q-monitor.git
cd async-task-q-monitor

# Initialize the project (installs all dependencies)
just init

# Or manually:
uv sync --all-extras          # Python dependencies
cd frontend && pnpm install   # Frontend dependencies
```

### Development Servers

```bash
# Run backend with auto-reload
just dev-backend

# Run frontend with hot-reload (in another terminal)
just dev-frontend
```

### Building

```bash
# Build frontend into Python package
just build-frontend

# Build Python package (includes frontend)
just build

# Full release build
just release
```

### Testing

```bash
# Run all tests
just test

# Run unit tests only
just test-unit

# Run with coverage
just test-cov
```

### Linting & Formatting

```bash
# Format all code
just format

# Lint all code
just lint

# Type check
just typecheck
```

## Project Structure

```
async-task-q-monitor/
├── src/
│   └── async_task_q_monitor/     # Python package
│       ├── __init__.py
│       ├── __main__.py           # CLI entry point
│       ├── api/                  # FastAPI routes
│       ├── models/               # Pydantic models
│       ├── services/             # Business logic
│       ├── websocket/            # WebSocket handling
│       └── static/               # Built frontend (generated)
├── frontend/                     # React frontend source
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── tests/                        # Python tests
├── pyproject.toml
└── justfile
```

## License

MIT License - see [LICENSE](LICENSE) for details.
