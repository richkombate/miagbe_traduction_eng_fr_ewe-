.PHONY: api test install frontend
install:
	pip install -r requirements.txt
api:
	uvicorn traducteur.api.main:app --reload --app-dir src
test:
	pytest -q
frontend:
	cd frontend && npm run dev
