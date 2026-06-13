FROM python:3.12-slim

# git + ssh client for the browser terminal's git push support
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Security: run as non-root
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app/backend

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# aioredis 2.0.1 is broken on Python 3.11+: asyncio.TimeoutError == builtins.TimeoutError,
# so its TimeoutError class declares a duplicate base. Drop the redundant base.
RUN sed -i 's/class TimeoutError(asyncio\.TimeoutError, builtins\.TimeoutError, RedisError)/class TimeoutError(asyncio.TimeoutError, RedisError)/' \
    /usr/local/lib/python3.12/site-packages/aioredis/exceptions.py

# Copy application code
COPY . .

# Give appuser access to the sandbox temp dir
RUN mkdir -p /tmp/submissions && chown appuser:appgroup /tmp/submissions

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
