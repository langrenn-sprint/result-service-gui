# webserver

Her finner du en enkel webserver som generer html basert på csv-filer i test-data

## Slik går du fram for å kjøre dette lokalt

## Utvikle og kjøre lokalt

### Krav til programvare

- [pyenv](https://github.com/pyenv/pyenv) (recommended)
- [poetry](https://python-poetry.org/)
- [nox](https://nox.thea.codes/en/stable/)
- [nox-poetry](https://pypi.org/project/nox-poetry/)

### Installere programvare

```Shell
% git clone https://github.com/langrenn-sprint/result-service-gui.git
% cd evnt-service-gui
% pyenv install 3.9.1
% pyenv local 3.9.1
% pipx install poetry
% pipx install nox
% pipx inject nox nox-poetry
% poetry install
```

## oppdatere

```Shell
% poetry update / poetry add <module>
```

## Miljøvariable

```Shell
Du må sette opp ei .env fil med miljøvariable. Eksempel:
JWT_SECRET=secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD=password
DB_USER=admin
DB_PASSWORD=password
EVENTS_HOST_SERVER=localhost
EVENTS_HOST_PORT=8082
FERNET_KEY=23EHUWpP_tpleR_RjuX5hxndWqyc0vO-cjNUMSzbjN4=
JWT_EXP_DELTA_SECONDS=3600
LOGGING_LEVEL=INFO
RACE_HOST_SERVER=localhost
RACE_SERVICE_PORT=8088
SPORTS_CLUBS=Bækkelaget,Heming,Kjelsås,Koll,Lillomarka,Lyn,Njård,Rustad,Røa,Try,Årvoll
TIME_ZONE_OFFSET=0
USERS_HOST_SERVER=localhost
USERS_HOST_PORT=8086
USER_SERVICE_HOST=localhost
USER_SERVICE_PORT=8086
DB_USER=admin
DB_PASSWORD=password
```

### Config gcloud

```Shell
gcloud -v
gcloud auth login
gcloud config set project langrenn-sprint
gcloud auth configure-docker

### Starte services i docker
docker-compose pull #oppdatere images
docker-compose up --build
docker-compose up --build event-service race-service user-service mongodb

Denne fila _skal_ ligge i .dockerignore og .gitignore
### Kjøre webserver lokalt
```

## Start lokal webserver mha aiohttp-devtools(adev)

```Shell
% source .env
% poetry run adev runserver -p 8090 result_service_gui
```

### Teste manuelt

Enten åpne din nettleser på <http://localhost:8090/>

Eller via curl:

```Shell
% curl -i http://localhost:8090/
```

Når du endrer koden i result_service_gui, vil webserveren laste applikasjonen på nytt autoamtisk ved lagring.

## Referanser

aiohttp: <https://docs.aiohttp.org/>
