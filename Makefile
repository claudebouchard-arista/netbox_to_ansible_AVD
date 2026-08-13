.PHONY: help lint test-unit test-integration test up down seed build clean verify generate

DOCKER_COMPOSE = docker compose -f docker/docker-compose.yml
PYTHONPATH = PYTHONPATH=.
COLLECTIONS_PATH = ANSIBLE_COLLECTIONS_PATH=/home/vscode/.ansible/collections:$(CURDIR)

# Use NETBOX_HOST_PORT=0 to let Docker pick a free port (avoids conflicts in devcontainers)
NETBOX_HOST_PORT ?= 0

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

lint: ## Run linters (flake8 + yamllint)
	flake8 ansible_collections/ tests/
	yamllint -d relaxed ansible_collections/arista/netbox_avd/

test-unit: ## Run unit tests
	$(PYTHONPATH) pytest tests/unit/ -v --cov=ansible_collections.arista.netbox_avd --cov-report=term-missing

test-integration: ## Run integration tests (requires NetBox)
	$(eval NETBOX_PORT := $(shell docker port docker-netbox-1 8080 2>/dev/null | head -1 | cut -d: -f2))
	$(PYTHONPATH) NETBOX_URL=http://localhost:$(NETBOX_PORT) NETBOX_INTEGRATION=1 pytest tests/integration/ -v

test: test-unit ## Run all non-integration tests

up: ## Start NetBox stack
	NETBOX_HOST_PORT=$(NETBOX_HOST_PORT) $(DOCKER_COMPOSE) up -d
	@PORT=$$(docker port docker-netbox-1 8080 2>/dev/null | head -1 | cut -d: -f2); \
	NETBOX_URL="http://localhost:$$PORT" bash docker/wait_for_netbox.sh; \
	echo "NetBox available at http://localhost:$$PORT"

down: ## Stop NetBox stack
	$(DOCKER_COMPOSE) down -v

seed: ## Seed NetBox with test data
	@PORT=$$(docker port docker-netbox-1 8080 2>/dev/null | head -1 | cut -d: -f2); \
	NETBOX_URL="http://localhost:$$PORT" python tests/fixtures/seed_netbox.py

generate: ## Generate sites/dc1 from NetBox (requires NetBox running + seeded)
	@PORT=$$(docker port docker-netbox-1 8080 2>/dev/null | head -1 | cut -d: -f2); \
	if [ -z "$$PORT" ]; then echo "NetBox not running. Run 'make up && make seed' first."; exit 1; fi; \
	echo "=== Generating AVD inventory from NetBox ==="; \
	cd sites/dc1 && NETBOX_URL="http://localhost:$$PORT" $(COLLECTIONS_PATH) ansible-playbook generate.yml; \
	echo "=== Running AVD build ==="; \
	cd sites/dc1/avd_inventory && $(COLLECTIONS_PATH) ansible-playbook build.yml -i inventory.yml; \
	echo "=== Done: sites/dc1/avd_inventory/ ==="

verify: ## Verify generated output matches committed reference (requires NetBox)
	@PORT=$$(docker port docker-netbox-1 8080 2>/dev/null | head -1 | cut -d: -f2); \
	if [ -z "$$PORT" ]; then echo "NetBox not running. Run 'make up && make seed' first."; exit 1; fi; \
	echo "=== Regenerating sites/dc1 from NetBox ==="; \
	cd sites/dc1 && NETBOX_URL="http://localhost:$$PORT" $(COLLECTIONS_PATH) ansible-playbook generate.yml; \
	cd sites/dc1/avd_inventory && $(COLLECTIONS_PATH) ansible-playbook build.yml -i inventory.yml; \
	echo "=== Checking for drift ==="; \
	if git diff --name-only sites/dc1/avd_inventory/ | grep -q .; then \
		echo "FAIL: Generated output differs from committed reference!"; \
		git diff --stat sites/dc1/avd_inventory/; \
		exit 1; \
	fi; \
	echo "PASS: All generated output matches committed reference."

build: ## Build Ansible collection tarball
	cd ansible_collections/arista/netbox_avd && ansible-galaxy collection build --force

clean: ## Remove build artifacts
	rm -f ansible_collections/arista/netbox_avd/*.tar.gz
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
