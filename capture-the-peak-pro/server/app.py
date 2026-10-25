"""
Capture the PEAK - portal.

Hosted, multi-team, scored CTF. One server; teams register a shared login,
race a 7-hour clock, and climb 12 stages across 5 categories. Two deployables
from one codebase: PEAK_MODE = board | linear.

Ships only salted SHA-256 hashes of flags/tokens, never plaintext.
"""
import os
import io
import json
import time
import datetime
import zipfile
import hashlib
import functools
import yaml
from flask import (Flask, render_template, request, jsonify, session,
                   redirect, url_for, send_file, abort)

import models
import rules

DATA_DIR = os.environ.get("PEAK_DATA", "/opt/peak/data")
CTF_DIR = os.environ.get("PEAK_CTF", "/ctf")
TTYD_PORT = os.environ.get("PEAK_TTYD_PORT", "7681")

# ---- load shipped config --------------------------------------------------
with open(os.path.join(DATA_DIR, "validation.json")) as fh:
    VALID = json.load(fh)
SALT = VALID["salt"]
FLAG_HASHES = VALID["flag_hashes"]          # {"1": hex, ...}

PROMPTS = yaml.safe_load(open(os.path.join(DATA_DIR, "prompts.yaml")))
HINTS = yaml.safe_load(open(os.path.join(DATA_DIR, "hints.yaml")))["hints"]
EVENT = yaml.safe_load(open(os.path.join(DATA_DIR, "event.yaml")))

STAGES = PROMPTS["stages"]
CATEGORIES = PROMPTS["categories"]
N_STAGES = len(STAGES)


def _env(key, default):
    return os.environ.get(key, default)


MODE = _env("PEAK_MODE", EVENT.get("mode", "board")).lower()
if MODE not in ("board", "linear"):
    MODE = "board"


def _end_epoch():
    """Single global deadline: everyone stops scoring at the same wall-clock time.
    Set PEAK_END_EPOCH (unix seconds) or PEAK_END (ISO, e.g.
    2026-10-24T16:00:00+05:30). 0 => never locks by time."""
    e = os.environ.get("PEAK_END_EPOCH") or EVENT.get("end_epoch")
    if e:
        try:
            return float(e)
        except Exception:
            pass
    s = os.environ.get("PEAK_END") or EVENT.get("end_time")
    if s:
        try:
            dt = datetime.datetime.fromisoformat(str(s))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return dt.timestamp()
        except Exception:
            pass
    return 0.0


END_EPOCH = _end_epoch()
FAST_SECS = int(_env("PEAK_FAST_SECS", EVENT.get("fast_solve_secs", 180)))
BURST_SECS = int(_env("PEAK_BURST_SECS", EVENT.get("burst_window_secs", 180)))
BURST_N = int(_env("PEAK_BURST_N", EVENT.get("burst_count", 3)))
LB_PUBLIC = str(_env("PEAK_LB_PUBLIC", EVENT.get("leaderboard_public", True))).lower() in ("1", "true", "yes")
REG_OPEN = str(_env("PEAK_REG_OPEN", EVENT.get("registration_open", True))).lower() in ("1", "true", "yes")
ADMIN_PASS = _env("PEAK_ADMIN_PASS", EVENT.get("admin_password", "change_me_peak_admin"))
ENTRY_KEY = _env("PEAK_ENTRY_KEY", EVENT.get("entry_key", ""))   # pro: unlock code to register
OOB = EVENT.get("oob", {})

# ---- app ------------------------------------------------------------------
app = Flask(__name__, static_folder="static", template_folder="templates")


def _secret():
    env = os.environ.get("PEAK_SECRET")
    if env:
        return env
    path = os.environ.get("PEAK_SECRET_FILE", "/var/peak/secret.key")
    try:
        if os.path.exists(path):
            return open(path).read().strip()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        s = os.urandom(24).hex()
        open(path, "w").write(s)
        return s
    except Exception:
        return "peak-dev-secret-change-me"


