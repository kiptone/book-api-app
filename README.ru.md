# Events Aggregator

Backend-сервис агрегатор для работы с Events Provider API. Предоставляет удобный REST API для управления событиями и мероприятиями.

## Возможности

- **Фоновая синхронизация** — автоматическая синхронизация событий раз в 24 часа
- **Ручная синхронизация** — endpoint для принудительного запуска синхронизации
- **Удобная пагинация** — page/page_size вместо cursor-based
- **Фильтрация по дате** — SQL-фильтрация событий по дате начала
- **Кэширование мест** — 30-секундный кэш свободных мест
- **Валидация данных** — проверка статуса события, дедлайна, доступности места

## Технологический стек

- Python 3.14
- FastAPI
- PostgreSQL + asyncpg
- SQLAlchemy (async)
- APScheduler (фоновые задачи)
- httpx (HTTP-клиент)
- Docker & Docker Compose

## Быстрый старт

### Требования

- Docker Desktop
- uv (Python package manager) — `curl -LsSf https://astral.sh/uv/install.sh | sh`

### Запуск

```bash
# Клонировать репозиторий
git clone https://github.com/<your-org>/events-aggregator.git
cd events-aggregator

# Настроить переменные окружения
cp .env.example .env
# Отредактировать .env (API ключ из LMS)

# Запустить через Docker Compose
docker compose up -d

# Проверить логи
docker compose logs -f app
```

### Переменные окружения

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/events
EVENTS_PROVIDER_BASE_URL=https://events-provider.dev-2.python-labs.ru
EVENTS_PROVIDER_API_KEY=<your-api-key>
```

## API Endpoints

### Health Check
```bash
GET /api/health
# Ответ: {"status": "ok"}
```

### Debug статус
```bash
GET /api/debug/status
# Ответ: информация о количестве событий и последней синхронизации
```

### Синхронизация
```bash
POST /api/sync/trigger
# Ответ: {"status": "sync_completed"}
```

### Список событий
```bash
GET /api/events?date_from=2026-01-01&page=1&page_size=20
# Ответ: пагинированный список событий из локальной БД
```

### Детали события
```bash
GET /api/events/{event_id}
# Ответ: полное описание события с place
```

### Свободные места
```bash
GET /api/events/{event_id}/seats
# Ответ: {"event_id": "...", "available_seats": ["A1", "A2", ...]}
```

### Регистрация
```bash
POST /api/tickets
Content-Type: application/json

{
  "event_id": "uuid",
  "first_name": "Ivan",
  "last_name": "Ivanov",
  "email": "ivan@example.com",
  "seat": "A15"
}
# Ответ: {"ticket_id": "uuid"}
```

### Отмена регистрации
```bash
DELETE /api/tickets/{ticket_id}
# Ответ: {"success": true}
```

## Тесты

```bash
# Установить зависимости
uv sync --extra dev

# Запустить тесты
uv run pytest -v

# Линтер
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

## Архитектура

```
src/
├── main.py                    # FastAPI app, endpoints → делегирует в сервисы
├── services/
│   ├── events_service.py      # Бизнес-логика: события, синхронизация, места (кэш 30с)
│   ├── tickets_service.py     # Бизнес-логика: билеты
│   └── debug_service.py       # Отладочная информация
├── usecases.py                # Чистые use cases с typing.Protocol DI
├── repositories.py            # Repository pattern (EventRepository, TicketRepository)
├── clients.py                 # EventsProviderClient + EventsPaginator (cursor-based)
├── sync.py                    # Оркестрация синхронизации
├── models.py                  # SQLAlchemy модели + EventStatus enum
├── schemas.py                 # Pydantic схемы
├── config.py                  # pydantic-settings
└── database.py                # SQLAlchemy async session factory
```

### Ключевые паттерны

- **Service Layer** — бизнес-логика отделена от API в `services/`
- **Repository** — абстракция доступа к БД
- **Use Cases** — чистая бизнес-логика с `typing.Protocol` для DI
- **Iterator** — `EventsPaginator` для обхода cursor-based пагинации

## CI/CD

GitHub Actions автоматически проверяет:
- `ruff check` — линтинг (PEP8)
- `ruff format --check` — форматирование

Проверка запускается **до деплоя** на платформу.

