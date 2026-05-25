.PHONY: setup up down migrate logs clean build

setup: ## Copy .env templates (safe — will not overwrite existing files)
	@cp -n .env.example .env 2>/dev/null && echo "Created .env — edit it with your POSTGRES_PASSWORD and DISCOGS_TOKEN" || echo ".env already exists"
	@cp -n apps/local-api/.env.example apps/local-api/.env 2>/dev/null && echo "Created apps/local-api/.env" || echo "apps/local-api/.env already exists"

build: ## Build all Docker images
	docker compose build

up: ## Start all services (postgres, api, react)
	docker compose up -d
	@echo "Services starting..."
	@echo "  React UI:  http://localhost"
	@echo "  API:       http://localhost:3001"
	@echo "  Health:    http://localhost/health"

down: ## Stop all services
	docker compose down

migrate: ## Run database migrations (requires services to be up)
	docker compose exec api npm run migrate

logs: ## Tail logs from all services
	docker compose logs -f

clean: ## Stop services and remove all volumes (DELETES DATA)
	docker compose down -v

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
