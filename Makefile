# Billo · one-command helpers. Run from the repo root (this folder).
UV ?= uv
PYTHON_VERSION ?= 3.11
VENV := .venv
BIN := $(VENV)/bin

.PHONY: setup env addresses db prices core fetch-ai agents photon frontend dev test test-backend test-frontend stop

setup:            ## create the Python venv + install everything (Python and Node)
	$(UV) venv --allow-existing --seed --python $(PYTHON_VERSION) $(VENV)
	$(BIN)/pip install -U pip
	$(BIN)/pip install -r backend/fetch.ai/requirements.txt -r backend/api/requirements.txt
	cd backend/photon && npm install
	cd frontend && npm install

env:              ## make your .env from the example (never commit .env)
	@test -f .env || cp .env.example .env
	@echo "Now edit .env: seeds, ASI_ONE_API_KEY, DATABASE_URL, SPECTRUM_*, SENTRY_DSN ..."

addresses:        ## print every agent address from its seed (paste into .env)
	cd backend/fetch.ai && ../../$(BIN)/python ../scripts/print_addresses.py

db:               ## create tables, hypertables and continuous aggregates in Tiger Data
	$(BIN)/python backend/scripts/apply_schema.py

prices:           ## load the price CSV (synthetic by default) into Tiger Data
	$(BIN)/python backend/scripts/load_prices.py $(FILE)

core:             ## Core API on :8000  (docs at /docs)
	cd backend/api && ../../$(BIN)/uvicorn app.main:app --reload --port 8000

fetch-ai:         ## all Billo Fetch.ai agents in the background (logs in .logs/)
	@mkdir -p .logs
	@for a in red_flag care_finder bill_auditor settlement_router imessage_gateway case_medic coordinator; do \
	  (cd backend/fetch.ai && ../../$(BIN)/python $$a.py > ../../.logs/$$a.log 2>&1 &) ; echo "started $$a"; done
	@echo "tail -f .logs/coordinator.log"

photon:           ## Photon iMessage bridge on :3000
	cd backend/photon && npm run dev

bridge: photon    ## compatibility alias

frontend:         ## Next.js frontend on :3001
	cd frontend && npm run dev -- --port 3001

agents: fetch-ai  ## compatibility alias

dev: fetch-ai     ## Core + Fetch.ai + Photon + frontend
	@(cd backend/photon && npm run dev > ../../.logs/bridge.log 2>&1 &)
	@(cd frontend && npm run dev -- --port 3001 > ../.logs/frontend.log 2>&1 &)
	$(MAKE) core

test: test-backend test-frontend ## unit tests (no keys, no database)

test-backend:
	$(BIN)/python -m pytest -q tests/backend
	cd backend/photon && npm test && npm run typecheck

test-frontend:
	cd frontend && npm test && npm run build

stop:             ## stop everything started by make fetch-ai / dev
	-pkill -f "python (red_flag|care_finder|bill_auditor|settlement_router|imessage_gateway|case_medic|coordinator).py"
	-pkill -f "tsx watch src/main.ts"
	-pkill -f "uvicorn app.main:app"
