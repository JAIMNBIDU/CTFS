# ============================================================
#  CAPTURE THE PEAK  -  single image, two modes (board | linear)
#  Multi-stage: the builder generates + SELF-TESTS every camp.
#  A failed self-test fails the build, so a green build == a
#  working CTF. Only salted hashes reach the final image; no
#  plaintext flags, no generator scripts.
# ============================================================
ARG TTYD_VER=1.7.7

# ---------- stage 1: builder ----------
FROM debian:stable-slim AS builder
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-pip python3-venv gcc binutils libc6-dev \
      steghide libimage-exiftool-perl imagemagick zbar-tools \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /venv && /venv/bin/pip install --no-cache-dir --timeout=120 --retries=10 \
      scapy==2.5.0 pillow qrcode numpy PyYAML pyjwt pycryptodome Flask==3.0.3
ENV PATH=/venv/bin:$PATH
WORKDIR /src
COPY config/ ./config/
COPY builder/ ./builder/
COPY lab/ ./lab/
# generate artifacts + hashes, then prove all 17 camps solve
RUN python3 builder/generate.py /build \
    && python3 builder/verify.py /build

# ---------- stage 2: final image ----------
FROM debian:stable-slim
ARG TTYD_VER
ENV DEBIAN_FRONTEND=noninteractive
# runtime tools: only what the camps + hints actually need, plus basics
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-pip \
      tshark steghide libimage-exiftool-perl imagemagick zbar-tools \
      john hashcat pocl-opencl-icd ocl-icd-libopencl1 unzip \
      xxd openssl curl ca-certificates ltrace less nano vim-tiny \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --timeout=120 --retries=10 --break-system-packages \
      Flask==3.0.3 PyYAML==6.0.2 pyjwt==2.9.0 pycryptodome==3.20.0

# ttyd (in-browser shell). amd64 pin; for arm64 swap the asset name.
RUN curl -fsSL -o /usr/local/bin/ttyd \
      https://github.com/tsl0922/ttyd/releases/download/${TTYD_VER}/ttyd.x86_64 \
    && chmod +x /usr/local/bin/ttyd

# unprivileged player
RUN useradd -m -s /bin/bash climber

# app code + generated content
COPY server/ /opt/peak/server/
COPY lab/app.py /opt/peak/lab/app.py
COPY --from=builder /build/ctf /ctf
COPY --from=builder /build/data /opt/peak/data
COPY --from=builder /build/lab/flags.json /opt/peak/lab/flags.json
COPY --from=builder /build/wordlists /opt/peak/wordlists
COPY entrypoint.sh /opt/peak/entrypoint.sh
COPY player_bashrc.sh /home/climber/.bashrc

# the PRO tier keeps no flags on disk ... camps 1/3/4 are served from relay
# memory, camps 2/5 are self-contained artifacts.

# give the player a copy of the downloadable artifacts in their shell
RUN mkdir -p /home/climber/camps && cp -r /ctf/* /home/climber/camps/ 2>/dev/null || true; \
    ln -s /opt/peak/wordlists/peak-mini.txt /home/climber/peak-mini.txt; \
    chown -R climber:climber /home/climber; \
    mkdir -p /var/peak && chown climber:climber /var/peak; \
    chmod +x /opt/peak/entrypoint.sh

# ---- HARDENING: three users, player shell locked out of everything ----------
# climber = the in-browser terminal (ttyd). relay = the vulnerable lab. portal =
# the scoring server. The player shell (climber) must not be able to read the
# flag stores, the hash store, the DB, or the server/lab source. Those belong to
# relay / portal and are chmod'd away from "other".
RUN useradd -r -M -s /usr/sbin/nologin relay && \
    useradd -r -M -s /usr/sbin/nologin portal && \
    # portal owns the hash store + prompts/hints + server source + /ctf originals
    chown -R portal:portal /opt/peak/server /opt/peak/data /ctf && \
    chmod -R o-rwx /opt/peak/server /opt/peak/data /ctf && \
    # relay owns the lab (incl. the in-memory flag source)
    chown -R relay:relay /opt/peak/lab && \
    chmod -R o-rwx /opt/peak/lab && \
    # the wordlist is a real player tool -> stays readable by everyone
    chmod -R a+rX /opt/peak/wordlists && \
    # the player's OWN copy of the camp artifacts stays theirs (expected)
    chown -R climber:climber /home/climber

# portal :8000  |  ttyd :7681  |  lab relay :9000
EXPOSE 8000 7681 9000
ENV PEAK_MODE=board \
    PEAK_DATA=/opt/peak/data \
    PEAK_CTF=/ctf \
    PEAK_DB=/var/peak/peak.db \
    PEAK_LAB_DATA=/opt/peak/lab \
    PEAK_WORDLIST=/opt/peak/wordlists/peak-mini.txt

HEALTHCHECK --interval=30s --timeout=4s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1

ENTRYPOINT ["/opt/peak/entrypoint.sh"]
