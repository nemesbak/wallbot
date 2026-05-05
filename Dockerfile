FROM python:3.11-slim-bookworm

RUN apt-get update && \
    apt-get install -y --no-install-recommends locales && \
    echo "es_ES.UTF-8 UTF-8" >> /etc/locale.gen && \
    locale-gen && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV LANG=es_ES.UTF-8 \
    LC_ALL=es_ES.UTF-8 \
    TZ=Europe/Madrid

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY tests/ ./tests/
COPY pytest.ini .
COPY VERSION .

RUN mkdir -p /data /logs

CMD ["python3", "-m", "src.wallbot"]
