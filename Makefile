.PHONY: help docker-build docker-pull docker-up docker-down docker-logs docker-sync docker-auth docker-reauth docker-status docker-shell docker-clean clean

help:
	@echo "Whoop Sync - Commands:"
	@echo ""
	@echo "Docker Operations:"
	@echo "  make docker-pull   - Pull latest image from Docker Hub"
	@echo "  make docker-up     - Start all Docker services"
	@echo "  make docker-down   - Stop all Docker services"
	@echo "  make docker-logs   - View dashboard logs"
	@echo "  make docker-shell  - Open shell in container"
	@echo "  make docker-clean  - Remove containers and volumes"
	@echo ""
	@echo "Authentication:"
	@echo "  make docker-auth   - Start authentication flow"
	@echo "  make docker-reauth - Re-authenticate (clear old tokens)"
	@echo "  make docker-status - Check authentication status"
	@echo ""
	@echo "Data Sync:"
	@echo "  make docker-sync   - Sync data once"
	@echo "  make docker-sync-full - Full historical sync"
	@echo ""
	@echo "Development:"
	@echo "  make docker-build  - Build Docker image locally"

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
