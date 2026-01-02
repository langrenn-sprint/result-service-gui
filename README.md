# webserver

Her finner du en enkel webserver som generer html sider basert på innhold fra backend tjenester event-service, user-service, competition-format-service, race-service og photo-service.

## Slik går du fram for å kjøre dette lokalt

## Usage example

```Zsh
% curl -H "Content-Type: application/json" \
  -X POST \
  --data '{"username":"admin","password":"passw123"}' \
  http://localhost:8080/login
% export ACCESS="" #token from response
% curl -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS" \
  -X POST \
  --data @tests/files/user.json \
  http://localhost:8080/users
% curl -H "Authorization: Bearer $ACCESS"  http://localhost:8080/users
```

## Architecture

Layers:

- views: routing functions, maps representations to/from model
- services: enforce validation, calls adapter-layer for storing/retrieving objects
- models: model-classes
- adapters: adapters to external services

## Environment variables

To run the service locally, you need to supply a set of environment variables. A simple way to solve this is to supply a .env file in the root directory.

A minimal .env:

```Zsh
JWT_SECRET=secret
ERROR_FILE=error.log
ADMIN_USERNAME=admin
ADMIN_PASSWORD=password
COMPETITION_FORMAT_HOST_PORT=8094
COMPETITION_FORMAT_HOST_SERVER=localhost
DB_USER=admin
DB_PASSWORD=password
EVENTS_HOST_SERVER=localhost
EVENTS_HOST_PORT=8082
PHOTOS_HOST_SERVER=localhost
PHOTOS_HOST_PORT=8092
FERNET_KEY=23EHUWpP_MyKey_MyKeyhxndWqyc0vO-MyKeySMyKey=
JWT_EXP_DELTA_SECONDS=3600
LOGGING_LEVEL=INFO
RACE_HOST_SERVER=localhost
RACE_HOST_PORT=8088
USERS_HOST_SERVER=localhost
USERS_HOST_PORT=8086
```

## Requirement for development

Install [uv](https://docs.astral.sh/uv/), e.g.:

```Zsh
% curl -LsSf https://astral.sh/uv/install.sh | sh
```

## If required - virtual environment

Install: curl <https://pyenv.run> | bash
Create: python -m venv .venv (replace .venv with your preferred name)
Install python 3.12: pyenv install 3.12
Activate:
source .venv/bin/activate

## Then install the dependencies:

```Zsh
% uv sync
```

## Running the API locally

Start the server locally - use docker to start required backend-services:

```Zsh
% uv run adev runserver -p 8090 result_service_gui
% docker compose up event-service competition-format-service user-service race-service mongodb photo-service integration-service
```

## Running the API in a wsgi-server (gunicorn)

```Zsh
% uv run gunicorn result_service_gui:create_app --bind localhost:8080 --worker-class aiohttp.GunicornWebWorker
```

## Running the wsgi-server in Docker

To build and run the api in a Docker container:

```Zsh
% docker build -t langrenn-sprint/result-service-gui:latest .
% docker run --env-file .env -p 8080:8080 -d langrenn-sprint/result-service-gui:latest
```

The easier way would be with docker-compose:

```Zsh
docker compose up --build
```

## Running tests

We use [pytest](https://docs.pytest.org/en/latest/) for contract testing.

To run linters, checkers and tests:

```Zsh
% uv run poe release
```

To run tests with logging, do:

```Zsh
% uv run pytest -m integration -- --log-cli-level=DEBUG
```

### Starte services i docker
docker compose pull #oppdatere images
docker compose up --build #bygge og debug modus
docker compose up -d #kjøre-modus

### Oppdatere services i docker
docker compose down #stoppe images
docker compose pull #oppdatere images
docker compose up --build #bygge og debug modus
docker compose stop #oppdatere images
docker compose up -d #kjøre-modus

## slette images og containere
```Shell
docker system prune -a --volumes
```