#!/usr/bin/env bash
set -euo pipefail

IMAGE="${ACR_IMAGE:-registry.cn-hangzhou.aliyuncs.com/cloud_prg_hub/atom-mvp-backend:feature-repo-init}"
PLATFORM="${DOCKER_PLATFORM:-linux/amd64}"
REGISTRY="${IMAGE%%/*}"

if [[ -n "${ACR_USERNAME:-}" || -n "${ACR_PASSWORD:-}" ]]; then
  if [[ -z "${ACR_USERNAME:-}" || -z "${ACR_PASSWORD:-}" ]]; then
    echo "ACR_USERNAME and ACR_PASSWORD must be set together." >&2
    exit 1
  fi

  printf '%s' "$ACR_PASSWORD" | docker login "$REGISTRY" --username "$ACR_USERNAME" --password-stdin
fi

docker build --platform "$PLATFORM" -t "$IMAGE" .
docker push "$IMAGE"
docker buildx imagetools inspect "$IMAGE"
