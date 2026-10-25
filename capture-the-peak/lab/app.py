"""
Capture the PEAK - SUMMIT RELAY (the deliberately-vulnerable lab service).

Hosts camps 06-09, 13 and 16. Runs on its own port (PEAK_LAB_PORT, default
9000) as an unprivileged user. It is INTENTIONALLY exploitable (SQLi, LFI,
command injection, SSTI, python sandbox escape). Run it ONLY inside the
container on an isolated event host. Flags for 6/7/13 are served from memory;
8/9/16 are written to /etc/peak/ so traversal, injection and the sandbox
escape have something real to reach.
"""
import os
import json
import base64
import sqlite3
import threading
import subprocess
from flask import Flask, request, Response, make_response, render_template_string
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

LAB_DATA = os.environ.get("PEAK_LAB_DATA", "/opt/peak/lab")
FLAG_DIR = os.environ.get("PEAK_FLAG_DIR", "/etc/peak")
LOG_DIR = os.environ.get("PEAK_LAB_LOGS", "/var/peak/lablogs")   # writable by the player user

FLAGS_FILE = os.path.join(LAB_DATA, "flags.json")
try:
    os.chmod(FLAGS_FILE, 0o600)   # we own it; ensure readable even if a prior run left it 000
except Exception:
    pass
with open(FLAGS_FILE) as fh:
    FLAGS = json.load(fh)   # {"6":..,"7":..,"8":..,"9":..}
# the served flags (6,7,13,18,20) now live only in this process's memory. hide the
# file from the read-only LFI once we've loaded it (an RCE camp could chmod it
# back, but the easy traversal path can't).
try:
    os.chmod(FLAGS_FILE, 0o000)
except Exception:
    pass

# on-disk flags for the file-read camps. flag8 is the LFI's intended target; 9 and
# 16 use non-obvious names so solving the LFI can't guess its way to them too.
ONDISK = {"8": "flag8", "9": ".diag_9f2a1c", "16": ".box_3d9e7b"}
os.makedirs(FLAG_DIR, exist_ok=True)
for k, nm in ONDISK.items():
    if k in FLAGS:
        try:
            open(os.path.join(FLAG_DIR, nm), "w").write(FLAGS[k] + "\n")
        except Exception:
            pass

FLAG16_PATH = os.path.join(FLAG_DIR, ONDISK["16"])
os.makedirs(LOG_DIR, exist_ok=True)
for name, txt in [("relay.log", "relay up. link nominal.\n" * 8),
                  ("auth.log", "login ok: ridge_ops\nlogin fail: guest\n" * 4)]:
    p = os.path.join(LOG_DIR, name)
    if not os.path.exists(p):
        open(p, "w").write(txt)

app = Flask(__name__)
# camp 13 (SSTI): the flag lives in the app config, reachable via {{ config.FLAG13 }}
app.config["FLAG13"] = FLAGS.get("13", "")

# in-memory users db for the SQLi camp
_dblock = threading.Lock()
_db = sqlite3.connect(":memory:", check_same_thread=False)
_db.execute("CREATE TABLE users(user TEXT, pass TEXT, role TEXT)")
_db.executemany("INSERT INTO users VALUES (?,?,?)", [
    ("admin", "S3cret-Relay-9k", "admin"),
    ("ridge_ops", "belay2026", "ops"),
    ("guest", "guest", "guest"),
])
# camp 20 (blind SQLi): the flag is a row in this table, never printed directly
_db.execute("CREATE TABLE vault(id INTEGER, note TEXT)")
_db.execute("INSERT INTO vault VALUES (1,?)", (FLAGS.get("20", ""),))
_db.execute("INSERT INTO vault VALUES (2,'relay log rotation nominal')")
_db.commit()

# camp 18 (AES-ECB byte-at-a-time): per-process key, secret = the flag
_ECB_KEY = os.urandom(16)
_ECB_SECRET = FLAGS.get("18", "").encode()

