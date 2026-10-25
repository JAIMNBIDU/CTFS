#!/usr/bin/env bash
# Cyber Escape Room helper.  Usage: ./cer.sh <command>
set -e
case "${1:-help}" in
  up)    docker compose up -d --build
         echo "up -> http://localhost/   admin: http://localhost/admin" ;;
  logs)  docker compose logs -f ;;
  stop)  docker compose down ;;
  wipe)  docker compose down -v && echo "board wiped (volume deleted)" ;;
  rebuild) docker compose up -d --build --force-recreate ;;
  push)  docker login && docker compose build && docker push jaimnbidu/cyber-escape-room:latest ;;
  *) echo "usage: ./cer.sh up|logs|stop|wipe|rebuild|push" ;;
esac
