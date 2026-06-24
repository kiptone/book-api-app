# Events Aggregator

Backend service aggregating Events Provider API with extended functionality.

## Stack

- Python 3.14, FastAPI
- PostgreSQL + asyncpg + SQLAlchemy (async)
- APScheduler (background sync)
- Docker Compose

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/sync/trigger` | Manual sync trigger |
| GET | `/api/events` | List events (pagination, date filter) |
| GET | `/api/events/{id}` | Event details |
| GET | `/api/events/{id}/seats` | Available seats (30s cache) |
| POST | `/api/tickets` | Register for event |
| DELETE | `/api/tickets/{id}` | Cancel registration |

## Quick Start

```bash
cp .env.example .env  # Set EVENTS_PROVIDER_API_KEY
docker compose up -d
```

## Tests

```bash
uv sync --extra dev
uv run pytest -v
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

## Architecture

- **Repository pattern**: `EventRepository`, `TicketRepository`
- **Use Cases**: `CreateTicketUseCase`, `CancelTicketUseCase`
- **Protocols**: Dependency injection via `typing.Protocol`
- **Iterator**: `EventsPaginator` for cursor-based pagination

## CI/CD

GitHub Actions: `ruff check` + `ruff format` (blocks deploy on failure).

---

📖 Full documentation in Russian: [README.ru.md](README.ru.md)