PAGE = """<!doctype html><meta charset=utf-8><title>SUMMIT RELAY</title>
<style>
 body{{background:#000;color:#d8d8df;font-family:ui-monospace,Menlo,Consolas,monospace;
   max-width:820px;margin:40px auto;padding:0 18px;line-height:1.55}}
 a{{color:#ff2a3a}} h1{{letter-spacing:.2em}} .m{{color:#8a8a97}}
 code{{color:#ff5a67;background:#0b0b0f;border:1px solid #17171c;padding:1px 5px}}
 .box{{border:1px solid #17171c;padding:16px;margin:14px 0}}
 input{{background:#050507;border:1px solid #45454f;color:#d8d8df;font-family:inherit;padding:8px}}
 .b{{display:inline-block;border:1px solid #ff2a3a;color:#ff2a3a;padding:7px 14px;text-decoration:none}}
 .ok{{color:#8b5cf6}} .flag{{color:#8b5cf6;font-size:17px;letter-spacing:.05em}}
</style>{body}"""


def page(body):
    return PAGE.format(body=body)


@app.route("/")
def home():
    return page("""<h1>SUMMIT <span style='color:#ff2a3a'>RELAY</span></h1>
<p class=m>status node for the ascent. four services exposed.</p>
<div class=box><b>/relay/panel</b> &middot; <span class=m>ops status panel (camp 06)</span></div>
<div class=box><b>/relay/login</b> &middot; <span class=m>operator sign-in (camp 07)</span></div>
<div class=box><b>/relay/logs?file=relay.log</b> &middot; <span class=m>log viewer (camp 08)</span></div>
<div class=box><b>/relay/diag?host=127.0.0.1</b> &middot; <span class=m>link diagnostics (camp 09)</span></div>
<div class=box><b>/relay/greet?name=climber</b> &middot; <span class=m>guest greeter (camp 13)</span></div>
<div class=box><b>/relay/sandbox?expr=2**10</b> &middot; <span class=m>expression sandbox (camp 16)</span></div>
<div class=box><b>/relay/vault?p=AAAA</b> &middot; <span class=m>sealing vault (camp 18)</span></div>
<div class=box><b>/relay/check?id=1</b> &middot; <span class=m>record lookup (camp 20)</span></div>
<p class=m>robots.txt is, of course, public.</p>""")


# ---- CAMP 06: robots + cookie role (IDOR-ish) -----------------------------
@app.route("/robots.txt")
def robots():
    return Response("User-agent: *\nDisallow: /relay/panel\n", mimetype="text/plain")


@app.route("/relay/panel")
def panel():
    raw = request.cookies.get("session", "")
    role = "guest"
    try:
        role = json.loads(base64.b64decode(raw).decode()).get("role", "guest")
    except Exception:
        role = "guest"
    if role == "admin":
        return page(f"<h1>OPS PANEL</h1><p class=m>welcome, admin.</p>"
                    f"<p>camp 06 flag:</p><p class=flag>{FLAGS['6']}</p>")
    sample = base64.b64encode(json.dumps({"user": "guest", "role": "guest"}).encode()).decode()
    resp = make_response(page(
        "<h1>OPS PANEL</h1><p class=m>403 &middot; guests cannot view the panel. "
        "the relay reads who you are from your <code>session</code> cookie ... "
        "base64 of a little JSON blob. we just set a fresh one for you. "
        "decode it, see what it says, and come back as someone else.</p>"), 403)
    resp.set_cookie("session", sample)
    return resp


# ---- CAMP 07: SQL injection auth bypass -----------------------------------
LOGIN_FORM = """<h1>OPERATOR SIGN-IN</h1>
<form method=post action=/relay/login>
<p><input name=user placeholder=user></p>
<p><input name=pass placeholder=pass type=password></p>
<p><button class=b>SIGN IN</button></p></form>
<p class=m>the query: <code>SELECT user,role FROM users WHERE user='$user' AND pass='$pass'</code></p>"""


@app.route("/relay/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return page(LOGIN_FORM)
    u = request.form.get("user", "")
    p = request.form.get("pass", "")
    q = "SELECT user,role FROM users WHERE user='%s' AND pass='%s'" % (u, p)
    try:
        with _dblock:
            row = _db.execute(q).fetchone()
    except Exception as e:
        return page(f"<h1>ERROR</h1><p class=m>sql error: {e}</p><p><a href=/relay/login>back</a></p>")
    if row:
        return page(f"<h1>DASHBOARD</h1><p class=ok>signed in as {row[0]} ({row[1]}).</p>"
                    f"<p>camp 07 flag:</p><p class=flag>{FLAGS['7']}</p>")
    return page("<h1>DENIED</h1><p class=m>no such operator.</p><p><a href=/relay/login>back</a></p>")


# ---- CAMP 08: LFI / path traversal ----------------------------------------
@app.route("/relay/logs")
def logs():
    f = request.args.get("file", "relay.log")
    try:
        with open(os.path.join(LOG_DIR, f)) as fh:   # intentionally unsanitised
            return Response(fh.read(), mimetype="text/plain")
    except Exception as e:
        return Response(f"cannot read {f}: {e}\n", mimetype="text/plain", status=404)


# ---- CAMP 09: OS command injection ----------------------------------------
@app.route("/relay/diag")
def diag():
    host = request.args.get("host", "127.0.0.1")
    cmd = "ping -c 1 -W 1 " + host     # intentionally shell-concatenated
    try:
        out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=8)
        return Response((out.stdout or "") + (out.stderr or ""), mimetype="text/plain")
    except Exception as e:
        return Response(f"diag failed: {e}\n", mimetype="text/plain", status=500)


