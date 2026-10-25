#!/bin/bash
# Capture the PEAK - launch the three services, each as its own unprivileged user:
#   ttyd  (player shell)      -> climber   (locked out of flag/hash/db stores)
#   relay (vulnerable lab)    -> relay      (owns the lab flags + /etc/peak)
#   portal (scoring server)   -> portal     (owns the hash store + the DB)
set -e
: "${PEAK_MODE:=board}"
export PEAK_MODE

# /var/peak is a mounted volume, so ownership is set at runtime (after the mount).
mkdir -p /var/peak/lablogs
chown portal:portal /var/peak 2>/dev/null || true
chown -R relay:relay /var/peak/lablogs 2>/dev/null || true
chmod 0711 /var/peak 2>/dev/null || true          # others may traverse, not list

echo "[peak] ======================================================"
echo "[peak]  CAPTURE THE PEAK  ::  mode = ${PEAK_MODE}"
echo "[peak]  portal  :8000     terminal :7681     relay :9000"
echo "[peak]  users: ttyd=climber  lab=relay  portal=portal (hardened)"
echo "[peak] ======================================================"

# in-browser shell for players, opened in their camps directory (climber)
runuser -u climber -- bash -lc 'cd /home/climber && ttyd -p 7681 -W bash' &

# deliberately-vulnerable lab relay (camps 06-09, 13, 16, 18, 20) as `relay`
runuser -u relay -- bash -lc 'PEAK_LAB_PORT=9000 python3 /opt/peak/lab/app.py' &

# portal (foreground; keeps the container alive, streams logs) as `portal`,
# umask 077 so the scores DB is created private
exec runuser -u portal -- bash -lc 'cd /opt/peak/server && umask 077 && PEAK_PORT=8000 python3 app.py'
