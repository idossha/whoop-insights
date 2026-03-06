.PHONY: help install auth sync sync-full dashboard docker-build docker-pull docker-up docker-down docker-logs docker-sync docker-auth docker-reauth docker-status docker-shell clean setup

help:
	@echo "Whoop Sync - Commands:"
	@echo ""
	@echo "Docker Operations:"
	@echo "  make docker-pull   - Pull latest image from Docker Hub"
	@echo "  make docker-build  - Build Docker image locally"
	@echo "  make docker-up     - Start all Docker services"
	@echo "  make docker-down   - Stop all Docker services"
	@echo "  make docker-logs   - View Docker logs (follow mode)"
	@echo "  make docker-shell  - Open shell in dashboard container"
	@echo ""
	@echo "Authentication (in container):"
	@echo "  make docker-auth   - Start authentication flow"
	@echo "  make docker-reauth - Re-authenticate (clear old tokens)"
	@echo "  make docker-status - Check authentication status"
	@echo ""
	@echo "Sync (in container):"
	@echo "  make docker-sync   - Sync data once"
	@echo "  make docker-sync-full - Full historical sync"
	@echo ""
	@echo "Local Development:"
	@echo "  make install       - Install Python deps locally"
	@echo "  make auth          - Authenticate with Whoop (local)"
	@echo "  make sync          - Sync data (local)"
	@echo "  make sync-full     - Full historical sync (local)"
	@echo "  make dashboard     - Run Streamlit dashboard (local)"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean         - Remove generated files"
	@echo "  make docker-clean  - Remove Docker volumes (WARNING: deletes data)"

setup:
	./scripts/setup.sh

install:
	pip install -r requirements.txt

auth:
	python main.py auth

sync:
	python main.py sync

sync-full:
	python main.py sync --full

dashboard:
	streamlit run dashboard/dashboard.py

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

clean:
	rm -rf __pycache__ src/whoop_sync/__pycache__ *.pyc
