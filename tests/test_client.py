from unittest.mock import AsyncMock, MagicMock

import pytest

from src.clients import EventsProviderClient


@pytest.mark.asyncio
async def test_get_seats():
    client = EventsProviderClient(base_url="http://test", api_key="key")
    mock_response = MagicMock()
    mock_response.json.return_value = {"seats": ["A1", "A2"]}
    mock_response.raise_for_status = MagicMock()
    client.client.get = AsyncMock(return_value=mock_response)
    seats = await client.get_seats("ev1")
    assert seats == ["A1", "A2"]
    client.client.get.assert_called_once_with("http://test/api/events/ev1/seats/")


@pytest.mark.asyncio
async def test_register():
    client = EventsProviderClient(base_url="http://test", api_key="key")
    mock_response = MagicMock()
    mock_response.json.return_value = {"ticket_id": "1234"}
    mock_response.raise_for_status = MagicMock()
    client.client.post = AsyncMock(return_value=mock_response)
    ticket_id = await client.register("ev1", "Ivan", "Ivanov", "ivan@example.com", "A1")
    assert ticket_id == "1234"
    client.client.post.assert_called_once()


@pytest.mark.asyncio
async def test_unregister():
    client = EventsProviderClient(base_url="http://test", api_key="key")
    mock_response = MagicMock()
    mock_response.json.return_value = {"success": True}
    mock_response.raise_for_status = MagicMock()
    client.client.request = AsyncMock(return_value=mock_response)
    result = await client.unregister("ev1", "ticket123")
    assert result is True
    client.client.request.assert_called_once()
