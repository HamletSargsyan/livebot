run:
	bash ./run.sh

stop:
	kill $(cat .pid)

lint:
	ruff check src
	pyright src

dev-install:
	pip install --upgrade ruff pyright pre-commit

dev-setup: dev-install
	pre-commit install


clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf nohup.out .pid site .*_cache
