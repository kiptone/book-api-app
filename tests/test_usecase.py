from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models import EventStatus
from src.usecases import (
    CreateTicketUseCase,
    EventNotFoundError,
    EventNotPublishedError,
    SeatUnavailableError,
)


@pytest.mark.asyncio
async def test_create_ticket_success():
    client = MagicMock()
    client.get_seats = AsyncMock(return_value=["A1", "A2"])
    client.register = AsyncMock(return_value="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    event = MagicMock()
    event.status = EventStatus.PUBLISHED

    event.registration_deadline = datetime.now(timezone.utc) + timedelta(days=1)
    event.id = "22222222-2222-2222-2222-222222222222"

    event_repo = MagicMock()
    event_repo.get = AsyncMock(return_value=event)

    ticket_repo = MagicMock()
    ticket_repo.create = AsyncMock()

    usecase = CreateTicketUseCase(client, event_repo, ticket_repo)

    ticket_id = await usecase.execute(
        event_id=event.id,
        first_name="Ivan",
        last_name="Ivanov",
        email="ivan@example.com",
        seat="A1",
    )

    assert ticket_id == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    ticket_repo.create.assert_awaited()


@pytest.mark.asyncio
async def test_create_ticket_event_not_found():
    client = MagicMock()
    event_repo = MagicMock()
    event_repo.get = AsyncMock(return_value=None)
    ticket_repo = MagicMock()
    usecase = CreateTicketUseCase(client, event_repo, ticket_repo)

    with pytest.raises(EventNotFoundError):
        await usecase.execute(
            event_id="nonexistent",
            first_name="Ivan",
            last_name="Ivanov",
            email="ivan@example.com",
            seat="A1",
        )


@pytest.mark.asyncio
async def test_create_ticket_event_not_published():
    client = MagicMock()

    event = MagicMock()
    event.status = EventStatus.NEW

    event.registration_deadline = datetime.now(timezone.utc) + timedelta(days=1)
    event_repo = MagicMock()
    event_repo.get = AsyncMock(return_value=event)
    ticket_repo = MagicMock()
    usecase = CreateTicketUseCase(client, event_repo, ticket_repo)

    with pytest.raises(EventNotPublishedError):
        await usecase.execute(
            event_id="id",
            first_name="Ivan",
            last_name="Ivanov",
            email="ivan@example.com",
            seat="A1",
        )


@pytest.mark.asyncio
async def test_create_ticket_seat_unavailable():
    client = MagicMock()
    client.get_seats = AsyncMock(return_value=["A1", "A2"])
    client.register = AsyncMock()

    event = MagicMock()
    event.status = EventStatus.PUBLISHED
    event.registration_deadline = datetime.now(timezone.utc) + timedelta(days=1)
    event.id = "22222222-2222-2222-2222-222222222222"

    event_repo = MagicMock()
    event_repo.get = AsyncMock(return_value=event)
    ticket_repo = MagicMock()
    ticket_repo.create = AsyncMock()

    usecase = CreateTicketUseCase(client, event_repo, ticket_repo)

    with pytest.raises(SeatUnavailableError):
        await usecase.execute(
            event_id=event.id,
            first_name="Ivan",
            last_name="Ivanov",
            email="ivan@example.com",
            seat="B99",
        )
    client.register.assert_not_awaited()
