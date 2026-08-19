#!/bin/sh
set -eu

NAME=etas-inversion-swap-helper
VOLUME=etas-inversion-swap

if docker inspect "$NAME" >/dev/null 2>&1; then
  docker exec "$NAME" swapoff /swap/etas.swap
  docker stop "$NAME" >/dev/null
  docker rm "$NAME" >/dev/null
fi

if docker volume inspect "$VOLUME" >/dev/null 2>&1; then
  docker volume rm "$VOLUME" >/dev/null
fi

echo "temporary reference swap removed"
