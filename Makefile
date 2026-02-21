.PHONY: help install auth sync sync-full dashboard docker-build docker-up docker-down docker-logs docker-sync clean setup

help:
	@echo "Commands:"
	@echo "  make setup      - Full Docker setup (first time)"
	@echo "  make install    - Install Python deps"
	@echo "  make auth       - Authenticate with Whoop"
	@echo "  make sync       - Sync data"
	@echo "  make sync-full  - Full historical sync"
	@echo "  make dashboard  - Run Streamlit dashboard"
	@echo "  make docker-up  - Start Docker services"
	@echo "  make docker-down- Stop Docker services"
	@echo "  make docker-logs- View Docker logs"
	@echo "  make clean      - Remove generated files"

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

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-sync:
	docker compose exec dashboard python main.py sync

clean:
	rm -rf __pycache__ src/whoop_sync/__pycache__ *.pyc
