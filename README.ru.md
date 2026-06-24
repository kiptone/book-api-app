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
- uv (Python package manager)

### Запуск

```bash
# Клонировать репозиторий
git clone https://github.com/kiptone/book-api-app.git
cd book-api-app

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

### Синхронизация
```bash
POST /api/sync/trigger
# Ответ: {"status": "sync_started"}
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
├── clients.py          # Events Provider API клиент
├── config.py           # Настройки (pydantic-settings)
├── database.py         # SQLAlchemy сессии
├── main.py             # FastAPI приложение, endpoints
├── models.py           # SQLAlchemy модели
├── repositories.py     # Repository pattern для БД
├── schemas.py          # Pydantic схемы
├── sync.py             # Логика синхронизации
└── usecases.py         # Бизнес-логика (use cases)
```

### Паттерны

- **Repository** — абстракция доступа к БД
- **Use Cases** — бизнес-логика, независимая от фреймворков
- **Protocol (typing)** — интерфейсы для внедрения зависимостей
- **Iterator** — EventsPaginator для обхода cursor-based пагинации

## CI/CD

GitHub Actions автоматически проверяет:
- `ruff check` — линтинг (PEP8)
- `ruff format --check` — форматирование

Проверка запускается **до деплоя** на платформу.

