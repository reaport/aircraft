FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
	build-essential \
	&& rm -rf /var/lib/apt/lists/*

# Установка uv через pip
RUN pip install uv

# Проверка наличия requirements.txt или pyproject.toml и копирование нужного файла
COPY pyproject.toml* ./

# Установка зависимостей с использованием uv
RUN uv sync

# Копирование всего проекта
COPY . .

# Настройка переменных окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Порт, на котором будет работать приложение
EXPOSE 8000

# Запуск приложения с помощью uvicorn
CMD uv run python -m uvicorn main:app --host 0.0.0.0 --port 8000 