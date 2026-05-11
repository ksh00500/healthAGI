.PHONY: help up down logs api db-shell migrate revision test lint mobile

help:
	@echo "Targets:"
	@echo "  up         - docker compose up -d (postgres, minio, ollama)"
	@echo "  down       - docker compose down"
	@echo "  logs       - tail compose logs"
	@echo "  api        - run uvicorn dev server on host"
	@echo "  db-shell   - psql into postgres"
	@echo "  migrate    - alembic upgrade head"
	@echo "  revision m=msg - alembic autogenerate revision"
	@echo "  test       - run backend pytest"
	@echo "  lint       - ruff + mypy on backend, tsc on mobile"
	@echo "  mobile     - expo start (mobile dev server)"

up:
	docker compose up -d postgres minio ollama

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

api:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

db-shell:
	docker compose exec postgres psql -U $${POSTGRES_USER:-healthagi} -d $${POSTGRES_DB:-healthagi}

migrate:
	cd backend && alembic upgrade head

revision:
	cd backend && alembic revision --autogenerate -m "$(m)"

test:
	cd backend && pytest -q

lint:
	cd backend && ruff check . && mypy app
	cd mobile && pnpm tsc --noEmit

mobile:
	cd mobile && pnpm start
