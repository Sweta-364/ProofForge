FROM python:3.12-slim

WORKDIR /app

RUN groupadd --gid 1001 app && \
    useradd --uid 1001 --gid app --create-home app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER app

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
