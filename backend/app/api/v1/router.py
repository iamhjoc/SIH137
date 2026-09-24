from fastapi import APIRouter

from app.api.v1.endpoints import (
    benchmarks,
    customers,
    depots,
    directions,
    graphs,
    health,
    optimization_jobs,
    projects,
    traffic,
    vehicles,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(projects.router)
api_router.include_router(depots.router)
api_router.include_router(customers.router)
api_router.include_router(vehicles.router)
api_router.include_router(graphs.router)
api_router.include_router(traffic.router)
api_router.include_router(optimization_jobs.router)
api_router.include_router(benchmarks.router)
api_router.include_router(directions.router)
