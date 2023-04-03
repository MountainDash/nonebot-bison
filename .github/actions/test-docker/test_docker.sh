#!/bin/bash

DOCKER_IMAGE=$1
WAIT_TIME=$2

docker run --name test-docker-container -d $DOCKER_IMAGE > /dev/null
sleep $WAIT_TIME

CONTAINER_STATE=$(docker ps -f name=test-docker-container -a --format '{{.State}}')
if [[ $CONTAINER_STATE = "running" ]]; then
    echo "container still running, check passed"
    docker rm -f test-docker-container > /dev/null
    exit
else
    echo "container exited"
    docker logs test-docker-container
    docker rm test-docker-container > /dev/null
    exit 1
fi
