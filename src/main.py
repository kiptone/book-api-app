import logging
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients import EventsProviderClient
from src.database import async_session, engine, get_db, wait_for_db
from src.models import Base
from src.schemas import (
    EventDetail,
    EventListResponse,
    SeatsResponse,
    SuccessResponse,
    TicketCreateRequest,
    TicketResponse,
)
from src.services.debug_service import DebugStatusService
from src.services.events_service import EventsNotFoundError, EventsNotPublishedError, EventsService
from src.services.tickets_service import TicketsNotFoundError, TicketsService

logger = logging.getLogger(__name__)
client = EventsProviderClient()


async def _run_scheduled_sync():
    async with async_session() as session:
        service = EventsService(session, client)
        await service.trigger_sync()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await wait_for_db()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"detail": exc.errors()},
    )


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/debug/status")
async def debug_status(db: AsyncSession = Depends(get_db)):
    service = DebugStatusService(db)
    return await service.get_status()


@app.post("/api/sync/trigger")
async def trigger_sync(db: AsyncSession = Depends(get_db)):
    try:
        service = EventsService(db, client)
        return await service.trigger_sync()
    except Exception as e:
        logger.error("Sync failed: %s", e, exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Sync failed: {type(e).__name__}")


@app.get("/api/events", response_model=EventListResponse)
async def list_events(
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    service = EventsService(db, client)
    events, count, next_url, prev_url = await service.list_events(date_from, page, page_size)
    return {
        "count": count,
        "next": next_url,
        "previous": prev_url,
        "results": events,
    }


@app.get("/api/events/{event_id}", response_model=EventDetail)
async def get_event(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = EventsService(db, client)
    try:
        event = await service.get_event(str(event_id))
        return event
    except EventsNotFoundError:
        raise HTTPException(status_code=404, detail="Event not found")


@app.get("/api/events/{event_id}/seats", response_model=SeatsResponse)
async def get_seats(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = EventsService(db, client)
    try:
        seats = await service.get_seats(str(event_id))
        return {"event_id": str(event_id), "available_seats": seats}
    except EventsNotFoundError:
        raise HTTPException(status_code=404, detail="Event not found")
    except EventsNotPublishedError:
        raise HTTPException(status_code=400, detail="Event is not published yet")


@app.post("/api/tickets", response_model=TicketResponse, status_code=201)
async def register_ticket(body: TicketCreateRequest, db: AsyncSession = Depends(get_db)):
    service = TicketsService(db, client)
    try:
        ticket_id = await service.create_ticket(
            body.event_id,
            body.first_name,
            body.last_name,
            body.email,
            body.seat,
        )
        return {"ticket_id": ticket_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/tickets/{ticket_id}", response_model=SuccessResponse)
async def cancel_ticket(ticket_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = TicketsService(db, client)
    try:
        await service.cancel_ticket(str(ticket_id))
        return {"success": True}
    except TicketsNotFoundError:
        raise HTTPException(status_code=404, detail="Ticket not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