app.secret_key = _secret()
app.permanent_session_lifetime = datetime.timedelta(days=2)   # sticky logins
models.init_db()


def client_ip():
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.remote_addr or ""


def lab_base():
    """Base URL teams use to reach the vulnerable lab service."""
    override = os.environ.get("PEAK_LAB_URL")
    if override:
        return override.rstrip("/")
    host = request.host.split(":")[0]
    port = os.environ.get("PEAK_LAB_PORT", "9000")
    return f"http://{host}:{port}"


def _sha(v):
    return hashlib.sha256((SALT + v.strip()).encode()).hexdigest()


def is_frozen():
    return models.get_setting("frozen", "0") == "1"


def _extra(t):
    try:
        return t["extra_seconds"] or 0
    except Exception:
        return 0


# ---- session --------------------------------------------------------------
def current_team():
    tid = session.get("tid")
    if tid is None:
        return None
    return models.get_team(tid)


def login_required(fn):
    @functools.wraps(fn)
    def wrap(*a, **k):
        if current_team() is None:
            return redirect(url_for("landing"))
        return fn(*a, **k)
    return wrap


@app.context_processor
def _ctx():
    t = current_team()
    tl = rules.time_left(END_EPOCH)

    def get_hint_text(n, tier):
        try:
            return HINTS[int(n)][int(tier) - 1].replace("{LAB}", lab_base())
        except Exception:
            return ""

    return {
        "PROMPTS": PROMPTS, "CATEGORIES": CATEGORIES, "N_STAGES": N_STAGES,
        "MODE": MODE, "LB_PUBLIC": LB_PUBLIC, "team": t,
        "time_left": tl, "end_epoch": END_EPOCH,
        "title": PROMPTS["title"], "subtitle": PROMPTS["subtitle"],
        "tagline": PROMPTS.get("tagline", ""), "get_hint_text": get_hint_text,
    }


# ---- state helper ---------------------------------------------------------
def team_view(t):
    solves = models.team_solves(t["id"])
    hints = models.team_hints(t["id"])
    early = models.team_early(t["id"])
    solved_set = set(solves.keys())
    tl = rules.time_left(END_EPOCH)
    paused = bool(t["paused"]) if "paused" in t.keys() else False
    locked = rules.is_locked(END_EPOCH, is_frozen()) or paused
    banned = bool(t["banned"]) if "banned" in t.keys() else False
    score = sum(v["points"] for v in solves.values())
    stages = []
    for n in range(1, N_STAGES + 1):
        st = STAGES[n]
        base = st.get("points", 100)
        stages.append({
            "n": n, "name": st["name"], "category": st["category"],
            "points_base": base,
            "solved": n in solved_set,
            "earned": solves.get(n, {}).get("points"),
            "available": rules.available(n, MODE, solved_set, N_STAGES),
            "hint_tier": hints.get(n, 0),
            "worth_now": rules.stage_points(base, early.get(n, 0)),
        })
    return {"stages": stages, "score": score, "solves": len(solved_set),
            "time_left": tl, "locked": locked, "banned": banned, "paused": paused,
            "frozen": is_frozen(), "mode": MODE}


# ---- pages ----------------------------------------------------------------
@app.route("/")
def root_decoy():
    # the PRO tier has a secret entrance; the bare root gives nothing away
    from flask import Response
    return Response("not found\n", status=404, mimetype="text/plain")


@app.route("/onlyforpro")
def landing():
    if current_team() is not None:
        return redirect(url_for("play"))
    return render_template("landing.html", reg_open=REG_OPEN, require_key=bool(ENTRY_KEY))


