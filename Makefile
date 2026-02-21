.PHONY: help install auth sync sync-full dashboard docker-build docker-pull docker-up docker-down docker-logs docker-sync docker-auth docker-reauth docker-status docker-shell docker-clean clean setup venv-setup venv-auth venv-sync venv-sync-full venv-dashboard venv-status venv-reauth

help:
	@echo "Whoop Sync - Commands:"
	@echo ""
	@echo "=== Docker (64-bit OS only) ==="
	@echo "  make docker-pull   - Pull latest image from Docker Hub"
	@echo "  make docker-up     - Start all Docker services"
	@echo "  make docker-down   - Stop all Docker services"
	@echo "  make docker-logs   - View dashboard logs"
	@echo "  make docker-shell  - Open shell in container"
	@echo "  make docker-auth   - Start authentication flow"
	@echo "  make docker-sync   - Sync data once"
	@echo ""
	@echo "=== Local/venv (32-bit or 64-bit) ==="
	@echo "  make venv-setup    - Create virtual environment"
	@echo "  make venv-dashboard- Run dashboard locally"
	@echo "  make venv-auth     - Authenticate locally"
	@echo "  make venv-sync     - Sync data locally"
	@echo ""
	@echo "=== Development ==="
	@echo "  make docker-build  - Build Docker image locally"
	@echo "  make install       - Install Python deps in venv"
	@echo "  make clean         - Remove generated files"

# Docker commands (64-bit OS only)
docker-pull:
	docker pull idossha/whoop-sync:latest

docker-build:
	docker build --no-cache -t idossha/whoop-sync:latest .

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f dashboard

docker-shell:
	docker exec -it whoop-dashboard /bin/bash

docker-auth:
	docker exec -it whoop-dashboard python main.py auth

docker-reauth:
	docker exec -it whoop-dashboard python main.py reauth

docker-status:
	docker exec whoop-dashboard python main.py status

docker-sync:
	docker exec whoop-dashboard python main.py sync

docker-sync-full:
	docker exec whoop-dashboard python main.py sync --full

docker-clean:
	docker compose down -v

# Local/venv commands (32-bit or 64-bit)
venv-setup:
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt

install:
	./venv/bin/pip install -r requirements.txt

auth:
	./venv/bin/python main.py auth

reauth:
	./venv/bin/python main.py reauth

status:
	./venv/bin/python main.py status

sync:
	./venv/bin/python main.py sync

sync-full:
	./venv/bin/python main.py sync --full

dashboard:
	./venv/bin/streamlit run dashboard/dashboard.py

# Aliases for venv
venv-auth: auth
venv-reauth: reauth
venv-status: status
venv-sync: sync
venv-sync-full: sync-full
venv-dashboard: dashboard

clean:
	rm -rf __pycache__ src/whoop_sync/__pycache__ *.pyc
