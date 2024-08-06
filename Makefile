export DOCKER_BUILDKIT=1
VERSION = $(strip $(shell poetry version --short))

.PHONY: help
help: ## Display this help message
	@echo "Usage: make <target>"
	@echo
	@echo "Available targets:"
	@grep --extended-regexp --no-filename '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "	%-20s%s\n", $$1, $$2}'

PHONY: build
build: ## Build all Docker images
	docker build --tag=camptocamp/tilecloud-chain-tests --target=tests .
	docker build --tag=camptocamp/tilecloud-chain --build-arg=VERSION=$(VERSION) .

PHONY: checks
checks: prospector ## Run the checks

PHONY: prospector
prospector: ## Run Prospector
	docker run --rm --volume=${PWD}:/app camptocamp/tilecloud-chain-tests prospector --output-format=pylint --die-on-tool-error

PHONY: tests
tests: build ## Run the unit tests
	docker compose stop --timeout=0
	docker compose down || true
	C2C_AUTH_GITHUB_CLIENT_ID=$(shell gopass show gs/projects/github/oauth-apps/geoservices-int/client-id) \
	C2C_AUTH_GITHUB_CLIENT_SECRET=$(shell gopass show gs/projects/github/oauth-apps/geoservices-int/client-secret) \
	docker compose up -d

	# Wait for DB to be up
	while ! docker compose exec -T test psql -h db -p 5432 -U postgres -v ON_ERROR_STOP=1 -c "SELECT 1" -d tests; \
	do \
		echo "Waiting for DB to be UP"; \
		sleep 1; \
	done

	c2cciutils-docker-logs

	docker compose exec -T test pytest -vv --color=yes

	c2cciutils-docker-logs
	docker compose down

PHONY: tests-fast
tests-fast:
	C2C_AUTH_GITHUB_CLIENT_ID=$(shell gopass show gs/projects/github/oauth-apps/geoservices-int/client-id) \
	C2C_AUTH_GITHUB_CLIENT_SECRET=$(shell gopass show gs/projects/github/oauth-apps/geoservices-int/client-secret) \
	docker compose up -d

	# Wait for DB to be up
	while ! docker compose exec -T test psql -h db -p 5432 -U postgres -v ON_ERROR_STOP=1 -c "SELECT 1" -d tests; \
	do \
		echo "Waiting for DB to be UP"; \
		sleep 1; \
	done

	docker compose exec -T test pytest -vv --color=yes --exitfirst #--last-failed