@app.route("/register", methods=["POST"])
def register():
    if not REG_OPEN:
        return render_template("landing.html", reg_open=False, err="registration is closed",
                               require_key=bool(ENTRY_KEY))
    name = request.form.get("name", "")
    pw = request.form.get("passphrase", "")
    is_solo = request.form.get("mode_solo") == "1"
    if ENTRY_KEY and request.form.get("entry_key", "").strip() != ENTRY_KEY:
        return render_template("landing.html", reg_open=REG_OPEN, name=name,
                               require_key=True,
                               err="wrong unlock code ... clear all 20 and ask a marshal")
    tid, err = models.create_team(name, pw, is_solo)
    if err:
        return render_template("landing.html", reg_open=REG_OPEN, err=err, name=name,
                               require_key=bool(ENTRY_KEY))
    session.permanent = True
    session["tid"] = tid
    models.record_ip(tid, client_ip())
    return redirect(url_for("play"))


@app.route("/login", methods=["POST"])
def login():
    name = request.form.get("name", "")
    pw = request.form.get("passphrase", "")
    tid, err = models.auth_team(name, pw)
    if err:
        return render_template("landing.html", reg_open=REG_OPEN, login_err=err, name=name,
                               require_key=bool(ENTRY_KEY))
    session.permanent = True
    session["tid"] = tid
    models.record_ip(tid, client_ip())
    return redirect(url_for("play"))


@app.route("/logout")
def logout():
    # logout is disabled during the event: teams must not drop their session
    # and risk re-registering / losing their place. Kept as a no-op redirect.
    return redirect(url_for("play"))


@app.route("/play")
@login_required
def play():
    t = current_team()
    vs = team_view(t)
    tmpl = "linear.html" if MODE == "linear" else "board.html"
    return render_template(tmpl, vs=vs)


@app.route("/stage/<int:n>")
@login_required
def stage(n):
    if n < 1 or n > N_STAGES:
        abort(404)
    t = current_team()
    solves = models.team_solves(t["id"])
    solved_set = set(solves.keys())
    if not rules.available(n, MODE, solved_set, N_STAGES) and n not in solved_set:
        return redirect(url_for("play"))
    if n not in solved_set:
        models.record_open(t["id"], n)          # opening starts the hint clock (once)
    st = STAGES[n]
    base = st.get("points", 100)
    hint_tier = models.team_hints(t["id"]).get(n, 0)
    early = models.team_early(t["id"]).get(n, 0)
    opened = models.team_opens(t["id"]).get(n, 0)
    paused = bool(t["paused"]) if "paused" in t.keys() else False
    locked = rules.is_locked(END_EPOCH, is_frozen()) or paused
    hint_free_in = {tier: rules.hint_free_in(opened, tier) for tier in (1, 2, 3)}
    oob_info = None
    if OOB.get("enabled") and OOB.get("stage") == n:
        oob_info = {"number": OOB.get("number"), "keyword": OOB.get("keyword")}
    return render_template("stage.html", n=n, st=st,
                           solved=(n in solved_set),
                           earned=solves.get(n, {}).get("points"),
                           hint_tier=hint_tier, locked=locked,
                           worth_now=rules.stage_points(base, early),
                           hint_free_in=hint_free_in,
                           lab=lab_base(), oob=oob_info, ttyd_port=TTYD_PORT)


@app.route("/terminal")
@login_required
def terminal():
    return render_template("terminal.html", ttyd_port=TTYD_PORT)


@app.route("/leaderboard")
def leaderboard():
    if not LB_PUBLIC and current_team() is None:
        return redirect(url_for("landing"))
    lb = models.leaderboard()
    return render_template("leaderboard.html", lb=lb, now=time.time(),
                           end_epoch=END_EPOCH)


# ---- api ------------------------------------------------------------------
@app.route("/api/state")
@login_required
def api_state():
    return jsonify(team_view(current_team()))


