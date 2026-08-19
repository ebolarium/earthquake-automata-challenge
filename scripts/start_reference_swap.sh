#!/bin/sh
set -eu

NAME=etas-inversion-swap-helper
VOLUME=etas-inversion-swap
SIZE_MIB=8192

if docker inspect "$NAME" >/dev/null 2>&1; then
  if [ "$(docker inspect --format '{{.State.Running}}' "$NAME")" = "true" ]; then
    echo "$NAME is already running"
    exit 0
  fi
  echo "$NAME exists but is not running; inspect it before removal" >&2
  exit 1
fi

docker volume create "$VOLUME" >/dev/null
docker run -d \
  --privileged \
  --name "$NAME" \
  -v "$VOLUME:/swap" \
  --entrypoint sh \
  redis:7-alpine \
  -c "dd if=/dev/zero of=/swap/etas.swap bs=1M count=$SIZE_MIB && chmod 600 /swap/etas.swap && mkswap /swap/etas.swap && swapon /swap/etas.swap && tail -f /dev/null" \
  >/dev/null

echo "waiting for the temporary swap file"
for _ in $(seq 1 60); do
  if docker logs "$NAME" 2>&1 | grep -q "Setting up swapspace"; then
    docker run --rm --platform linux/amd64 \
      etas-challenge-reference cat /proc/swaps
    exit 0
  fi
  sleep 1
done

echo "temporary swap did not become ready" >&2
exit 1
