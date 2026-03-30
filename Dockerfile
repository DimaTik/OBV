FROM python:3.11-slim

# Создаем рабочую папку
WORKDIR /app

# Копируем requirements.txt из проекта
COPY requirements.txt requirements.txt
# --no-cache-dir - скачиваем без кеша
RUN pip install --no-cache-dir -r requirements.txt
# Копируем из основной папки проекта в /app
COPY . .
CMD ["python", "-u", "./main.py"]

