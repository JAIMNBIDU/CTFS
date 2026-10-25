# Cyber Escape Room — Local Setup

One command, one container, runs on any CPU. No Azure, no public IP.

## 0. Prereqs

Docker + Compose v2 (`docker compose version`). First build ~2-3 min: it
generates the 7 challenge files and self-tests all 10 stages. Green build = a CTF
that actually solves.

## 1. Build + run

From inside this `cyber-escape-room/` folder:

```bash
docker compose up -d --build
```

Open:

| Page | URL |
|------|-----|
| Play (register here) | http://localhost:8080 |
| Leaderboard | http://localhost:8080/leaderboard |
| Admin (optional) | http://localhost:8080/admin |

> The helper `./cer.sh up` does the same build, but its printed URL says
> `http://localhost/` ... that's wrong for the default compose, which maps to
> **port 8080**. Use `http://localhost:8080`. (Harmless cosmetic bug in the echo;
> the app is fine.)

Register as SINGLE (solo) or TEAM, hit start, and go.

## 2. Settings (optional)

All in `docker-compose.yml` under `environment:`:

| Setting | Default | What it does |
|---------|---------|--------------|
| `CER_ADMIN_PASSWORD` | `change_me_admin` | `/admin` password (you don't need admin to play) |
| `CER_SECRET` | `change_me_random` | cookie-signing salt |
| `CER_DURATION_MIN` | `150` | per-team clock in minutes |
| `CER_EXTEND_MIN` | `30` | minutes added per admin "+30" |

**Solo practice tip:** the 150-minute clock is an event timer. If you just want to
grind the puzzles without a countdown breathing on you, bump it:
`CER_DURATION_MIN: "6000"` then `docker compose up -d`.

## 3. The two physical stages (5 & 8)

No room, no printout needed. When you hit stage 5 or 8, your six coordinates
appear on your dashboard. Open [`challenges/grid.png`](challenges/grid.png), read
`row,column` for each coordinate in order, and that spells your six-letter word.
Submit it lowercase in braces. (Details + a worked example in `SOLUTIONS.md`.)

## 4. Stop / reset / wipe

```bash
docker compose stop                 # pause
docker compose down                 # stop + remove (data survives)
docker compose down -v              # wipe everything incl. the board
```

Helper: `./cer.sh stop` / `./cer.sh wipe`.

---

## Port conflicts (read this if it won't start)

Default host port is **8080**. If it's taken, Docker prints:

```
Error ... Bind for 0.0.0.0:8080 failed: port is already allocated
```

Find it:
```bash
# Linux / macOS
lsof -i :8080       # or: docker ps
# Windows (PowerShell)
netstat -ano | findstr :8080
```

Fix: stop whatever holds it, or move the app. In `docker-compose.yml`, change the
**host** side only (left of the colon):

```yaml
    ports:
      - "8090:80"     # was "8080:80"  -> now play on http://localhost:8090
```

Leave `:80` (the container side) alone. Then `docker compose up -d`.

---

## Does it run? (honest status)

- **Verified by reading:** binds `0.0.0.0:80`, compose maps it to host 8080, no
  hardcoded IPs, multi-arch base image (`python:3.12-slim` ... works on Intel,
  AMD, and Apple Silicon with no changes).
- **Not yet verified:** a clean build on a fresh machine. Run
  `docker compose up -d --build` once and confirm the self-test passes and
  `docker compose ps` shows the container `healthy` before you rely on it.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `port is already allocated` | See "Port conflicts" above. |
| `http://localhost/` doesn't load | Default is port **8080**, not 80. Use `http://localhost:8080`. |
| Build fails at self-test | A challenge asset is inconsistent ... the error names the stage. Only happens if `challenges.py` was edited without re-running `tools/make_assets.py`. |
| Container won't stay up | `docker compose logs --tail 50`. |
| Want a clean board | `docker compose down -v && docker compose up -d --build`. |
