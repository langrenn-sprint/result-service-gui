# webserver

Her finner du en enkel webserver som generer html basert på csv-filer i test-data

## Slik går du fram for å kjøre dette lokalt

## Utvikle og kjøre lokalt

### Krav til programvare

- [pyenv](https://github.com/pyenv/pyenv) (recommended)
- [poetry](https://python-poetry.org/)
- [nox](https://nox.thea.codes/en/stable/)
- [nox-poetry](https://pypi.org/project/nox-poetry/)

### Installere programvare og sette miljøvariable

```Shell
% git clone https://github.com/langrenn-sprint/result-service-gui.git
% cd evnt-service-gui
% pyenv install 3.10
% pyenv local 3.10
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
GOOGLE_APPLICATION_CREDENTIALS=/home/heming/github/secrets/application_default_credentials.json
COMPETITION_FORMAT_HOST_PORT=8094
COMPETITION_FORMAT_HOST_SERVER=localhost
DB_USER=admin
DB_PASSWORD=password
EVENTS_HOST_SERVER=localhost
EVENTS_HOST_PORT=8082
PHOTOS_HOST_SERVER=localhost
PHOTOS_HOST_PORT=8092
FERNET_KEY=23EHUWpP_MyKey_MyKeyhxndWqyc0vO-MyKeySMyKey=
GOOGLE_OAUTH_CLIENT_ID=12345My-ClientId12345.apps.googleusercontent.com
SERVICEBUS_NAMESPACE_CONNECTION_STR=<connection string>
JWT_EXP_DELTA_SECONDS=3600
LOGGING_LEVEL=INFO
RACE_HOST_SERVER=localhost
RACE_HOST_PORT=8088
USERS_HOST_SERVER=localhost
USERS_HOST_PORT=8086
```

### Config gcloud

```Shell
gcloud -v
gcloud auth login
gcloud config set project langrenn-sprint
gcloud auth configure-docker

### Starte services i docker
sudo docker-compose pull #oppdatere images
sudo docker-compose up --build #bygge og debug modus
sudo docker-compose up -d #kjøre-modus

### Oppdatere services i docker
sudo docker-compose stop #oppdatere images
sudo docker-compose pull #oppdatere images
sudo git pull #result-service-gui
sudo docker-compose up --build #bygge og debug modus
sudo docker-compose stop #oppdatere images
sudo docker-compose up -d #kjøre-modus


Denne fila _skal_ ligge i .dockerignore og .gitignore
### Kjøre webserver lokalt
```

## Start lokal webserver mha aiohttp-devtools(adev)

```Shell
% source .env
% export GOOGLE_APPLICATION_CREDENTIALS="/home/heming/github/secrets/application_default_credentials.json"
% poetry run adev runserver -p 8090 result_service_gui
% docker-compose up event-service race-service user-service photo-service mongodb competition-format-service event-service-gui
```

### Teste manuelt
Brukermanualer finnes på https://langrenn-sprint.github.io/docs
Enten åpne din nettleser på <http://localhost:8090/>

Eller via curl:

```Shell
% curl -i http://localhost:8090/
```

GCP testinstans: http://34.88.91.136:8090/
Dokumentasjon: https://langrenn-sprint.github.io/docs/

Når du endrer koden i result_service_gui, vil webserveren laste applikasjonen på nytt autoamtisk ved lagring.

## Referanser

aiohttp: <https://docs.aiohttp.org/>
