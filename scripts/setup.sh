#!/bin/bash
set -e

echo "=== Whoop Dashboard Setup ==="
echo ""

# Check .env
if [ ! -f .env ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    echo ""
    echo "ERROR: Edit .env with your Whoop API credentials"
    echo "Get credentials at: https://developer-dashboard.whoop.com/"
    echo "Redirect URI: http://localhost:8080/callback"
    echo ""
    echo "Then run: ./scripts/setup.sh"
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "Docker installed. Log out and back in, then run this script again."
    exit 0
fi

# Build and start
echo "Building and starting services..."
docker compose build
docker compose up -d

echo ""
echo "Waiting for services (10s)..."
sleep 10

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Services running:"
echo "  Dashboard:  http://localhost:8501"
echo ""
echo "Next steps:"
echo "  1. Authenticate: docker compose exec dashboard python main.py auth"
echo "  2. Sync data:    docker compose exec dashboard python main.py sync"
echo ""
echo "Useful commands:"
echo "  Logs:   docker compose logs -f"
echo "  Stop:   docker compose down"
echo "  Update: docker compose pull && docker compose up -d"
