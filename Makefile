export DOCKER_BUILDKIT=1

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
	docker build --tag=camptocamp/tilecloud-chain .

PHONY: checks
checks: prospector ## Run the checks

PHONY: prospector
prospector: ## Run Prospector
	docker run --rm --volume=${PWD}:/app camptocamp/tilecloud-chain-tests prospector --output-format=pylint --die-on-tool-error

PHONY: tests
tests: build ## Run the unit tests
	docker-compose stop --timeout=0
	docker-compose down || true
	docker-compose up -d

	# Wait for DB to be up
	while ! docker-compose exec -T test psql -h db -p 5432 -U postgres -v ON_ERROR_STOP=1 -c "SELECT 1" -d tests; \
	do \
		echo "Waiting for DB to be UP"; \
		sleep 1; \
	done

	c2cciutils-docker-logs

	docker-compose exec -T test pytest -vv

	c2cciutils-docker-logs
	docker-compose down

PHONY: tests-fast
tests-fast:
	docker-compose up -d

	# Wait for DB to be up
	while ! docker-compose exec -T test psql -h db -p 5432 -U postgres -v ON_ERROR_STOP=1 -c "SELECT 1" -d tests; \
	do \
		echo "Waiting for DB to be UP"; \
		sleep 1; \
	done

	docker-compose exec -T test pytest -vv --exitfirst #--last-failed

PHONY: jsonschema
jsonschema: ## Generate the files related to the JSON schema
	jsonschema-gentypes
