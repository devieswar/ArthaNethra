# ArthaNethra - Development Makefile

.PHONY: help install-backend install-frontend lint-backend lint-frontend lint format-backend format-frontend format test-backend test-frontend test docker-up docker-down clean

help:
	@echo "ArthaNethra Development Commands"
	@echo "================================="
	@echo "setup            - Install all dependencies"
	@echo "lint             - Run all linters"
	@echo "format           - Format all code"
	@echo "test             - Run all tests"
	@echo "docker-up        - Start Docker services"
	@echo "docker-down      - Stop Docker services"
	@echo "clean            - Clean generated files"

# Setup
setup: install-backend install-frontend

install-backend:
	@echo "Installing backend dependencies with uv..."
	cd backend && uv sync

install-backend-pip:
	@echo "Installing backend dependencies with pip (fallback)..."
	cd backend && pip install -r requirements.txt

install-frontend:
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

# Linting
lint: lint-backend lint-frontend

lint-backend:
	@echo "Linting backend with ruff..."
	cd backend && ruff check .

lint-frontend:
	@echo "Linting frontend with eslint..."
	cd frontend && npm run lint

# Formatting
format: format-backend format-frontend

format-backend:
	@echo "Formatting backend with ruff..."
	cd backend && ruff format .
	cd backend && ruff check --fix .

format-frontend:
	@echo "Formatting frontend with prettier..."
	cd frontend && npx prettier --write "src/**/*.{ts,html,scss}"

# Testing
test: test-backend test-frontend

test-backend:
	@echo "Running backend tests..."
	cd backend && pytest

test-frontend:
	@echo "Running frontend tests..."
	cd frontend && npm test

# Docker
docker-up:
	@echo "Starting Docker services..."
	docker compose up -d

docker-down:
	@echo "Stopping Docker services..."
	docker compose down

docker-logs:
	docker compose logs -f

# Clean
clean:
	@echo "Cleaning generated files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	cd frontend && rm -rf node_modules dist .angular 2>/dev/null || true
	@echo "Clean complete!"

# Development
dev-backend:
	cd backend && uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

dev-backend-pip:
	cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && ng serve --host 0.0.0.0 --port 4200

# Quick start
start: docker-up dev-backend dev-frontend

# UV specific commands
uv-init:
	@echo "Initializing uv environment..."
	cd backend && uv venv
	cd backend && uv sync

uv-add:
	@echo "Add a package: make uv-add PACKAGE=package-name"
	cd backend && uv add $(PACKAGE)

uv-update:
	@echo "Updating all dependencies..."
	cd backend && uv lock --upgrade

