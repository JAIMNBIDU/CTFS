"""
CAPTURE THE PEAK :: PRO - build-time self-test. Solves all five pro camps from
the generated artifacts / live relay and checks each recovers the real flag.
Exits non-zero on any mismatch.
"""
import os
import re
import sys
import json
import time
import base64
import hmac
import hashlib
import math
import subprocess
import urllib.request
import urllib.parse
from pathlib import Path

import warnings
import yaml
warnings.filterwarnings("ignore")

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "_build"
ROOT = Path(__file__).resolve().parent.parent
FLAGS = {int(k): v for k, v in yaml.safe_load(open(ROOT / "config" / "flags.yaml"))["flags"].items()}
CTF = OUT / "ctf"
fails = []


def check(n, got, want=None, note=""):
    want = FLAGS[n] if want is None else want
    ok = (got == want)
    print(f"  pro {n}  {'PASS' if ok else 'FAIL':4}  {note}")
    if not ok:
        fails.append((n, got, want))


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


# ---- 2 RSA (Fermat) -------------------------------------------------------
def s02():
    from Crypto.Util.number import long_to_bytes, inverse
    txt = (CTF / "stage02" / "rsa.txt").read_text()
    n = int(re.search(r"n = (\d+)", txt).group(1))
    e = int(re.search(r"e = (\d+)", txt).group(1))
    c = int(re.search(r"c = (\d+)", txt).group(1))
    a = math.isqrt(n)
    if a * a < n:
        a += 1
    while True:
        b2 = a * a - n
        b = math.isqrt(b2)
        if b * b == b2:
            break
        a += 1
    p, q = a + b, a - b
    d = inverse(e, (p - 1) * (q - 1))
    m = pow(c, d, n)
    check(2, long_to_bytes(m).decode("latin1"), note="rsa fermat factor + decrypt")


# ---- 5 VM crackme ---------------------------------------------------------
def s05():
    serial = "PR0_V4ULT_K3Y_99"
    b = CTF / "stage05" / "vault_vm"
    got = run([str(b), serial]).stdout.strip()
    st = run(["strings", str(b)]).stdout
    leaked = (FLAGS[5] in st) or (serial in st)
    check(5, got, note=f"vm keygen reverse (strings-clean={not leaked})")
    if leaked:
        fails.append((5, "flag/serial in strings", "clean binary"))


# ---- 1,3,4 live on the pro relay ------------------------------------------
def _b64u(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=")


def lab_suite():
    env = dict(os.environ)
    env.update({"PEAK_LAB_DATA": str(OUT / "lab"), "PEAK_LAB_PORT": "9199"})
    proc = subprocess.Popen([sys.executable, str(ROOT / "lab" / "app.py")], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = "http://127.0.0.1:9199"

    def get(path):
        return urllib.request.urlopen(base + path, timeout=8).read()

    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(base + "/healthz", timeout=1); break
            except Exception:
                time.sleep(0.25)

        # --- camp 1: CBC padding oracle ---
        blob = bytes.fromhex(get("/pro/sealed").decode().strip())
        blocks = [blob[i:i + 16] for i in range(0, len(blob), 16)]

        def oracle(two):
            return get("/pro/unseal?c=" + two.hex()).decode().strip() == "valid"

        def recover(cur):
            inter = bytearray(16)
            for k in range(1, 17):
                pos = 16 - k
                forged = bytearray(16)
                for j in range(pos + 1, 16):
                    forged[j] = inter[j] ^ k
                for g in range(256):
                    forged[pos] = g
                    if oracle(bytes(forged) + cur):
                        if k == 1:
                            t = bytearray(forged); t[pos - 1] ^= 0xFF
                            if not oracle(bytes(t) + cur):
                                continue
                        inter[pos] = g ^ k
                        break
            return bytes(inter)

        pt = b""
        for bi in range(1, len(blocks)):
            inter = recover(blocks[bi])
            pt += bytes(a ^ b for a, b in zip(inter, blocks[bi - 1]))
        padn = pt[-1]
        check(1, pt[:-padn].decode("latin1"), note="cbc padding oracle")

        # --- camp 3: ECB cut-and-paste ---
        admin_name = "A" * 11 + "admin" + chr(11) * 11
        ct1 = bytes.fromhex(get("/pro/badge?user=" + urllib.parse.quote(admin_name, safe="")).decode().strip())
        admin_block = ct1[16:32]
        ct2 = bytes.fromhex(get("/pro/badge?user=AAAAA").decode().strip())
        forged = ct2[:16] + admin_block
        b3 = get("/pro/enter?badge=" + forged.hex()).decode()
        m = re.search(r"acqu1redP34k\{[^}]+\}", b3)
        check(3, m.group(0) if m else "", note="ecb cut-and-paste")

        # --- camp 4: JWT RS256/HS256 confusion ---
        pem = get("/pro/pubkey")
        hdr = _b64u(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        pl = _b64u(json.dumps({"role": "admin"}).encode())
        signing = hdr + b"." + pl
        sig = _b64u(hmac.new(pem, signing, hashlib.sha256).digest())
        tok = (signing + b"." + sig).decode()
        b4 = get("/pro/vip?token=" + urllib.parse.quote(tok, safe="")).decode()
        m = re.search(r"acqu1redP34k\{[^}]+\}", b4)
        check(4, m.group(0) if m else "", note="jwt rs256->hs256 confusion")
    finally:
        proc.terminate()


def main():
    print("== Capture the PEAK :: PRO :: build self-test ==")
    s02(); s05(); lab_suite()
    if fails:
        print(f"\nFAILED pro camps: {[f[0] for f in fails]}")
        for n, got, want in fails:
            print(f"  pro {n}: got {got!r} want {want!r}")
        sys.exit(1)
    print("\nALL PRO CAMPS VERIFIED. green build.")


if __name__ == "__main__":
    main()
