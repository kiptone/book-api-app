import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PlaceSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    city: str
    address: str
    seats_pattern: str


class EventDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    place: PlaceSchema
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int


class EventListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    place: PlaceSchema
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int


class EventListResponse(BaseModel):
    count: int
    next: str | None
    previous: str | None
    results: list[EventListItem]


class SeatsResponse(BaseModel):
    event_id: str
    available_seats: list[str]


class TicketCreateRequest(BaseModel):
    event_id: str
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    email: EmailStr
    seat: str


class TicketCancelRequest(BaseModel):
    event_id: str
    ticket_id: str


class TicketResponse(BaseModel):
    ticket_id: str


class SuccessResponse(BaseModel):
    success: bool = True
