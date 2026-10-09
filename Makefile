.PHONY: run test lint format terraform-check
run:
	uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
test:
	pytest -q
lint:
	ruff check .
	ruff format --check .
format:
	ruff check --fix .
	ruff format .
terraform-check:
	terraform fmt -check -recursive infra
	terraform -chdir=infra/bootstrap init -backend=false
	terraform -chdir=infra/bootstrap validate
	terraform -chdir=infra/workload init -backend=false
	terraform -chdir=infra/workload validate
	terraform -chdir=infra/workload test
