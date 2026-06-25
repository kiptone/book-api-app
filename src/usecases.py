import typing
from datetime import datetime, timezone

from src.models import Event, EventStatus, Ticket


class EventNotFoundError(Exception):
    pass


class EventNotPublishedError(Exception):
    pass


class RegistrationDeadlinePassedError(Exception):
    pass


class SeatUnavailableError(Exception):
    """Место уже занято или недоступно для регистрации."""

    pass


class IEventsProviderClient(typing.Protocol):
    """Protocol for Events Provider API client."""

    async def get_seats(self, event_id: str) -> list[str]:
        """Return list of available seats for an event."""
        ...

    async def register(
        self, event_id: str, first_name: str, last_name: str, email: str, seat: str
    ) -> str:
        """Register a user for an event and return ticket_id."""
        ...

    async def unregister(self, event_id: str, ticket_id: str) -> bool:
        """Unregister a user from an event."""
        ...


class IEventRepository(typing.Protocol):
    """Protocol for Event repository."""

    async def get(self, event_id: str) -> Event | None:
        """Get event by ID."""
        ...


class ITicketRepository(typing.Protocol):
    """Protocol for Ticket repository."""

    async def create(
        self,
        ticket_id: str,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> None:
        """Create a ticket record."""
        ...

    async def delete(self, ticket_id: str) -> None:
        """Delete a ticket by ID."""
        ...

    async def get(self, ticket_id: str) -> "Ticket | None":
        """Get a ticket by ID."""
        ...


class CreateTicketUseCase:
    def __init__(
        self,
        client: IEventsProviderClient,
        event_repo: IEventRepository,
        ticket_repo: ITicketRepository,
    ):
        self.client = client
        self.event_repo = event_repo
        self.ticket_repo = ticket_repo

    async def execute(
        self, event_id: str, first_name: str, last_name: str, email: str, seat: str
    ) -> str:
        event = await self.event_repo.get(event_id)
        if not event:
            raise EventNotFoundError()
        if event.status != EventStatus.PUBLISHED:
            raise EventNotPublishedError()
        if event.registration_deadline < datetime.now(timezone.utc):
            raise RegistrationDeadlinePassedError()

        available_seats = await self.client.get_seats(event_id)
        if seat not in available_seats:
            raise SeatUnavailableError(seat)

        ticket_id = await self.client.register(event_id, first_name, last_name, email, seat)
        await self.ticket_repo.create(ticket_id, event_id, first_name, last_name, email, seat)
        return ticket_id


class CancelTicketUseCase:
    def __init__(
        self,
        client: IEventsProviderClient,
        ticket_repo: ITicketRepository,
        event_repo: IEventRepository,
    ):
        self.client = client
        self.ticket_repo = ticket_repo
        self.event_repo = event_repo

    async def execute(self, ticket_id: str, event_id: str) -> bool:
        ticket = await self.ticket_repo.get(ticket_id)
        if not ticket:
            raise EventNotFoundError("Ticket not found")

        event = await self.event_repo.get(str(event_id))
        if not event:
            raise EventNotFoundError("Event not found")

        if event.event_time < datetime.now(timezone.utc):
            raise RegistrationDeadlinePassedError("Event already passed")

        ok = await self.client.unregister(str(event_id), ticket_id)
        if not ok:
            raise RuntimeError("Failed to unregister in provider")

        await self.ticket_repo.delete(ticket_id)
        return True


class ListEventsUseCase:
    """Use case для получения списка событий с пагинацией."""

    def __init__(self, event_repo: IEventRepository):
        self.event_repo = event_repo

    async def execute(
        self, date_from: str | None, page: int, page_size: int
    ) -> tuple[list[Event], int]:
        events = await self.event_repo.list_filtered(date_from, page, page_size)
        count = await self.event_repo.count_filtered(date_from)
        return events, count


class GetEventUseCase:
    """Use case для получения деталей события."""

    def __init__(self, event_repo: IEventRepository):
        self.event_repo = event_repo

    async def execute(self, event_id: str) -> Event:
        event = await self.event_repo.get(event_id)
        if not event:
            raise EventNotFoundError()
        return event


class GetSeatsUseCase:
    """Use case для получения свободных мест события."""

    def __init__(
        self,
        event_repo: IEventRepository,
        client: IEventsProviderClient,
    ):
        self.event_repo = event_repo
        self.client = client

    async def execute(self, event_id: str) -> list[str]:
        event = await self.event_repo.get(event_id)
        if not event:
            raise EventNotFoundError()
        if event.status != EventStatus.PUBLISHED:
            raise EventNotPublishedError()
        return await self.client.get_seats(event_id)
