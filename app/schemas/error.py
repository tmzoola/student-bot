from typing import Optional

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    status_code: int
    error: str
    detail: Optional[str] = None


class FieldError(BaseModel):
    field: str
    message: str


class ValidationErrorResponse(BaseModel):
    status_code: int
    error: str
    detail: list[FieldError]
