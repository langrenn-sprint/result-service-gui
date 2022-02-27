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
GLOBAL_SETTINGS_FILE=global_settings.json
JWT_EXP_DELTA_SECONDS=3600
LOGGING_LEVEL=INFO
RACE_HOST_SERVER=localhost
RACE_SERVICE_PORT=8088
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
sudo docker-compose pull #oppdatere images
sudo docker-compose up --build #bygge og debug modus
sudo docker-compose up -d #kjøre-modus

### Starte services i docker
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
% poetry run adev runserver -p 8090 result_service_gui
```

### Teste manuelt
Brukermanualer finnes på https://langrenn-sprint.github.io/documentation/
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

## AZURE innstallere
1. Sette opp virtuell server - ubuntu
2. Networking: Open up port 8080 and 8090 for incoming traffic from any * incoming source.
3. Tildele dns navn - eks: ragdesprinten.norwayeast.cloudapp.azure.com

4. kommandoer for å innstallere containere
sudo apt-get update
sudo apt-get install python3.9
sudo apt-get install python-is-python3
sudo curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
log out and back in
sudo apt install python3-pip
sudo apt install pipx
sudo apt install python3.8-venv
pipe install nox
pipx ensurepath
pipx install poetry
sudo apt install docker-compose
sudo git clone https://github.com/langrenn-sprint/result-service-gui.git
copy .env file
sudo docker-compose up -—build

## AZURE remote access
ssh -i /home/heming/github/sprint-ubuntu_key.pem azureuser@ragdesprinten.northeurope.cloudapp.azure.com
ssh -i /home/heming/github/sprint2-ubuntu_key_0223.pem azureuser@ragdesprinten.norwayeast.cloudapp.azure.com
## slette images og containere
sudo docker image prune -a
sudo docker rm -f $(sudo docker ps -a -q)
