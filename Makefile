.PHONY: run smoke test autopilot stop score-prospects score-seed draft-outreach import-google-places first-money-status generate-secrets

run:
	PYTHONPATH=src python3 -m ai_receptionist_autopilot.server

smoke:
	python3 scripts/smoke.py

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -p '*_runtime.py'

autopilot:
	scripts/autopilot_run.sh

stop:
	scripts/stop.sh

score-prospects:
	python3 scripts/score_prospects.py validation/prospect-template.csv

score-seed:
	python3 scripts/score_prospects.py validation/sydney-emergency-plumbing-seed.csv > validation/sydney-emergency-plumbing-scored.csv

draft-outreach:
	python3 scripts/draft_outreach.py validation/sydney-emergency-plumbing-scored.csv > validation/outreach-drafts.csv

import-google-places:
	python3 scripts/google_places_prospects.py --out validation/google-places-sydney-plumbing.csv

first-money-status:
	python3 scripts/first_money_status.py

generate-secrets:
	python3 scripts/generate_secrets.py
