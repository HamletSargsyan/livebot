run:
	bash ./run.sh

stop:
	kill $(cat .pid)

lint:
	ruff check --respect-gitignore src tools
	pyright src tools

format:
	ruff format --respect-gitignore src tools

fix:
	ruff check --respect-gitignore --fix src tools

dev-install:
	pip install --upgrade ruff pyright pre-commit

dev-setup: dev-install
	pre-commit install

release:
	python3 tools/bump_version.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf nohup.out .pid site .*_cache release_body.md
