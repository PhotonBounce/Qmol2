# ComputeSwarm — Developer Makefile
# Works on Linux/macOS (Git Bash/WSL for Windows)

.PHONY: setup setup-win dev up down logs test test-smoke test-e2e test-integration migrate shell-api clean build-jobs lint format seed

# ------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------
setup:
	bash scripts/setup.sh

setup-win:
	@powershell -ExecutionPolicy RemoteSigned -File scripts\setup.ps1

# ------------------------------------------------------------------
# Development helpers
# ------------------------------------------------------------------
dev:
	bash scripts/dev-start.sh

dev-win:
	@powershell -ExecutionPolicy RemoteSigned -File scripts\dev-start.ps1

# ------------------------------------------------------------------
# Docker Compose shortcuts
# ------------------------------------------------------------------
up:
	@if command -v docker-compose >/dev/null 2>&1; then \
		docker-compose up -d; \
	else \
		docker compose up -d; \
	fi

down:
	@if command -v docker-compose >/dev/null 2>&1; then \
		docker-compose down; \
	else \
		docker compose down; \
	fi

logs:
	@if command -v docker-compose >/dev/null 2>&1; then \
		docker-compose logs -f; \
	else \
		docker compose logs -f; \
	fi

# ------------------------------------------------------------------
# Testing
# ------------------------------------------------------------------
test: test-integration

test-smoke:
	python scripts/test-smoke.py

test-e2e:
	python scripts/test-e2e.py

test-integration:
	python scripts/test-integration.py

# ------------------------------------------------------------------
# Database
# ------------------------------------------------------------------
migrate:
	@if command -v docker-compose >/dev/null 2>&1; then \
		docker-compose exec api sh -c "cd /app && alembic upgrade head"; \
	else \
		docker compose exec api sh -c "cd /app && alembic upgrade head"; \
	fi

shell-api:
	@if command -v docker-compose >/dev/null 2>&1; then \
		docker-compose exec api bash; \
	else \
		docker compose exec api bash; \
	fi

seed:
	@if command -v docker-compose >/dev/null 2>&1; then \
		docker-compose exec api sh -c "cd /app && python scripts/seed.py"; \
	else \
		docker compose exec api sh -c "cd /app && python scripts/seed.py"; \
	fi

# ------------------------------------------------------------------
# Cleanup
# ------------------------------------------------------------------
clean:
	@if command -v docker-compose >/dev/null 2>&1; then \
		docker-compose down -v --rmi local; \
	else \
		docker compose down -v --rmi local; \
	fi

# ------------------------------------------------------------------
# Docker job images
# ------------------------------------------------------------------
build-jobs:
	@echo "Building docker-jobs base image ..."
	@docker build -t computeswarm/base:latest docker-jobs/base/
	@echo "Building docker-jobs example images ..."
	@docker build -t computeswarm/physics-sim:latest docker-jobs/examples/physics-sim/
	@docker build -t computeswarm/blender-render:latest docker-jobs/examples/blender-render/
	@docker build -t computeswarm/molecular-dock:latest docker-jobs/examples/molecular-dock/
	@echo "Done."

# ------------------------------------------------------------------
# Linting / Formatting (placeholders)
# ------------------------------------------------------------------
lint:
	@echo "Linting not yet configured."
	@echo "  Python: pip install black flake8 && black --check backend worker"
	@echo "  JS:     cd dashboard && npm run lint"

format:
	@echo "Formatting not yet configured."
	@echo "  Python: pip install black && black backend worker"
	@echo "  JS:     cd dashboard && npm run format"
