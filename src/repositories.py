import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import Event, SyncMeta, Ticket


class EventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, event_id: str) -> Event | None:
        query = select(Event).options(selectinload(Event.place)).where(Event.id == event_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_filtered(self, date_from: str | None, page: int, page_size: int):
        query = select(Event).options(selectinload(Event.place))
        if date_from:
            query = query.where(Event.event_time >= date_from)
        query = query.order_by(Event.event_time).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count_filtered(self, date_from: str | None) -> int:
        query = select(func.count(Event.id))
        if date_from:
            query = query.where(Event.event_time >= date_from)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def upsert(self, event: Event):
        await self.session.merge(event)


class SyncMetaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self) -> SyncMeta:
        result = await self.session.execute(select(SyncMeta).limit(1))
        meta = result.scalar_one_or_none()
        if not meta:
            from datetime import datetime, timezone

            meta = SyncMeta(
                last_changed_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
                last_sync_time=datetime.now(timezone.utc),
                status="idle",
            )
            self.session.add(meta)
            await self.session.flush()
        return meta

    async def update(self, **kwargs):
        meta = await self.get()
        for key, value in kwargs.items():
            setattr(meta, key, value)
        await self.session.flush()


class TicketRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        ticket_id: str,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ):
        tid = uuid.UUID(ticket_id)
        ticket = Ticket(
            ticket_id=tid,
            event_id=uuid.UUID(event_id),
            first_name=first_name,
            last_name=last_name,
            email=email,
            seat=seat,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(ticket)
        await self.session.flush()

    async def delete(self, ticket_id: str):
        try:
            tid = uuid.UUID(ticket_id)
        except ValueError:
            return
        obj = await self.session.get(Ticket, tid)
        if obj:
            await self.session.delete(obj)
            await self.session.flush()

    async def get(self, ticket_id: str) -> Ticket | None:
        try:
            tid = uuid.UUID(ticket_id)
        except ValueError:
            return None
        return await self.session.get(Ticket, tid)
