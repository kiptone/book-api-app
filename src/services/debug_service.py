from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Event, Place, SyncMeta


class DebugStatusService:
    """Сервис для получения отладочной информации о состоянии системы."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_status(self) -> dict:
        event_count = await self.session.execute(select(func.count(Event.id)))
        event_count = event_count.scalar() or 0

        place_count = await self.session.execute(select(func.count(Place.id)))
        place_count = place_count.scalar() or 0

        meta_result = await self.session.execute(select(SyncMeta).limit(1))
        meta = meta_result.scalar_one_or_none()

        return {
            "events_count": event_count,
            "places_count": place_count,
            "last_sync": {
                "last_changed_at": meta.last_changed_at.isoformat() if meta else None,
                "last_sync_time": meta.last_sync_time.isoformat() if meta else None,
                "status": meta.status if meta else None,
            }
            if meta
            else None,
        }
