"""
FastAPI application entrypoint: middleware (request_id), exception
handlers (standard error envelope), routers, OpenAPI metadata.
"""
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import cors_origin_list, get_settings
from app.core.exceptions import AppError, app_error_handler, unhandled_exception_handler
from app.core.logging import configure_logging

settings = get_settings()
configure_logging()

app = FastAPI(
    title="SIH26137 - Quantum-Inspired Intelligent Traffic Route Optimization Platform",
    description=(
        "Enterprise decision-support backend for multi-vehicle, congestion-aware route "
        "optimization using a Quantum-behaved PSO engine, with classical-algorithm "
        "benchmarking, reproducible seeded experiments, and full provenance tracking."
    ),
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

_cors_origins = cors_origin_list(settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    # Credentialed CORS + wildcard origin is invalid per the CORS spec, so
    # only allow credentials when specific origins are configured.
    allow_credentials=_cors_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
async def root():
    return {"service": "SIH26137 backend", "docs": "/docs"}
