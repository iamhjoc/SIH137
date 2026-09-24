from uuid import UUID

from pydantic import BaseModel, Field
from datetime import datetime


class ObjectiveWeights(BaseModel):
    distance: float = 0.25
    time: float = 0.40
    congestion: float = 0.25
    late: float = 0.10
    vehicle: float = 0.0
    constraint: float = 1.0


class AlgorithmConfig(BaseModel):
    particles: int = 40
    iterations: int = 500
    beta_start: float = 1.0
    beta_end: float = 0.5
    # These three were silently dropped by Pydantic (extra fields are
    # ignored by default) even though the frontend's optimization form
    # sends them and QPSOConfig (app/optimization/qpso.py) already
    # supports all three -- so time budget, target cost and convergence
    # threshold had no effect on a run.
    time_budget_s: float | None = None
    target_cost: float | None = None
    convergence_threshold: float | None = None


class OptimizationConstraints(BaseModel):
    capacity: bool = True
    visit_once: bool = True
    return_to_depot: bool = True


class OptimizationJobCreate(BaseModel):
    project_id: UUID
    graph_version_id: UUID
    traffic_scenario_id: UUID | None = None
    algorithm: str = Field("qpso", examples=["qpso", "ga", "aco", "pso", "dijkstra", "astar"])
    seed: int = 20260909
    objective_weights: ObjectiveWeights = Field(default_factory=ObjectiveWeights)
    algorithm_config: AlgorithmConfig = Field(default_factory=AlgorithmConfig)
    constraints: OptimizationConstraints = Field(default_factory=OptimizationConstraints)


class OptimizationJobResponse(BaseModel):
    id: UUID
    project_id: UUID
    status: str
    algorithm: str
    algorithm_version: str
    seed: int
    best_cost: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OptimizationProgressResponse(BaseModel):
    job_id: UUID
    status: str
    progress: float
    iteration: int
    total_iterations: int
    best_cost: float | None
    elapsed_ms: int
