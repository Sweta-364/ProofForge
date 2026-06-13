FROM python:3.12-slim

# Security: run as non-root inside sandbox containers
RUN groupadd --gid 1001 runner && \
    useradd --uid 1001 --gid runner --shell /bin/bash --create-home runner

# Install test runner + common Python packages used in problems
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        pytest==8.3.3 \
        pytest-json-report==1.5.0 \
        pytest-asyncio==0.24.0 \
        bandit==1.7.9 \
        cachetools==5.5.0 \
        python-jose[cryptography]==3.3.0 \
        PyJWT==2.8.0 \
        bcrypt==4.2.0 \
        fastapi==0.115.0 \
        uvicorn[standard]==0.30.6 \
        python-multipart==0.0.12 \
        email-validator==2.2.0 \
        itsdangerous==2.2.0 \
        jinja2==3.1.4 \
        sqlalchemy==2.0.36 \
        asyncpg==0.29.0 \
        aiofiles==24.1.0 \
        httpx==0.27.2 \
        pyyaml==6.0.2

WORKDIR /workspace

USER runner

# No CMD — the API passes the command when creating containers via Docker SDK