@app.route("/api/submit", methods=["POST"])
@login_required
def api_submit():
    t = current_team()
    models.record_ip(t["id"], client_ip())
    if t["banned"]:
        return jsonify(ok=False, msg="your team has been disqualified. contact a marshal."), 403
    if "paused" in t.keys() and t["paused"]:
        return jsonify(ok=False, msg="your team is paused by a marshal. sit tight."), 403
    if is_frozen():
        return jsonify(ok=False, msg="the event is frozen by the marshals."), 403
    if rules.is_locked(END_EPOCH, is_frozen()):
        return jsonify(ok=False, msg="the event is over. the board is locked."), 403
    data = request.get_json(force=True, silent=True) or {}
    n = int(data.get("stage", 0))
    guess = (data.get("flag") or "").strip()
    if n < 1 or n > N_STAGES:
        return jsonify(ok=False, msg="no such stage"), 400
    solves = models.team_solves(t["id"])
    solved_set = set(solves.keys())
    if n in solved_set:
        return jsonify(ok=False, msg="already flagged")
    if not rules.available(n, MODE, solved_set, N_STAGES):
        return jsonify(ok=False, msg="locked ... solve the camp below it first"), 403
    if _sha(guess) != FLAG_HASHES[str(n)]:
        models.log_event(t["id"], "bad_flag", f"stage={n}")
        return jsonify(ok=False, msg="the mountain rejects that flag")
    base = STAGES[n].get("points", 100)
    early = models.team_early(t["id"]).get(n, 0)
    pts = rules.stage_points(base, early)
    models.record_solve(t["id"], n, pts)
    win = (len(solved_set) + 1) == N_STAGES
    return jsonify(ok=True, msg=f"camp taken ... +{pts}", points=pts, win=win)


@app.route("/api/hint", methods=["POST"])
@login_required
def api_hint():
    t = current_team()
    if t["banned"]:
        return jsonify(ok=False, msg="your team has been disqualified."), 403
    if "paused" in t.keys() and t["paused"]:
        return jsonify(ok=False, msg="your team is paused by a marshal."), 403
    data = request.get_json(force=True, silent=True) or {}
    n = int(data.get("stage", 0))
    tier = int(data.get("tier", 0))
    force = bool(data.get("force", False))
    if n not in HINTS or tier < 1 or tier > 3:
        return jsonify(ok=False), 400
    cur = models.team_hints(t["id"]).get(n, 0)
    base = STAGES[n].get("points", 100)
    lab = lab_base()
    # already revealed -> just hand it back, no change
    if tier <= cur:
        return jsonify(ok=True, tier=tier, text=HINTS[n][tier - 1].replace("{LAB}", lab),
                       early=False,
                       worth=rules.stage_points(base, models.team_early(t["id"]).get(n, 0)))
    if tier > cur + 1:
        return jsonify(ok=False, msg="reveal hints in order"), 400
    solved = n in models.team_solves(t["id"])
    opened = models.team_opens(t["id"]).get(n, 0)
    free = solved or rules.hint_is_free(opened, tier)
    if not free and not force:
        # on the clock still ... tell the client, let it offer "reveal now (-30%)"
        return jsonify(ok=False, locked=True,
                       free_in=rules.hint_free_in(opened, tier),
                       msg="this hint is still on the clock")
    is_early = (not free)
    if not solved:
        models.reveal_hint(t["id"], n, tier, is_early=is_early)
    new_early = models.team_early(t["id"]).get(n, 0)
    return jsonify(ok=True, tier=tier, text=HINTS[n][tier - 1].replace("{LAB}", lab),
                   early=is_early,
                   worth=(None if solved else rules.stage_points(base, new_early)))


@app.route("/download/<int:n>")
@login_required
def download(n):
    t = current_team()
    solves = models.team_solves(t["id"])
    if not rules.available(n, MODE, set(solves.keys()), N_STAGES) and n not in solves:
        abort(403)
    folder = os.path.join(CTF_DIR, f"stage{n:02d}")
    if not os.path.isdir(folder):
        abort(404)
    files = [f for f in sorted(os.listdir(folder)) if os.path.isfile(os.path.join(folder, f))]
    if not files:
        abort(404)
    if len(files) == 1:
        return send_file(os.path.join(folder, files[0]), as_attachment=True,
                         download_name=files[0])
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(os.path.join(folder, f), arcname=f)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name=f"stage{n:02d}.zip",
                     mimetype="application/zip")


