FROM python:3.11-slim
WORKDIR /app
RUN apt-get update \
    && apt-get upgrade -y \
    && useradd --system --create-home --home-dir /home/app app \
    && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ./app ./app
COPY ./scripts ./scripts
EXPOSE 8000
USER app
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
