FROM python:3.10

RUN mkdir -p /app
WORKDIR /app

RUN pip install --upgrade pip
RUN pip install "poetry==1.1.6"
COPY poetry.lock pyproject.toml /app/

# Project initialization:
RUN poetry config virtualenvs.create false \
  && poetry install --no-dev --no-interaction --no-ansi

ADD result_service_gui /app/result_service_gui

EXPOSE 8080

CMD gunicorn  "result_service_gui:create_app"  --config=result_service_gui/gunicorn_config.py --worker-class aiohttp.GunicornWebWorker
