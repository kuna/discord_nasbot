.PHONY: run cli test docker-build docker-run

run:
	uv run python main.py

# stdin test mode: run plugins without connecting to discord
cli:
	TEST_CLI_MODE=1 uv run python main.py

test:
	uv run pytest

docker-build:
	docker build -t discord-nasbot .

docker-run:
	docker run --rm --env-file .env -v "$(PWD)/downloads:/data/downloads" discord-nasbot:latest
