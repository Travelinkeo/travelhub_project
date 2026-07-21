.PHONY: help test lint format security docker-build docker-test clean migrate makemigrations check shell dbshell start setup requirements

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

test: ## Run tests with coverage
	pytest tests/ --cov=. --cov-report=term-missing -v --create-db

lint: ## Run linters (ruff check with project rules from .ruff.toml)
	ruff check .
	ruff check . --max-complexity=10 --line-length=127

format: ## Format code with ruff (replaces black/isort)
	ruff format .

security: ## Run security checks
	python manage.py check --deploy
	safety check --json
	bandit -r . -ll -ii -x tests/

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

shell: ## Open Django shell_plus (django-extensions)
	python manage.py shell_plus

dbshell: ## Open database shell
	python manage.py dbshell

start: ## Run development server
	python manage.py runserver

setup: ## Install dev dependencies and run migrations
	pip install -r requirements/dev.txt
	python manage.py migrate --noinput
	python manage.py collectstatic --noinput

requirements: ## Install dev dependencies
	pip install -r requirements/dev.txt

e2e: ## Run E2E tests (Playwright) — requires PostgreSQL running
	pytest tests/e2e/ -m e2e -v --tb=short --timeout=120 --nomigrations

e2e-install: ## Install Playwright browsers
	python -m playwright install chromium --with-deps
