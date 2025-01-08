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

FROM node:22.13.0-slim AS frontend-stage

WORKDIR /tmp/admin-frontend

ENV TZ=Asia/Shanghai \
    PNPM_HOME="/pnpm" \
    PATH="$PNPM_HOME:$PATH"

COPY ./admin-frontend/package.json ./admin-frontend/pnpm-lock.yaml ./

RUN corepack enable && \
    corepack prepare pnpm@latest --activate && \
    echo "🔔 Verifying Node.js installation..." && \
    if NODE_VERSION=$(node --version 2>&1); then \
        echo "✅ Node.js version ${NODE_VERSION} installed successfully"; \
    else \
        echo "❌ Node.js installation failed" && exit 1; \
    fi && \
    echo "🔔 Verifying pnpm installation..." && \
    if PNPM_VERSION=$(pnpm --version 2>&1); then \
        echo "✅ pnpm version ${PNPM_VERSION} installed successfully"; \
    else \
        echo "❌ pnpm installation failed" && exit 1; \
    fi

RUN pnpm install --frozen-lockfile

COPY ./admin-frontend .
RUN mkdir -p ../nonebot_bison/admin_page/dist

RUN echo "🏗️ Starting frontend build..." && \
    pnpm run build && \
    echo "✅ Frontend build completed"

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS playwright-stage

WORKDIR /tmp

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

RUN echo "📦 Installing playwright..." && \
    uvx playwright install --with-deps chromium && \
    echo "✅ Playwright installed successfully"

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS uv-stage

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_FROZEN=1 \
    UV_LINK_MODE=copy \
    TZ=Asia/Shanghai

RUN echo "🔔 Verifying uv installation..." && \
    if UV_VERSION=$(uv --version 2>&1); then \
        echo "✅ uv version ${UV_VERSION} installed successfully"; \
    else \
        echo "❌ uv installation failed" && exit 1; \
    fi

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    echo "📦 Installing project dependencies..." && \
    uv sync --no-install-project --no-dev --extra docker && \
    echo "✅ Dependencies installed successfully"

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS production

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_FROZEN=1 \
    UV_LINK_MODE=copy \
    TZ=Asia/Shanghai \
    SHELL="/bin/bash"

RUN echo "📦 Installing system dependencies..." && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        xvfb \
        fonts-noto-color-emoji \
        fonts-unifont \
        libfontconfig1 \
        libfreetype6 \
        xfonts-scalable \
        fonts-liberation \
        fonts-ipafont-gothic \
        fonts-wqy-zenhei \
        fonts-tlwg-loma-otf \
        at-spi2-common \
        fonts-freefont-ttf \
        libasound2 \
        libasound2-data \
        libatk-bridge2.0-0 \
        libatk1.0-0 \
        libatspi2.0-0 \
        libavahi-client3 \
        libavahi-common-data \
        libavahi-common3 \
        libcairo2 \
        libcups2 \
        libdatrie1 \
        libdbus-1-3 \
        libfribidi0 \
        libgbm1 \
        libglib2.0-0 \
        libgraphite2-3 \
        libharfbuzz0b \
        libnspr4 \
        libnss3 \
        libpango-1.0-0 \
        libthai-data \
        libthai0 \
        libwayland-server0 \
        libxcb-render0 \
        libxcomposite1 \
        libxdamage1 \
        libxi6 \
        libxkbcommon0 && \
    fc-cache -fv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    echo "✅ System dependencies installed successfully"

# 少变动的放上面，频繁变动的放下面
COPY ./docker.env.prod ./.env
COPY --from=playwright-stage /root/.cache/ms-playwright /root/.cache/ms-playwright
COPY extra_plugins/ /app/extra_plugins/
COPY --from=frontend-stage /tmp/nonebot_bison/admin_page/dist ./nonebot_bison/admin_page/dist
COPY --from=uv-stage /app /app
COPY ./pyproject.toml ./uv.lock ./README.md ./
COPY nonebot_bison/ /app/nonebot_bison/
COPY --from=metadata-stage /tmp/VERSION /app/VERSION

RUN --mount=type=cache,target=/root/.cache/uv \
    echo "📦 Installing bison project..." && \
    uv sync --no-dev --extra docker && \
    uv run nb adapter install nonebot-adapter-satori && \
    uv run nb adapter install nonebot-adapter-qq && \
    uv run nb plugin install nonebot-plugin-sentry && \
    echo "✅ Bison installed successfully"

EXPOSE 8080

RUN echo '#!/bin/bash' > /app/start.sh && \
    echo 'echo "📌 Current bison Version: $(cat /app/VERSION)"' >> /app/start.sh && \
    echo 'echo "🚀 Starting service..."' >> /app/start.sh && \
    echo 'source /app/.venv/bin/activate' >> /app/start.sh && \
    echo 'nb run' >> /app/start.sh && \
    chmod +x /app/start.sh

CMD ["/app/start.sh"]
