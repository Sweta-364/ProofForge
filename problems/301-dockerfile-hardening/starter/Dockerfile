# BROKEN: unpinned base image, runs as root, poor layer caching, cached wheels.
FROM python:latest

COPY . .

RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
