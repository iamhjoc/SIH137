"""
Convenience script: seeds the DB (if empty) and immediately triggers the
sample optimization job synchronously (without Celery) for a quick local demo.
"""

from app.optimization.qpso import QPSOConfig, QPSOEngine
from app.services.optimization_service import build_problem_from_job, load_job_sync


def run_demo(job_id: str):
    job = load_job_sync(job_id)
    problem = build_problem_from_job(job)
    engine = QPSOEngine(QPSOConfig(**job.algorithm_config))
    result = engine.optimize(problem)
    print(f"Best cost: {result.best_cost}")
    print(f"Routes: {len(result.routes)}")
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m app.seed.demo_scenario <optimization_job_id>")
    else:
        run_demo(sys.argv[1])
