from sqlalchemy.ext.asyncio import AsyncSession

from src.clients import EventsProviderClient
from src.repositories import EventRepository, TicketRepository
from src.usecases import CancelTicketUseCase, CreateTicketUseCase


class TicketsNotFoundError(Exception):
    pass


class TicketsService:
    """Сервис для работы с билетами."""

    def __init__(
        self,
        session: AsyncSession,
        client: EventsProviderClient,
    ):
        self.session = session
        self.client = client
        self.event_repo = EventRepository(session)
        self.ticket_repo = TicketRepository(session)

    async def create_ticket(
        self,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> str:
        usecase = CreateTicketUseCase(self.client, self.event_repo, self.ticket_repo)
        ticket_id = await usecase.execute(event_id, first_name, last_name, email, seat)
        await self.session.commit()
        return ticket_id

    async def cancel_ticket(self, ticket_id: str) -> bool:
        ticket = await self.ticket_repo.get(ticket_id)
        if not ticket:
            raise TicketsNotFoundError()
        event_id = str(ticket.event_id)
        usecase = CancelTicketUseCase(self.client, self.ticket_repo, self.event_repo)
        await usecase.execute(ticket_id, event_id)
        await self.session.commit()
        return True
