import logging
from typing import Optional

import httpx

from .config import settings

logger = logging.getLogger(__name__)


class EventsProviderClient:
    """Клиент для работы с Events Provider API."""

    def __init__(
        self,
        base_url: str = settings.events_provider_base_url,
        api_key: str = settings.events_provider_api_key,
    ):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"x-api-key": api_key},
            verify=False,
            follow_redirects=True,
        )

    async def close(self):
        await self.client.aclose()

    async def get(self, path: str) -> dict:
        """Выполнить GET-запрос по пути и вернуть JSON."""
        response = await self.client.get(path)
        response.raise_for_status()
        return response.json()

    async def get_events_page(self, changed_at: str) -> dict:
        """Возвращает одну страницу событий."""
        url = f"/api/events/?changed_at={changed_at}"
        logger.info(f"Fetching events page: {url}")
        try:
            response = await self.client.get(url, follow_redirects=True)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Got {len(data.get('results', []))} events, next={data.get('next')}")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch events page: {e}", exc_info=True)
            raise

    async def get_seats(self, event_id: str) -> list[str]:
        path = f"/api/events/{event_id}/seats/"
        response = await self.client.get(path)
        response.raise_for_status()
        return response.json()["seats"]

    async def register(
        self, event_id: str, first_name: str, last_name: str, email: str, seat: str
    ) -> str:
        path = f"/api/events/{event_id}/register/"
        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "seat": seat,
        }
        response = await self.client.post(path, json=payload)
        response.raise_for_status()
        return response.json()["ticket_id"]

    async def unregister(self, event_id: str, ticket_id: str) -> bool:
        path = f"/api/events/{event_id}/unregister/"
        payload = {"ticket_id": ticket_id}
        response = await self.client.request("DELETE", path, json=payload)
        response.raise_for_status()
        return response.json()["success"]


class EventsPaginator:
    """Итератор для обхода всех страниц событий через cursor-based пагинацию."""

    def __init__(self, client: EventsProviderClient, changed_at: str = "2000-01-01"):
        self.client = client
        self.changed_at = changed_at
        self._next_url: Optional[str] = None
        self._initial = True
        self._buffer: list[dict] = []
        self._pages_loaded = 0
        self._total_events = 0

    def __aiter__(self):
        return self

    async def __anext__(self) -> dict:
        # Если буфер пуст — грузим новую страницу
        while not self._buffer:
            if self._initial:
                page = await self.client.get_events_page(self.changed_at)
                self._initial = False
                self._next_url = page.get("next")
                self._pages_loaded += 1
            elif self._next_url is None:
                logger.info(
                    f"Paginator finished: {self._pages_loaded} pages, {self._total_events} events"
                )
                raise StopAsyncIteration
            else:
                page = await self.client.get(self._next_url)
                self._next_url = page.get("next")
                self._pages_loaded += 1
            self._buffer = page.get("results", [])
            self._total_events += len(self._buffer)
            if not self._buffer and self._next_url:
                continue

        return self._buffer.pop(0)
