#!/usr/bin/env bash
# Capture the PEAK - Linux/macOS helper. Usage: ./peak.sh <command>
set -e
IMAGE="jaimnbidu/capture-the-peak:latest"
ADMIN="${PEAK_ADMIN_PASS:-change_me_peak_admin}"
case "${1:-help}" in
  build)  docker build --no-cache -t "$IMAGE" . ;;
  board)  docker run --rm -d --name peak-board -p 8000:8000 -p 7681:7681 -p 9000:9000 \
            -e PEAK_MODE=board -e PEAK_ADMIN_PASS="$ADMIN" "$IMAGE"
          echo "board up -> http://localhost:8000  (admin: /admin)" ;;
  linear) docker run --rm -d --name peak-linear -p 8100:8000 -p 7781:7681 -p 9100:9000 \
            -e PEAK_MODE=linear -e PEAK_LAB_PORT=9100 -e PEAK_ADMIN_PASS="$ADMIN" "$IMAGE"
          echo "linear up -> http://localhost:8100  (admin: /admin)" ;;
  logs)   docker logs -f peak-board ;;
  stop)   docker stop peak-board peak-linear 2>/dev/null || true ;;
  push)   docker login && docker push "$IMAGE" ;;
  clean)  docker stop peak-board peak-linear 2>/dev/null || true; docker image rm "$IMAGE" 2>/dev/null || true ;;
  *) echo "usage: ./peak.sh build|board|linear|logs|stop|push|clean" ;;
esac
