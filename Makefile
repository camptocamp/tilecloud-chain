export DOCKER_BUILDKIT=1

PHONY: build
build:
	docker build --tag=camptocamp/tilecloud-chain:tests --target=tests .
	docker build --tag=camptocamp/tilecloud-chain .

PHONY: tests
tests: build
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

	docker-compose exec -T test pytest

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

	docker-compose exec -T test pytest --exitfirst #--last-failed

PHONY: jsonschema
jsonschema:
	jsonschema-gentypes
