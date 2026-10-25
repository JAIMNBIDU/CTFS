"""
CAPTURE THE PEAK :: PRO RELAY (deliberately-vulnerable, invitation-only tier).

Hosts the three live PRO camps:
  1 THE LEAKING SEAL   - CBC padding oracle           (/pro/sealed, /pro/unseal)
  3 SHUFFLE THE BADGE  - AES-ECB cut-and-paste        (/pro/badge, /pro/enter)
  4 A KEY BY ANY NAME  - JWT RS256/HS256 confusion    (/pro/token, /pro/pubkey, /pro/vip)

Runs as the `relay` user inside the pro container. Flags are held only in this
process's memory (loaded from flags.json, which is then chmod'd away).
"""
import os
import json
import base64
import hmac
import hashlib
from flask import Flask, request, Response

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from Crypto.Random import get_random_bytes

LAB_DATA = os.environ.get("PEAK_LAB_DATA", "/opt/peak/lab")

FLAGS_FILE = os.path.join(LAB_DATA, "flags.json")
try:
    os.chmod(FLAGS_FILE, 0o600)
except Exception:
    pass
with open(FLAGS_FILE) as fh:
    FLAGS = json.load(fh)
try:
    os.chmod(FLAGS_FILE, 0o000)      # flags live in memory now; hide the file
except Exception:
    pass

# ---- camp 1: CBC padding oracle -------------------------------------------
_CBC_KEY = get_random_bytes(16)
_CBC_IV = get_random_bytes(16)
_SEALED = _CBC_IV + AES.new(_CBC_KEY, AES.MODE_CBC, _CBC_IV).encrypt(
    pad(FLAGS.get("1", "").encode(), 16))

# ---- camp 3: ECB cut-and-paste --------------------------------------------
_ECB_KEY = get_random_bytes(16)

# ---- camp 4: JWT RS256/HS256 confusion ------------------------------------
_RSA = RSA.generate(2048)
_PUB_PEM = _RSA.publickey().export_key()            # bytes, PEM


def _b64u(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=")


def _b64u_dec(s):
    s = s.encode() if isinstance(s, str) else s
    return base64.urlsafe_b64decode(s + b"=" * (-len(s) % 4))


def _jwt_rs256(payload):
    hdr = _b64u(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    pl = _b64u(json.dumps(payload).encode())
    signing = hdr + b"." + pl
    sig = pkcs1_15.new(_RSA).sign(SHA256.new(signing))
    return (signing + b"." + _b64u(sig)).decode()


app = Flask(__name__)

PAGE = """<!doctype html><meta charset=utf-8><title>PRO RELAY</title>
<style>body{{background:#000;color:#d8d8df;font-family:ui-monospace,Menlo,monospace;
max-width:820px;margin:40px auto;padding:0 18px;line-height:1.55}}
a{{color:#ff2a3a}} code{{color:#ff5a67;background:#0b0b0f;border:1px solid #17171c;padding:1px 5px}}
.box{{border:1px solid #17171c;padding:14px;margin:12px 0}} .flag{{color:#8b5cf6}}</style>{body}"""


def page(b):
    return PAGE.format(body=b)


@app.route("/")
def home():
    return page("<h1>PRO <span style='color:#ff2a3a'>RELAY</span></h1>"
                "<p>final-ascent services.</p>"
                "<div class=box><b>/pro/sealed</b> &middot; <b>/pro/unseal?c=HEX</b> (camp 1)</div>"
                "<div class=box><b>/pro/badge?user=NAME</b> &middot; <b>/pro/enter?badge=HEX</b> (camp 3)</div>"
                "<div class=box><b>/pro/token</b> &middot; <b>/pro/pubkey</b> &middot; <b>/pro/vip?token=JWT</b> (camp 4)</div>")


# ===== CAMP 1: CBC PADDING ORACLE ==========================================
@app.route("/pro/sealed")
def sealed():
    return Response(_SEALED.hex() + "\n", mimetype="text/plain")


@app.route("/pro/unseal")
def unseal():
    c = request.args.get("c", "")
    try:
        blob = bytes.fromhex(c)
        iv, ct = blob[:16], blob[16:]
        if len(ct) == 0 or len(ct) % 16 != 0:
            return Response("bad padding\n", mimetype="text/plain")
        pt = AES.new(_CBC_KEY, AES.MODE_CBC, iv).decrypt(ct)
        unpad(pt, 16)                       # raises on bad PKCS7 padding
        return Response("valid\n", mimetype="text/plain")
    except Exception:
        return Response("bad padding\n", mimetype="text/plain")


# ===== CAMP 3: AES-ECB CUT-AND-PASTE =======================================
@app.route("/pro/badge")
def badge():
    user = request.args.get("user", "")
    pt = ("user=" + user + "&role=guest").encode("latin1", "ignore")
    ct = AES.new(_ECB_KEY, AES.MODE_ECB).encrypt(pad(pt, 16))
    return Response(ct.hex() + "\n", mimetype="text/plain")


@app.route("/pro/enter")
def enter():
    h = request.args.get("badge", "")
    try:
        pt = unpad(AES.new(_ECB_KEY, AES.MODE_ECB).decrypt(bytes.fromhex(h)), 16)
        fields = dict(kv.split("=", 1) for kv in pt.decode("latin1").split("&") if "=" in kv)
        if fields.get("role") == "admin":
            return page(f"<h1>ADMIN</h1><p>badge accepted.</p><p class=flag>{FLAGS['3']}</p>")
        return page("<h1>DENIED</h1><p>guests may not enter.</p>")
    except Exception as e:
        return page(f"<h1>MALFORMED</h1><p>{type(e).__name__}</p>")


# ===== CAMP 4: JWT RS256/HS256 CONFUSION ===================================
@app.route("/pro/token")
def token():
    return Response(_jwt_rs256({"user": "climber", "role": "guest"}) + "\n",
                    mimetype="text/plain")


@app.route("/pro/pubkey")
def pubkey():
    return Response(_PUB_PEM, mimetype="text/plain")


@app.route("/pro/vip")
def vip():
    tok = request.args.get("token", "")
    try:
        h_b64, p_b64, s_b64 = tok.split(".")
        signing = (h_b64 + "." + p_b64).encode()
        header = json.loads(_b64u_dec(h_b64))
        payload = json.loads(_b64u_dec(p_b64))
        sig = _b64u_dec(s_b64)
        alg = header.get("alg")
        ok = False
        if alg == "RS256":
            try:
                pkcs1_15.new(_RSA.publickey()).verify(SHA256.new(signing), sig)
                ok = True
            except Exception:
                ok = False
        elif alg == "HS256":
            # the bug: verify HS256 using the PUBLIC key bytes as the secret
            expect = hmac.new(_PUB_PEM, signing, hashlib.sha256).digest()
            ok = hmac.compare_digest(expect, sig)
        if ok and payload.get("role") == "admin":
            return page(f"<h1>VIP</h1><p>welcome, admin.</p><p class=flag>{FLAGS['4']}</p>")
        return page("<h1>DENIED</h1><p>not an admin token.</p>")
    except Exception as e:
        return page(f"<h1>BAD TOKEN</h1><p>{type(e).__name__}</p>")


@app.route("/healthz")
def healthz():
    return "ok"


if __name__ == "__main__":
    port = int(os.environ.get("PEAK_LAB_PORT", "9000"))
    app.run(host="0.0.0.0", port=port, threaded=True)
