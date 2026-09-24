"""
Standard application exceptions and the global error envelope handler.

Every API error follows:
{
  "code": "...",
  "message": "...",
  "details": {},
  "request_id": "uuid"
}
Stack traces are never exposed to clients; they are logged internally.
"""
from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Base class for all domain/application errors."""

    code: str = "INTERNAL_ERROR"
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None, details: dict[str, Any] | None = None):
        self.message = message or self.message
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Resource not found."


class ValidationAppError(AppError):
    code = "VALIDATION_ERROR"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = "Validation failed."


class ConflictError(AppError):
    code = "CONFLICT"
    status_code = status.HTTP_409_CONFLICT
    message = "Resource conflict."


class UnauthorizedError(AppError):
    code = "UNAUTHORIZED"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Authentication required."


class ForbiddenError(AppError):
    code = "FORBIDDEN"
    status_code = status.HTTP_403_FORBIDDEN
    message = "You do not have permission to perform this action."


class TenantIsolationError(ForbiddenError):
    code = "TENANT_ISOLATION_VIOLATION"
    message = "Cross-organization access is not permitted."


class OptimizationJobNotFoundError(NotFoundError):
    code = "OPTIMIZATION_JOB_NOT_FOUND"
    message = "Optimization job was not found."


class InfeasibleProblemError(ValidationAppError):
    code = "INFEASIBLE_OPTIMIZATION_PROBLEM"
    message = "The optimization problem is infeasible with the given inputs."


class CustomerGraphMappingError(ValidationAppError):
    code = "CUSTOMER_GRAPH_MAPPING_FAILED"
    message = "Customer location could not be mapped to the road graph."


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "app_error",
        code=exc.code,
        message=exc.message,
        details=exc.details,
        request_id=request_id,
        path=str(request.url),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
            "request_id": request_id,
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception("unhandled_exception", request_id=request_id, path=str(request.url))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred.",
            "details": {},
            "request_id": request_id,
        },
    )
