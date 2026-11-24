# Developer tasks for the SAPS backend (Developer Guide §10).

.PHONY: fixtures
fixtures: ## Render the dummy sample set, manifest and schema from the JSON results (SAPS-18)
	uv run python tools/generate_fixtures.py

.PHONY: keycloak-realm
keycloak-realm: ## Generate the Keycloak realm file from fixtures/companies.json (SAPS-43)
	uv run python tools/generate_keycloak_realm.py
