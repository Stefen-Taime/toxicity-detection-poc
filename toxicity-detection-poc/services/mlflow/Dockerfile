FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY entrypoint.sh .
COPY . .

RUN chmod +x entrypoint.sh

RUN mkdir -p /mlflow

EXPOSE 5000

ENTRYPOINT ["/app/entrypoint.sh"]
