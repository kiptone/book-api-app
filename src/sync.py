import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from .clients import EventsPaginator, EventsProviderClient
from .models import Event, Place
from .repositories import SyncMetaRepository

logger = logging.getLogger(__name__)


def parse_uuid(value: str) -> uuid.UUID:
    """Конвертирует строку в UUID."""
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(value)


def parse_datetime(value: str) -> datetime:
    """Парсит ISO 8601 дату."""
    return datetime.fromisoformat(value)


async def sync_events(client: EventsProviderClient, session: AsyncSession):
    meta_repo = SyncMetaRepository(session)
    meta = await meta_repo.get()
    last_changed = meta.last_changed_at.strftime("%Y-%m-%d")
    logger.info(f"Starting sync with changed_at={last_changed}")

    paginator = EventsPaginator(client, changed_at=last_changed)
    max_changed = meta.last_changed_at
    events_count = 0
    errors_count = 0

    async for event_data in paginator:
        # Используем savepoint для каждого события
        # Если одно событие упадет - остальные сохранятся
        try:
            async with session.begin_nested():
                # Upsert place
                place_data = event_data["place"]
                place = Place(
                    id=parse_uuid(place_data["id"]),
                    name=place_data["name"],
                    city=place_data["city"],
                    address=place_data["address"],
                    seats_pattern=place_data["seats_pattern"],
                    changed_at=parse_datetime(place_data["changed_at"]),
                    created_at=parse_datetime(place_data["created_at"]),
                )
                await session.merge(place)
                # Upsert event
                event = Event(
                    id=parse_uuid(event_data["id"]),
                    name=event_data["name"],
                    place_id=parse_uuid(place_data["id"]),
                    event_time=parse_datetime(event_data["event_time"]),
                    registration_deadline=parse_datetime(event_data["registration_deadline"]),
                    status=event_data["status"],
                    number_of_visitors=event_data["number_of_visitors"],
                    changed_at=parse_datetime(event_data["changed_at"]),
                    created_at=parse_datetime(event_data["created_at"]),
                    status_changed_at=parse_datetime(event_data["status_changed_at"]),
                )
                await session.merge(event)
                events_count += 1
                # Track max changed_at
                event_changed = parse_datetime(event_data["changed_at"])
                if event_changed > max_changed:
                    max_changed = event_changed
        except Exception as e:
            errors_count += 1
            logger.error(
                f"Error processing event {event_data.get('id', 'unknown')}: {e}", exc_info=True
            )
            # Savepoint автоматически откатится, продолжаем со следующим событием
            continue

    await meta_repo.update(
        last_changed_at=max_changed,
        last_sync_time=datetime.now(timezone.utc),
        status="success" if errors_count == 0 else "partial",
    )
    logger.info(f"Sync completed: {events_count} events processed, {errors_count} errors")
