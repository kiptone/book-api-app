import pytest

from src.clients import EventsPaginator, EventsProviderClient


@pytest.mark.asyncio
async def test_paginator_iterates_all():
    client = EventsProviderClient(base_url="http://test", api_key="key")
    pages = [
        {
            "results": [{"id": 1}, {"id": 2}],
            "next": "http://test/api/events/?changed_at=2000-01-01&cursor=abc",
        },
        {"results": [{"id": 3}], "next": None},
    ]

    call_count = 0

    async def mock_get_events_page(changed_at):
        nonlocal call_count
        call_count += 1
        return pages[0]

    async def mock_get(path):
        nonlocal call_count
        call_count += 1
        return pages[1]

    client.get_events_page = mock_get_events_page
    client.get = mock_get

    paginator = EventsPaginator(client, "2000-01-01")
    results = []
    async for event in paginator:
        results.append(event)
    assert len(results) == 3
    assert results[0]["id"] == 1
    assert results[1]["id"] == 2
    assert results[2]["id"] == 3


@pytest.mark.asyncio
async def test_paginator_empty():
    client = EventsProviderClient(base_url="http://test", api_key="key")

    async def mock_get_events_page(changed_at):
        return {"results": [], "next": None}

    client.get_events_page = mock_get_events_page

    paginator = EventsPaginator(client, "2000-01-01")
    results = []
    async for event in paginator:
        results.append(event)
    assert len(results) == 0
