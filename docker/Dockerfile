# syntax=docker/dockerfile:1.10
FROM python:3.12-slim-bookworm AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1

WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-editable

ADD . /app/

RUN --mount=type=cache,target=/var/cache/apt \
  --mount=type=cache,target=/var/lib/apt \
    apt-get update && apt-get install -y xvfb fonts-noto-color-emoji fonts-unifont \
    libfontconfig1 libfreetype6 xfonts-scalable fonts-liberation \
    fonts-ipafont-gothic fonts-wqy-zenhei fonts-tlwg-loma-otf  \
    fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 libatspi2.0-0 \
    libcairo2 libcups2 libdbus-1-3 libdrm2 libegl1 libgbm1 libglib2.0-0 libgtk-3-0 \
    libnspr4 libnss3 libpango-1.0-0 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 \
    libxdamage1 libxext6 libxfixes3 libxrandr2 libxshmfence1 vim

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --frozen --no-editable --extra=docker

RUN uv run playwright install chromium &&\
  mv docker.env.prod .env.prod && \
  nb adapter install nonebot-adapter-red && \
  nb adapter install nonebot-adapter-qq

CMD ["uv", "run", "nb", "run"]
