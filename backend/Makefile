.PHONY: up down migrate seed test
up:
	docker compose up --build
down:
	docker compose down
migrate:
	docker compose exec api alembic upgrade head
seed:
	docker compose exec api python -m app.seed.dummy_data
test:
	pytest tests/unit
