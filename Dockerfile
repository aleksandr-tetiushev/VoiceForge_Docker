FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Скачиваем VoiceForge
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 https://github.com/code-1py/VoiceForge.git /app/voiceforge

WORKDIR /app/voiceforge

# Устанавливаем зависимости
RUN pip install --no-cache-dir \
    discord.py \
    python-dotenv \
    pydantic

# Директория для постоянных данных
RUN mkdir -p /data

CMD ["python", "main.py"]