# ---- admin ----------------------------------------------------------------
def admin_ok():
    return session.get("admin") is True


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASS:
            session["admin"] = True
            return redirect(url_for("admin_dash"))
        return render_template("admin_login.html", err="wrong password")
    if admin_ok():
        return redirect(url_for("admin_dash"))
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin"))


@app.route("/admin/dash")
def admin_dash():
    if not admin_ok():
        return redirect(url_for("admin"))
    now = time.time()
    teams = []
    for t in models.all_teams():
        solves = models.team_solves(t["id"])          # {stage: {points, epoch}}
        hints = models.team_hints(t["id"])
        opens = models.team_opens(t["id"])
        epochs = sorted(v["epoch"] for v in solves.values())
        # anti-cheat signal 1: camps solved faster than a human plausibly could
        fast = []
        for stg, v in solves.items():
            op = opens.get(stg)
            if op and (v["epoch"] - op) < FAST_SECS:
                fast.append((stg, int(v["epoch"] - op)))
        # signal 2: a burst of solves in a tight window
        burst = False
        for i in range(len(epochs)):
            c = sum(1 for e in epochs if epochs[i] <= e < epochs[i] + BURST_SECS)
            if c >= BURST_N:
                burst = True
                break
        flags = []
        if fast:
            flags.append(f"{len(fast)} solve(s) under {FAST_SECS}s")
        if burst:
            flags.append(f"{BURST_N}+ solves in {BURST_SECS}s")
        teams.append({
            "id": t["id"], "name": t["name"], "is_solo": bool(t["is_solo"]),
            "banned": bool(t["banned"]) if "banned" in t.keys() else False,
            "paused": bool(t["paused"]) if "paused" in t.keys() else False,
            "score": sum(v["points"] for v in solves.values()),
            "solves": sorted(solves.keys()), "hints": hints,
            "fast": sorted(fast, key=lambda x: x[1]), "flags": flags,
            "suspect": bool(flags),
        })
    teams.sort(key=lambda x: (-int(x["suspect"]), -x["score"]))   # suspects float up
    shared = models.shared_ips()
    events = models.recent_events(250)
    return render_template("admin_dash.html", teams=teams, events=events,
                           now=now, mode=MODE, end_epoch=END_EPOCH,
                           n_stages=N_STAGES, frozen=is_frozen(),
                           shared_ips=shared, fast_secs=FAST_SECS)


@app.route("/admin/freeze", methods=["POST"])
def admin_freeze():
    if not admin_ok():
        abort(403)
    models.set_setting("frozen", "0" if is_frozen() else "1")
    models.log_event(None, "admin", "event frozen" if is_frozen() else "event resumed")
    return redirect(url_for("admin_dash"))


@app.route("/admin/team/<int:tid>/ban", methods=["POST"])
def admin_ban(tid):
    if not admin_ok():
        abort(403)
    t = models.get_team(tid)
    if t:
        models.set_ban(tid, not bool(t["banned"]))
    return redirect(url_for("admin_dash"))


@app.route("/admin/team/<int:tid>/pause", methods=["POST"])
def admin_pause(tid):
    if not admin_ok():
        abort(403)
    t = models.get_team(tid)
    if t:
        cur = bool(t["paused"]) if "paused" in t.keys() else False
        models.set_pause(tid, not cur)
    return redirect(url_for("admin_dash"))


@app.route("/admin/team/<int:tid>/extend", methods=["POST"])
def admin_extend(tid):
    if not admin_ok():
        abort(403)
    mins = int(request.form.get("mins", 30))
    models.add_extra(tid, mins * 60)
    return redirect(url_for("admin_dash"))


@app.route("/healthz")
def healthz():
    return "ok"


if __name__ == "__main__":
    port = int(os.environ.get("PEAK_PORT", "8000"))
    app.run(host="0.0.0.0", port=port, threaded=True)
