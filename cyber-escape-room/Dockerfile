# ============================================================
#  CYBER ESCAPE ROOM  -  single image
#  Generates the challenge assets at build time and SELF-TESTS
#  the whole solve chain. A failed test fails the build, so a
#  green build == a CTF that actually solves.
# ============================================================
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 DEBIAN_FRONTEND=noninteractive

# fonts-dejavu-core: the grid + spectrogram text need a real TTF to render legibly
RUN apt-get update && apt-get install -y --no-install-recommends \
      fonts-dejavu-core curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# deps first (layer cache). pillow+numpy are only needed to generate assets.
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt pillow numpy

# app code (.dockerignore keeps the answer key / db / caches out of the image)
COPY . .

# generate the 7 challenge files, then prove all 10 stages solve
RUN python3 tools/make_assets.py && python3 tools/verify.py

ENV CER_DB=/data/cer.db \
    CER_DURATION_MIN=150 \
    CER_EXTEND_MIN=30
EXPOSE 80

HEALTHCHECK --interval=30s --timeout=4s --retries=5 \
  CMD curl -fsS http://127.0.0.1:80/api/health || exit 1

WORKDIR /app/backend
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80", "--workers", "2"]
