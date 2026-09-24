from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict = Field(default_factory=dict)
    request_id: str


class PaginatedResponse(BaseModel):
    items: list
    next_cursor: str | None = None
