# Observability Lab — common tasks.  `make help`
SHELL := /bin/bash
ENV   ?= kind
TF    := terraform -chdir=terraform/envs/$(ENV)
KUST  := gitops/apps/demo-shop/base/kustomization.yaml
DEMO_IMAGE := $(shell awk '/- name: .*demo-shop/{print $$3}' $(KUST)):$(shell awk '/newTag:/{print $$2}' $(KUST))

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ----------------------------------------------------------------- lifecycle --
.PHONY: up down
up: ## Create cluster + bootstrap GitOps (ENV=kind|eks|gke)
	$(TF) init -input=false
	$(TF) apply -input=false
	@if [ "$(ENV)" = "kind" ]; then $(MAKE) demo-image; fi
	@$(TF) output -raw next_steps 2>/dev/null || true

down: ## Destroy the environment
	$(TF) destroy

.PHONY: demo-image
demo-image: ## Build the demo app and load it into kind (no registry needed)
	docker build -t $(DEMO_IMAGE) apps/demo-shop
	kind load docker-image $(DEMO_IMAGE) --name observability

# ---------------------------------------------------------------------- access --
.PHONY: ui grafana-password argocd-password keycloak-password sso-users sso-test lab-ca status
ui: ## Port-forward Prometheus, Alertmanager, OpenCost, demo (+ Grafana/Argo CD fallback)
	@scripts/port-forward.sh

grafana-password: ## Print the Grafana admin password
	@kubectl -n observability get secret grafana-admin -o jsonpath='{.data.admin-password}' | base64 -d; echo

argocd-password: ## Print the initial Argo CD admin password
	@kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo

keycloak-password: ## Print the Keycloak admin console password (user: admin)
	@kubectl -n keycloak get secret keycloak-secrets -o jsonpath='{.data.KC_BOOTSTRAP_ADMIN_PASSWORD}' | base64 -d; echo

sso-users: ## Print the demo SSO users (kind)
	@echo "alice → sre-team     (Grafana Admin,  Argo CD admin)"
	@echo "bob   → stakeholders (Grafana Viewer, Argo CD read-only)"
	@printf "password: "; kubectl -n keycloak get secret keycloak-secrets -o jsonpath='{.data.DEMO_USER_PASSWORD}' | base64 -d; echo

sso-test: ## Log in to Grafana + Argo CD through Keycloak and check roles
	@scripts/sso-smoke-test.sh

lab-ca: ## Export the kind lab CA to lab-ca.crt (trust it to silence browser warnings)
	@kubectl -n cert-manager get secret platform-issuer-ca -o jsonpath='{.data.ca\.crt}' | base64 -d > lab-ca.crt
	@echo "Wrote lab-ca.crt. macOS: sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain lab-ca.crt"

status: ## Argo CD application sync/health
	@kubectl -n argocd get applications -o custom-columns=APP:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status,WAVE:.metadata.annotations.argocd\.argoproj\.io/sync-wave

# ------------------------------------------------------------------ validation --
.PHONY: render validate test dashboards
render: ## Render every Application for ENV into build/ENV
	python3 scripts/render.py $(ENV) --strict

dashboards: ## Regenerate Grafana dashboards JSON
	python3 scripts/generate-dashboards.py

test: ## Lint + unit-test the demo app
	cd apps/demo-shop && ruff check . && pytest -q

validate: ## Quick local checks: terraform fmt + render all 4 envs
	terraform fmt -check -recursive terraform
	for e in kind eks gke existing; do python3 scripts/render.py $$e --strict || exit 1; done
	@echo "CI additionally runs kubeconform, otelcol validate, promtool and amtool (gitops-validate.yaml)."

# ------------------------------------------------------------------- game days --
.PHONY: chaos-errors chaos-latency chaos-reset
chaos-errors: ## Inject 20% payment errors (fires SLO burn-rate alerts)
	scripts/chaos.sh errors 0.2
chaos-latency: ## Add 800ms latency to orders
	scripts/chaos.sh latency 800
chaos-reset: ## Remove all injected faults
	scripts/chaos.sh reset
