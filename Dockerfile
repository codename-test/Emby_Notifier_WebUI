FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV WEB_PORT=5000
VOLUME ["/data"]

CMD ["python3", "main.py"]
