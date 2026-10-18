# Billo · one-command helpers. Run from the repo root (this folder).
UV ?= uv
PYTHON_VERSION ?= 3.11
VENV := .venv
BIN := $(VENV)/bin

.PHONY: setup env addresses db prices core agents bridge dev test stop

setup:            ## create the Python venv + install everything (Python and Node)
	$(UV) venv --allow-existing --seed --python $(PYTHON_VERSION) $(VENV)
	$(BIN)/pip install -U pip
	$(BIN)/pip install -r agents/requirements.txt -r core/requirements.txt
	cd bridge && npm install

env:              ## make your .env from the example (never commit .env)
	@test -f .env || cp .env.example .env
	@echo "Now edit .env: seeds, ASI_ONE_API_KEY, DATABASE_URL, SPECTRUM_*, SENTRY_DSN ..."

addresses:        ## print every agent address from its seed (paste into .env)
	cd agents && ../$(BIN)/python ../scripts/print_addresses.py

db:               ## create tables, hypertables and continuous aggregates in Tiger Data
	$(BIN)/python scripts/apply_schema.py

prices:           ## load the price CSV (synthetic by default) into Tiger Data
	$(BIN)/python scripts/load_prices.py $(FILE)

core:             ## Core API on :8000  (docs at /docs)
	cd core && ../$(BIN)/uvicorn app.main:app --reload --port 8000

agents:           ## all Billo agents in the background (logs in .logs/)
	@mkdir -p .logs
	@for a in red_flag care_finder bill_auditor settlement_router imessage_gateway case_medic coordinator; do \
	  (cd agents && ../$(BIN)/python $$a.py > ../.logs/$$a.log 2>&1 &) ; echo "started $$a"; done
	@echo "tail -f .logs/coordinator.log"

bridge:           ## Photon iMessage bridge on :3000
	cd bridge && npm run dev

dev: agents       ## core + agents + bridge (core and bridge in this terminal)
	@(cd bridge && npm run dev > ../.logs/bridge.log 2>&1 &)
	$(MAKE) core

test:             ## unit tests (no keys, no database)
	$(BIN)/python -m pytest -q tests ocr/tests

stop:             ## stop everything started by make agents / dev
	-pkill -f "python (red_flag|care_finder|bill_auditor|settlement_router|imessage_gateway|case_medic|coordinator).py"
	-pkill -f "tsx watch src/main.ts"
	-pkill -f "uvicorn app.main:app"
