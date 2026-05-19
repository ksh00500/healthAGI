.PHONY: help up up-storage up-ollama up-all down logs api db-shell migrate revision test lint mobile

help:
	@echo "Targets:"
	@echo "  up           - postgres only (default — Gemini API + local fs storage)"
	@echo "  up-storage   - postgres + minio (when HEALTHAGI_STORAGE_BACKEND=minio)"
	@echo "  up-ollama    - postgres + ollama (when HEALTHAGI_LLM_BACKEND=ollama)"
	@echo "  up-all       - postgres + minio + ollama"
	@echo "  down         - docker compose down"
	@echo "  logs         - tail compose logs"
	@echo "  api          - run uvicorn dev server on host"
	@echo "  db-shell     - psql into postgres"
	@echo "  migrate      - alembic upgrade head"
	@echo "  revision m=msg - alembic autogenerate revision"
	@echo "  test         - run backend pytest"
	@echo "  lint         - ruff + mypy on backend, tsc on mobile"
	@echo "  mobile       - expo start (mobile dev server)"

up:
	docker compose up -d postgres

up-storage:
	docker compose --profile storage up -d postgres minio

up-ollama:
	docker compose --profile ollama up -d postgres ollama

up-all:
	docker compose --profile storage --profile ollama up -d postgres minio ollama

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
