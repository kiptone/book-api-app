from unittest.mock import AsyncMock, MagicMock

import pytest

from src.repositories import TicketRepository


@pytest.mark.asyncio
async def test_ticket_repository_create_get_delete():
    session = MagicMock()
    session.flush = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.delete = AsyncMock()

    repo = TicketRepository(session)

    # create should add and flush
    await repo.create(
        ticket_id="11111111-1111-1111-1111-111111111111",
        event_id="22222222-2222-2222-2222-222222222222",
        first_name="Ivan",
        last_name="Ivanov",
        email="ivan@example.com",
        seat="A1",
    )
    assert session.add.called
    assert session.flush.await_count >= 1

    # get should call session.get
    session.get.return_value = MagicMock()
    await repo.get("11111111-1111-1111-1111-111111111111")
    session.get.assert_called()

    # delete should call session.get and session.delete
    session.get.return_value = MagicMock()
    await repo.delete("11111111-1111-1111-1111-111111111111")
    session.delete.assert_awaited()
    assert session.flush.await_count >= 1
