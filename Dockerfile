FROM python:3.12-slim AS bot

ENV ENV_FILE ".env"

COPY . /app
WORKDIR /app

RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python3", "main.py", "--env-file", "$ENV_FILE"]