# Events Aggregator

Backend service aggregating Events Provider API with extended functionality.

## Stack

- Python 3.14, FastAPI
- PostgreSQL + asyncpg + SQLAlchemy (async)
- APScheduler (background sync)
- httpx (HTTP client)
- Docker Compose

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/debug/status` | Debug sync status |
| POST | `/api/sync/trigger` | Manual sync trigger |
| GET | `/api/events` | List events (pagination, date filter) |
| GET | `/api/events/{id}` | Event details |
| GET | `/api/events/{id}/seats` | Available seats (30s cache) |
| POST | `/api/tickets` | Register for event |
| DELETE | `/api/tickets/{id}` | Cancel registration |

## Quick Start

```bash
cp .env.example .env           # Set EVENTS_PROVIDER_API_KEY
docker compose up -d           # Start PostgreSQL + app
```

## Tests

```bash
# Install uv if needed: curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync --extra dev
uv run pytest -v
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

## Architecture

```
src/
├── main.py                    # FastAPI app, endpoints → delegates to services
├── services/
│   ├── events_service.py      # Business logic: events, sync, seats (with 30s cache)
│   ├── tickets_service.py     # Business logic: tickets
│   └── debug_service.py       # Debug status
├── usecases.py                # Pure use cases with typing.Protocol DI
├── repositories.py            # Repository pattern (EventRepository, TicketRepository)
├── clients.py                 # EventsProviderClient + EventsPaginator (cursor-based)
├── sync.py                    # Sync orchestration
├── models.py                  # SQLAlchemy models + EventStatus enum
├── schemas.py                 # Pydantic schemas
├── config.py                  # pydantic-settings
└── database.py                # SQLAlchemy async session factory
```

### Key Patterns

- **Service Layer** — business logic separated from API (`services/`)
- **Repository** — data access abstraction in `repositories.py`
- **Use Cases** — pure business logic with `typing.Protocol` for DI
- **Iterator** — `EventsPaginator` for cursor-based pagination

## CI/CD

GitHub Actions: `ruff check` + `ruff format` (blocks deploy on failure).

---

📖 Full documentation in Russian: [README.ru.md](README.ru.md)
