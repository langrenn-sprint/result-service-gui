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
FERNET_KEY=<generate, see below>
JWT_EXP_DELTA_SECONDS=3600
LOGGING_LEVEL=INFO
STATIC_CACHE_MAX_AGE_SECONDS=3600
RACE_HOST_SERVER=localhost
RACE_HOST_PORT=8088
USERS_HOST_SERVER=localhost
USERS_HOST_PORT=8086
```

`FERNET_KEY` encrypts the session cookie and is required: the app does not start if it is missing or invalid. Generate one per environment and never reuse a key from an example:

```Zsh
echo "FERNET_KEY=$(python3 -c 'import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())')" >> .env
```

The tests use their own key, set in `[tool.pytest.ini_options]` in `pyproject.toml`.

Optional session cookie settings:

| Variable | Description |
| --- | --- |
| `JWT_MAX_SESSION_SECONDS` | `max_age` of the session cookie, so the session survives a browser restart. Same value as the maximum session length in user-service. Default `86400` (24 hours) |
| `SESSION_COOKIE_SECURE` | `true` to only send the session cookie over https. Set this when the GUI runs behind https. Default `false` |

When the token in the session has expired, pages that need login send the user to `/login?next=<page>`, and back to that page after login. `next` must be a relative path on this site.

An active user stays logged in: when half the token's lifetime has passed, the next request renews it with `POST /token/renew` in user-service. A session without activity still expires with the token (`JWT_EXP_DELTA_SECONDS` in user-service), and renewal is refused after `JWT_MAX_SESSION_SECONDS`, which logs the user out. Static files (`/static/`, `/files/`), `/ping`, `/ready`, `/login` and `/logout` do not renew the token.

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

Start the backend services on fixed ports with the [deploy](https://github.com/langrenn-sprint/deploy) repo, then start the server locally:

```Zsh
set -a
source .env
set +a
uv run adev runserver -p 8090 result_service_gui
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

To run the whole stack (GUIs, backend services and MongoDB) on fixed ports, use the [deploy](https://github.com/langrenn-sprint/deploy) repo.

The `docker-compose.yml` in this repo is for the contract tests. It publishes no fixed ports on the host, so the tests can run while the deploy stack is running. If you start it yourself, Docker picks a free port for the GUI:

```Zsh
docker compose up --build -d
docker compose port result-service-gui 8080   # e.g. 0.0.0.0:55012
```

## Running tests

We use [pytest](https://docs.pytest.org/en/latest/) for contract testing.

To run linters, checkers and tests:

```Zsh
% uv run poe release
```

Adapters are tested against small fake backend services, not mocks: see "Testing adapters against HTTP" in `tests/conftest.py`.

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