# ---- CAMP 13: SSTI (Jinja2 template injection) ----------------------------
@app.route("/relay/greet")
def greet():
    name = request.args.get("name", "climber")
    # the name is handed straight to the template engine and rendered
    try:
        greeting = render_template_string("Hello, " + name + "!")   # SSTI here
    except Exception as e:
        greeting = f"(greeter error: {type(e).__name__})"
    body = ("<h1>GUEST GREETER</h1>"
            "<p class=m>sign the relay's guest log and it greets you back.</p>"
            f"<div class=box>{greeting}</div>"
            "<p class=m>sign with <code>?name=your-handle</code></p>")
    return page(body)


# ---- CAMP 16: python sandbox escape (eval, no builtins) --------------------
@app.route("/relay/sandbox")
def sandbox():
    expr = request.args.get("expr", "")
    if not expr:
        return page(
            "<h1>EXPRESSION SANDBOX</h1>"
            "<p class=m>a tiny python expression evaluator. built-ins are stripped.</p>"
            f"<p class=m>the summit key sits in <code>{FLAG16_PATH}</code> ... this "
            "evaluator can reach that file, but you cannot simply name it.</p>"
            "<div class=box>try <code>?expr=2**10</code></div>"
            "<p class=m>escape the box from the inside and read the key.</p>")
    try:
        result = eval(expr, {"__builtins__": {}}, {})   # intentionally escapable
        return page(f"<h1>SANDBOX</h1><div class=box>{str(result)[:4000]}</div>"
                    "<p class=m><a href=/relay/sandbox>back</a></p>")
    except Exception as e:
        return page(f"<h1>SANDBOX ERROR</h1><p class=m>{type(e).__name__}: {e}</p>"
                    "<p class=m><a href=/relay/sandbox>back</a></p>")


# ---- CAMP 18: AES-ECB byte-at-a-time oracle --------------------------------
@app.route("/relay/vault")
def vault():
    p = request.args.get("p", "")
    # seals  attacker_input + SECRET  under AES-ECB (ECB = the whole bug)
    data = p.encode("latin1", "ignore") + _ECB_SECRET
    ct = AES.new(_ECB_KEY, AES.MODE_ECB).encrypt(pad(data, 16))
    if request.args.get("raw") is not None or "p" in request.args:
        return Response(ct.hex() + "\n", mimetype="text/plain")
    return page("<h1>THE VAULT DOOR</h1><p class=m>the vault seals "
                "<code>your_input + MASTER_WORD</code> under AES-ECB and returns the hex.</p>"
                "<div class=box>try <code>?p=AAAA</code> and watch the blocks repeat.</div>")


# ---- CAMP 20: blind boolean SQL injection ----------------------------------
@app.route("/relay/check")
def check():
    rid = request.args.get("id", "")
    if rid == "":
        return page("<h1>SILENT LEDGER</h1><p class=m>record existence check. "
                    "answers only YES or NO.</p>"
                    "<div class=box>try <code>?id=1</code></div>"
                    "<p class=m>query: <code>SELECT note FROM vault WHERE id=$id</code></p>")
    q = "SELECT note FROM vault WHERE id=%s" % rid     # intentionally injectable
    try:
        with _dblock:
            row = _db.execute(q).fetchone()
    except Exception as e:
        return Response(f"query error: {e}\n", mimetype="text/plain", status=400)
    # boolean only ... never return the row contents
    return Response(("YES\n" if row else "NO\n"), mimetype="text/plain")


@app.route("/healthz")
def healthz():
    return "ok"


if __name__ == "__main__":
    port = int(os.environ.get("PEAK_LAB_PORT", "9000"))
    app.run(host="0.0.0.0", port=port, threaded=True)
