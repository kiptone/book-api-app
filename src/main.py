import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from . import schemas
from .clients import EventsProviderClient
from .database import async_session, engine, get_db, wait_for_db
from .models import Base
from .repositories import EventRepository, TicketRepository
from .sync import sync_events
from .usecases import (
    CancelTicketUseCase,
    CreateTicketUseCase,
    EventNotFoundError,
    EventNotPublishedError,
    RegistrationDeadlinePassedError,
    SeatUnavailableError,
)

logger = logging.getLogger(__name__)
client = EventsProviderClient()

# Кэш свободных мест в памяти: {event_id: (expires_at, seats)}
SEATS_CACHE: dict[str, tuple[datetime, list[str]]] = {}


async def _run_scheduled_sync():
    async with async_session() as session:
        await sync_events(client, session)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ждём PostgreSQL
    await wait_for_db()
    # Создание таблиц
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Запуск фонового планировщика
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _run_scheduled_sync,
        "interval",
        hours=24,
        id="daily_sync",
    )
    scheduler.start()
    yield
    await client.close()
    scheduler.shutdown()


app = FastAPI(title="Events Aggregator", lifespan=lifespan)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/debug/status")
async def debug_status(db: AsyncSession = Depends(get_db)):
    """Debug endpoint: показывает состояние синхронизации и БД."""
    from sqlalchemy import func, select
    from .models import SyncMeta, Event, Place

    # Сколько событий в БД
    event_count = await db.execute(select(func.count(Event.id)))
    event_count = event_count.scalar() or 0

    # Сколько площадок в БД
    place_count = await db.execute(select(func.count(Place.id)))
    place_count = place_count.scalar() or 0

    # Последняя синхронизация
    meta_result = await db.execute(select(SyncMeta).limit(1))
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


@app.post("/api/sync/trigger")
async def trigger_sync(db: AsyncSession = Depends(get_db)):
    try:
        await sync_events(client, db)
        # Гарантируем коммит после синхронизации
        await db.commit()
        return {"status": "sync_completed"}
    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Sync failed: {type(e).__name__}")


@app.get("/api/events", response_model=schemas.EventListResponse)
async def list_events(
    date_from: str = Query(None, description="YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    repo = EventRepository(db)
    events = await repo.list_filtered(date_from, page, page_size)
    count = await repo.count_filtered(date_from)
    next_url = (
        f"/api/events?page={page + 1}&page_size={page_size}" if len(events) == page_size else None
    )
    prev_url = f"/api/events?page={page - 1}&page_size={page_size}" if page > 1 else None
    return {
        "count": count,
        "next": next_url,
        "previous": prev_url,
        "results": events,
    }


@app.get("/api/events/{event_id}", response_model=schemas.EventDetail)
async def get_event(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    repo = EventRepository(db)
    event = await repo.get(str(event_id))
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@app.get("/api/events/{event_id}/seats", response_model=schemas.SeatsResponse)
async def get_seats(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    repo = EventRepository(db)
    event = await repo.get(str(event_id))
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.status != "published":
        raise HTTPException(status_code=400, detail="Event is not published yet")
    event_key = str(event_id)
    now = datetime.now(timezone.utc)
    cached = SEATS_CACHE.get(event_key)
    if cached and cached[0] > now:
        seats = cached[1]
    else:
        seats = await client.get_seats(event_key)
        SEATS_CACHE[event_key] = (now + timedelta(seconds=30), seats)
    return {"event_id": event_key, "available_seats": seats}


@app.post("/api/tickets", response_model=schemas.TicketResponse, status_code=201)
async def register_ticket(body: schemas.TicketCreateRequest, db: AsyncSession = Depends(get_db)):
    repo = EventRepository(db)
    ticket_repo = TicketRepository(db)
    usecase = CreateTicketUseCase(client, repo, ticket_repo)
    try:
        ticket_id = await usecase.execute(
            event_id=body.event_id,
            first_name=body.first_name,
            last_name=body.last_name,
            email=body.email,
            seat=body.seat,
        )
    except EventNotFoundError:
        raise HTTPException(status_code=404, detail="Event not found")
    except EventNotPublishedError:
        raise HTTPException(status_code=400, detail="Event is not published")
    except RegistrationDeadlinePassedError:
        raise HTTPException(status_code=400, detail="Registration deadline passed")
    except SeatUnavailableError as e:
        raise HTTPException(status_code=400, detail=f"Seat '{e}' is not available")
    except httpx.HTTPStatusError as e:
        # Провайдер отклонил регистрацию — логируем тело ответа для отладки
        error_body = e.response.text[:200] if e.response else "No response"
        raise HTTPException(status_code=400, detail=f"Provider rejected: {error_body}")
    await db.commit()
    return {"ticket_id": ticket_id}


@app.delete("/api/tickets/{ticket_id}", response_model=schemas.SuccessResponse)
async def cancel_ticket(ticket_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    ticket_repo = TicketRepository(db)
    repo = EventRepository(db)
    usecase = CancelTicketUseCase(client, ticket_repo, repo)
    ticket = await ticket_repo.get(str(ticket_id))
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    try:
        await usecase.execute(ticket_id=str(ticket_id), event_id=str(ticket.event_id))
    except EventNotFoundError:
        raise HTTPException(status_code=404, detail="Event not found")
    except RegistrationDeadlinePassedError:
        raise HTTPException(status_code=400, detail="Event already passed")
    await db.commit()
    return {"success": True}
