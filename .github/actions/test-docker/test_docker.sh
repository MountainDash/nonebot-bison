#!/bin/bash

set -e

DOCKER_IMAGE=$1
WAIT_TIME=$2
NETWORK_NAME="bison-test-network"

# 清理可能残留的容器/网络
docker rm -f test-docker-container > /dev/null 2>&1 || true
docker rm -f playwright > /dev/null 2>&1 || true
docker network rm $NETWORK_NAME > /dev/null 2>&1 || true

# 创建自定义网络，让被测镜像可以通过容器名 playwright 访问 playwright server
docker network create $NETWORK_NAME > /dev/null

# 从被测镜像内解析 playwright 版本（与镜像锁定的版本保持一致）
PLAYWRIGHT_VERSION=$(docker run --rm --entrypoint /app/.venv/bin/python \
    $DOCKER_IMAGE -c "from importlib.metadata import version; print(version('playwright'))")
echo "Resolved Playwright version: $PLAYWRIGHT_VERSION"

if [[ -z "$PLAYWRIGHT_VERSION" ]]; then
    echo "failed to resolve playwright version from image $DOCKER_IMAGE"
    exit 1
fi

# 启动 playwright server 容器（与被测镜像同网络，通过 --name playwright 提供 DNS）
docker run -d --rm --init --ipc=host \
    --name playwright \
    --network $NETWORK_NAME \
    -p 3000:3000 \
    --workdir /home/pwuser \
    --user pwuser \
    "mcr.microsoft.com/playwright:v${PLAYWRIGHT_VERSION}-noble" \
    /bin/sh -c "npx -y playwright@${PLAYWRIGHT_VERSION} run-server --port 3000 --host 0.0.0.0" \
    || { echo "failed to start playwright container"; docker logs playwright 2>&1 || true; exit 1; }

# 等待 playwright server 就绪（容器退出则立即失败）
for i in $(seq 1 60); do
    if ! docker inspect -f '{{.State.Running}}' playwright 2>/dev/null | grep -q true; then
        echo "playwright container exited unexpectedly"
        docker logs playwright 2>&1 || true
        docker rm -f playwright > /dev/null 2>&1 || true
        docker network rm $NETWORK_NAME > /dev/null 2>&1 || true
        exit 1
    fi
    if python3 -c "import socket; s = socket.create_connection(('127.0.0.1', 3000), 1); s.close()" 2>/dev/null; then
        echo "Playwright server is ready on ws://playwright:3000/"
        break
    fi
    sleep 1
done

# 启动被测镜像
docker run --name test-docker-container -d --network $NETWORK_NAME $DOCKER_IMAGE > /dev/null
sleep $WAIT_TIME

CONTAINER_STATE=$(docker ps -f name=test-docker-container -a --format '{{.State}}')
if [[ $CONTAINER_STATE = "running" ]]; then
    echo "container still running, check passed"
    docker rm -f test-docker-container > /dev/null
    docker rm -f playwright > /dev/null 2>&1 || true
    docker network rm $NETWORK_NAME > /dev/null 2>&1 || true
    exit
else
    echo "container exited"
    docker logs test-docker-container
    docker rm test-docker-container > /dev/null 2>&1 || true
    docker rm -f playwright > /dev/null 2>&1 || true
    docker network rm $NETWORK_NAME > /dev/null 2>&1 || true
    exit 1
fi
