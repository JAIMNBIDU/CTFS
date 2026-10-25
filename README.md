# CTF

Two self-hostable Capture The Flag events, built and run for a college TechFest,
packaged here so you can clone, build, and play them locally on your own machine.
Everything runs in Docker. No cloud, no public server, no account.

```
capture-the-peak/        20-camp scored CTF (5 categories)  +  pro bonus tier
cyber-escape-room/        10-stage chained escape-room CTF
```

## What you need

- **Docker** with Compose v2 (`docker compose version` should print something).
  - Linux: `curl -fsSL https://get.docker.com | sudo sh`
  - Mac / Windows: Docker Desktop.
- ~2 GB free disk, a browser, and 5 minutes for the first build.

That's the whole dependency list. The challenge tools (CyberChef, exiftool,
Audacity, etc.) run in your browser or are already inside the container.

## Pick one and go

| Event | Difficulty | Start here |
|-------|-----------|------------|
| **Capture the PEAK** | intermediate → hard, pick-your-order | [`capture-the-peak/SETUP.md`](capture-the-peak/SETUP.md) |
| **Capture the PEAK :: PRO** | hard crypto/reversing, 5 camps | [`capture-the-peak-pro/SETUP.md`](capture-the-peak-pro/SETUP.md) |
| **Cyber Escape Room** | easy → hard, strictly chained | [`cyber-escape-room/SETUP.md`](cyber-escape-room/SETUP.md) |

Each folder has three docs: a **README** (what it is), a **SETUP** (how to build
and run it locally), and a **SOLUTIONS** file.

## ⚠️ Spoilers

Every `SOLUTIONS.md` is the complete answer key. Don't open it until you've
tried. Worse: because these build from source, the flags also live in the code
itself (`config/flags.yaml` in PEAK, `backend/challenges.py` in Escape). If you
want to actually solve these, stay out of those files. Reading the source is
cheating with extra steps.

## Platform note

`cyber-escape-room` builds on any CPU. `capture-the-peak` ships an x86_64 binary
for its in-browser terminal (ttyd); on **Apple Silicon / ARM** you need the
one-line Dockerfile change documented in `capture-the-peak/SETUP.md`. Everything
else is architecture-agnostic.
