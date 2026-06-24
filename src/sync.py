import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from .clients import EventsPaginator, EventsProviderClient
from .models import Event, Place
from .repositories import SyncMetaRepository

logger = logging.getLogger(__name__)


async def sync_events(client: EventsProviderClient, session: AsyncSession):
    meta_repo = SyncMetaRepository(session)
    meta = await meta_repo.get()
    last_changed = meta.last_changed_at.strftime("%Y-%m-%d")
    logger.info(f"Starting sync with changed_at={last_changed}")
    paginator = EventsPaginator(client, changed_at=last_changed)
    max_changed = meta.last_changed_at
    async for event_data in paginator:
        # Upsert place
        place_data = event_data["place"]
        place = Place(
            id=place_data["id"],
            name=place_data["name"],
            city=place_data["city"],
            address=place_data["address"],
            seats_pattern=place_data["seats_pattern"],
            changed_at=datetime.fromisoformat(place_data["changed_at"]),
            created_at=datetime.fromisoformat(place_data["created_at"]),
        )
        await session.merge(place)
        # Upsert event
        event = Event(
            id=event_data["id"],
            name=event_data["name"],
            place_id=place_data["id"],
            event_time=datetime.fromisoformat(event_data["event_time"]),
            registration_deadline=datetime.fromisoformat(event_data["registration_deadline"]),
            status=event_data["status"],
            number_of_visitors=event_data["number_of_visitors"],
            changed_at=datetime.fromisoformat(event_data["changed_at"]),
            created_at=datetime.fromisoformat(event_data["created_at"]),
            status_changed_at=datetime.fromisoformat(event_data["status_changed_at"]),
        )
        await session.merge(event)
        # Track max changed_at
        event_changed = datetime.fromisoformat(event_data["changed_at"])
        if event_changed > max_changed:
            max_changed = event_changed
    await meta_repo.update(
        last_changed_at=max_changed,
        last_sync_time=datetime.now(timezone.utc),
        status="success",
    )
    await session.commit()
    logger.info("Sync completed")
