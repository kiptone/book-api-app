from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.clients import EventsProviderClient
from src.models import Event, EventStatus
from src.repositories import EventRepository, SyncMetaRepository
from src.sync import sync_events


class EventsNotFoundError(Exception):
    pass


class EventsNotPublishedError(Exception):
    pass


# Кэш свободных мест в памяти: {event_id: (expires_at, seats)}
_SEATS_CACHE: dict[str, tuple[datetime, list[str]]] = {}


class EventsService:
    """Сервис для работы с событиями."""

    def __init__(
        self,
        session: AsyncSession,
        client: EventsProviderClient,
    ):
        self.session = session
        self.client = client
        self.event_repo = EventRepository(session)
        self.sync_repo = SyncMetaRepository(session)

    async def trigger_sync(self) -> dict:
        await sync_events(self.client, self.session)
        await self.session.commit()
        return {"status": "sync_completed"}

    async def list_events(
        self, date_from: Optional[str], page: int, page_size: int
    ) -> tuple[list[Event], int]:
        """Возвращает список событий и общее количество, без URL пагинации"""
        events = await self.event_repo.list_filtered(date_from, page, page_size)
        count = await self.event_repo.count_filtered(date_from)
        return events, count

    async def get_event(self, event_id: str) -> Event:
        event = await self.event_repo.get(event_id)
        if not event:
            raise EventsNotFoundError()
        return event

    async def get_seats(self, event_id: str) -> list[str]:
        event = await self.event_repo.get(event_id)
        if not event:
            raise EventsNotFoundError()
        if event.status != EventStatus.PUBLISHED:
            raise EventsNotPublishedError()

        # Кэш в памяти на 30 секунд
        now = datetime.now(timezone.utc)
        cached = _SEATS_CACHE.get(event_id)
        if cached and cached[0] > now:
            return cached[1]

        seats = await self.client.get_seats(event_id)
        _SEATS_CACHE[event_id] = (now + timedelta(seconds=30), seats)
        return seats
