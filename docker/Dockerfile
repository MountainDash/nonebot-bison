# syntax=docker/dockerfile:1.10
FROM python:3.12-slim AS metadata-stage

WORKDIR /tmp

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    python3-pip \
    git \
    && pip install toml \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY ./pyproject.toml ./

RUN echo "📋 Collecting metadata..." && \
    export CREATED_DATE="$(date -u '+%Y-%m-%d %H:%M:%S UTC')" && \
    export PYPROJECT_NAME=$(python3 -c 'import toml; print(toml.load("pyproject.toml")["project"]["name"])') && \
    export DESCRIPTION=$(python3 -c 'import toml; print(toml.load("pyproject.toml")["project"]["description"])') && \
    export AUTHOR=$(python3 -c 'import toml; print(toml.load("pyproject.toml")["project"]["authors"][0]["name"])') && \
    echo "⏰ Created Date: $CREATED_DATE" && \
    echo "📝 Project Name: $PYPROJECT_NAME" && \
    echo "📄 Description: $DESCRIPTION" && \
    echo "👤 Author: $AUTHOR" && \
    echo "$CREATED_DATE" > /tmp/CREATED_DATE && \
    echo "$PYPROJECT_NAME" > /tmp/PYPROJECT_NAME && \
    echo "$DESCRIPTION" > /tmp/DESCRIPTION && \
    echo "$AUTHOR" > /tmp/AUTHOR


RUN --mount=type=bind,source=./.git/,target=/tmp/.git/ \
    echo "🏷️  Checking version information..." && \
    VERSION=$(git describe --tags --exact-match 2>/dev/null || git rev-parse --short HEAD || echo "unknown") && \
    echo "📌 Version: $VERSION" && \
    echo "$VERSION" > /tmp/VERSION

LABEL org.opencontainers.image.created="$(cat /tmp/CREATED_DATE)" \
      org.opencontainers.image.authors="$(cat /tmp/AUTHOR)" \
      org.opencontainers.image.description="$(cat /tmp/DESCRIPTION)" \
      org.opencontainers.image.name="$(cat /tmp/PYPROJECT_NAME)" \
      org.opencontainers.image.version="$(cat /tmp/VERSION)"

FROM python:3.12-slim AS production

WORKDIR /app

#ENV UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV DEBIAN_FRONTEND=noninteractive \
    UV_COMPILE_BYTECODE=1 \
    UV_SYSTEM_PYTHON=true \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    TZ=Asia/Shanghai

RUN echo "📦 Installing system dependencies..." && \
#    --mount=type=cache,target=/var/cache/apt \
#    --mount=type=cache,target=/var/lib/apt \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    xvfb \
    fonts-noto-color-emoji fonts-unifont \
    libfontconfig1 libfreetype6 xfonts-scalable \
    fonts-liberation fonts-ipafont-gothic \
    fonts-wqy-zenhei fonts-tlwg-loma-otf \
    vim && \
    echo "🔍 Verifying Python installation..." && \
    if PYTHON_VERSION=$(python3 --version 2>&1); then \
        echo "✅ ${PYTHON_VERSION} installed successfully"; \
    else \
        echo "❌ Python installation failed" && exit 1; \
    fi && \
    fc-cache -fv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    echo "✅ System dependencies installed successfully"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN echo "🔍 Verifying uv installation..." && \
    if UV_VERSION=$(uv --version 2>&1); then \
        echo "✅ uv version ${UV_VERSION} installed successfully"; \
    else \
        echo "❌ uv installation failed" && exit 1; \
    fi

COPY ./pyproject.toml ./uv.lock ./

RUN echo "📦 Installing bison dependencies..." && \
    uv pip install --extra=docker --requirement pyproject.toml --no-cache && \
    echo "✅ Dependencies installed successfully" && \
    echo "🧹 Cleaning up uv..." && \
    rm -rf /bin/uv /bin/uvx && \
    rm -rf /root/.cache/ && \
    rm -rf /root/.uv && \
    echo "✅ UV cleanup completed"

COPY --from=metadata-stage /tmp/VERSION /app/VERSION
COPY . .

RUN echo "🎭 Installing Playwright..." && \
    playwright install --with-deps chromium && \
    rm -rf /var/lib/apt/lists/* /tmp/* && \
    mv docker.env.prod .env.prod && \
    echo "✅ Playwright installed successfully"

EXPOSE 8080

RUN echo '#!/bin/bash\n\
echo "📌 Current bison Version: $(cat /app/VERSION)"\n\
echo "🚀 Starting backend service..."\n\
nb run' > /app/start.sh && \
    chmod +x /app/start.sh

CMD ["/app/start.sh"]
