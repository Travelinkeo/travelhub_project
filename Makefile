.PHONY: help test lint format security docker-build docker-test clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

test: ## Run tests with coverage
	pytest tests/ --cov=. --cov-report=term-missing -v --create-db

lint: ## Run linters (ruff, black, isort)
	ruff check . --select E9,F63,F7,F82
	ruff check . --max-complexity=10 --line-length=127 || true
	black --check . || true
	isort --check-only . || true

format: ## Format code with black and isort
	black .
	isort .

security: ## Run security checks
	python manage.py check --deploy
	safety check --json || true
	bandit -r . -ll -ii -x tests/ || true

docker-build: ## Build Docker image
	docker build -t travelhub:local .

docker-test: ## Run tests in Docker
	docker-compose -f docker-compose.test.yml up --abort-on-container-exit --exit-code-from web

clean: ## Clean up cache and build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache .coverage htmlcov dist build

migrate: ## Run migrations
	python manage.py migrate --noinput

makemigrations: ## Create new migrations
	python manage.py makemigrations

check: ## Run Django system check
	python manage.py check
