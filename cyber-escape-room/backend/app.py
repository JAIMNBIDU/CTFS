"""
CYBER ESCAPE ROOM // backend
FastAPI + SQLite. Single-file app. Serves the three dashboards + API.

Run (dev):   uvicorn app:app --host 0.0.0.0 --port 8000
Run (prod):  see DEPLOY_AZURE.md  (systemd + uvicorn, or gunicorn -k uvicorn.workers)

Env vars:
  CER_ADMIN_PASSWORD   admin panel password          (default: changeme_admin)
  CER_DURATION_MIN     event duration in minutes      (default: 120)
  CER_EXTEND_MIN       minutes added per admin extend  (default: 30)
  CER_DB               sqlite path                     (default: ./cer.db)
  CER_SECRET           cookie-signing salt             (default: dev_secret)
"""
import os, sqlite3, secrets, time, hashlib, random, string, json
from pathlib import Path
from contextlib import contextmanager

from fastapi import FastAPI, Request, Response, HTTPException, Form, Cookie
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

import challenges as CH

# ----------------------------------------------------------------------------- config
HERE          = Path(__file__).resolve().parent
ROOT          = HERE.parent
FRONTEND      = ROOT / "frontend"
ASSET_DIR     = ROOT / "challenges"
ADMIN_PW      = os.environ.get("CER_ADMIN_PASSWORD", "changeme_admin")
DURATION_SEC  = int(os.environ.get("CER_DURATION_MIN", "120")) * 60
EXTEND_SEC    = int(os.environ.get("CER_EXTEND_MIN", "30")) * 60
DB_PATH       = os.environ.get("CER_DB", str(ROOT / "cer.db"))
SECRET        = os.environ.get("CER_SECRET", "dev_secret")

# Fixed scrambled 6x6 lookup grid (A-Z + 0-9, each once). Printed copies go on the
# physical doors. Deterministic scramble so the server and the printed sheet always match.
_base = list(string.ascii_uppercase + string.digits)   # 36 chars, all unique
random.Random(1337).shuffle(_base)                       # deterministic
GRID = "".join(_base)                                    # 36 chars, six rows of six

def grid_rows():
    return [GRID[i*6:(i+1)*6] for i in range(6)]

def word_to_coords(word: str):
    """Return list of (row,col) 1-indexed for each letter of word on GRID."""
    coords = []
    for ch in word.upper():
        idx = GRID.index(ch)
        coords.append((idx // 6 + 1, idx % 6 + 1))
    return coords

def coords_str(coords):
    return " ".join(f"{r},{c}" for r, c in coords)

# ----------------------------------------------------------------------------- db
def connect():
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA busy_timeout=5000;")
    return con

@contextmanager
def db():
    con = connect()
    try:
        yield con
        con.commit()
    finally:
        con.close()

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS teams(
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT UNIQUE NOT NULL,
            code        TEXT UNIQUE NOT NULL,
            mode        TEXT NOT NULL,            -- 'single' | 'team'
            stage       INTEGER NOT NULL DEFAULT 1,   -- next stage to solve (1..7), 8 = escape prompt
            escaped     INTEGER NOT NULL DEFAULT 0,
            started     INTEGER NOT NULL DEFAULT 0,
            start_ts    REAL,
            extra_sec   INTEGER NOT NULL DEFAULT 0,
            frozen      INTEGER NOT NULL DEFAULT 0,
            finished_ts REAL,
            created_ts  REAL NOT NULL,
            phys1_word  TEXT, phys1_coords TEXT,
            phys2_word  TEXT, phys2_coords TEXT
        );
        CREATE TABLE IF NOT EXISTS players(
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id  INTEGER NOT NULL,
            handle   TEXT NOT NULL,
            token    TEXT UNIQUE NOT NULL,
            created_ts REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS solves(
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id  INTEGER NOT NULL,
            stage    INTEGER NOT NULL,
            ts       REAL NOT NULL,
            skipped  INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS events(      -- audit log for admin
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL NOT NULL, team_id INTEGER, kind TEXT, detail TEXT
        );
        """)

def log(con, kind, team_id=None, detail=""):
    con.execute("INSERT INTO events(ts,team_id,kind,detail) VALUES(?,?,?,?)",
                (time.time(), team_id, kind, detail))

# ----------------------------------------------------------------------------- helpers
def new_code():
    return "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))

def new_token():
    return secrets.token_urlsafe(24)

def assign_physical_words(con):
    """Pick two distinct words from pool for the two physical stages, compute coords."""
    used1 = {r[0] for r in con.execute("SELECT phys1_word FROM teams WHERE phys1_word IS NOT NULL")}
    used2 = {r[0] for r in con.execute("SELECT phys2_word FROM teams WHERE phys2_word IS NOT NULL")}
    pool = CH.PHYSICAL_WORD_POOL[:]
    random.shuffle(pool)
    w1 = next((w for w in pool if w not in used1), random.choice(CH.PHYSICAL_WORD_POOL))
    w2 = next((w for w in pool if w not in used2 and w != w1), random.choice([x for x in CH.PHYSICAL_WORD_POOL if x != w1]))
    return (w1, coords_str(word_to_coords(w1)), w2, coords_str(word_to_coords(w2)))

def team_by_token(con, token):
    if not token:
        return None
    row = con.execute(
        "SELECT t.* FROM teams t JOIN players p ON p.team_id=t.id WHERE p.token=?",
        (token,)).fetchone()
    return row

def duration_for(team):
    return DURATION_SEC + (team["extra_sec"] or 0)

def time_left(team):
    if not team["started"] or not team["start_ts"]:
        return duration_for(team)
    left = duration_for(team) - (time.time() - team["start_ts"])
    return max(0, int(left))

def is_time_up(team):
    return team["started"] and time_left(team) <= 0

def solved_count(con, team_id):
    return con.execute("SELECT COUNT(*) FROM solves WHERE team_id=?", (team_id,)).fetchone()[0]

def flag_match(submitted, expected):
    return submitted.strip().lower() == expected.strip().lower()

# ----------------------------------------------------------------------------- app
app = FastAPI(title="Cyber Escape Room")
init_db()

@app.get("/", response_class=HTMLResponse)
def home():
    return FileResponse(FRONTEND / "index.html")

@app.get("/dashboard", response_class=HTMLResponse)
def dash():
    return FileResponse(FRONTEND / "dashboard.html")

@app.get("/leaderboard", response_class=HTMLResponse)
def board_page():
    return FileResponse(FRONTEND / "leaderboard.html")

@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    return FileResponse(FRONTEND / "admin.html")

app.mount("/static", StaticFiles(directory=str(FRONTEND / "static")), name="static")

# ----------------------------------------------------------------- registration / auth
@app.post("/api/register")
def register(name: str = Form(...), handle: str = Form(...), mode: str = Form(...)):
    name = name.strip()
    handle = handle.strip() or "player"
    if mode not in ("single", "team"):
        raise HTTPException(400, "mode must be single or team")
    if not name or len(name) > 40:
        raise HTTPException(400, "team/player name required (<=40 chars)")
    with db() as con:
        if con.execute("SELECT 1 FROM teams WHERE name=?", (name,)).fetchone():
            raise HTTPException(409, "that name is taken")
        code = new_code()
        while con.execute("SELECT 1 FROM teams WHERE code=?", (code,)).fetchone():
            code = new_code()
        w1, c1, w2, c2 = assign_physical_words(con)
        cur = con.execute(
            """INSERT INTO teams(name,code,mode,created_ts,phys1_word,phys1_coords,phys2_word,phys2_coords)
               VALUES(?,?,?,?,?,?,?,?)""",
            (name, code, mode, time.time(), w1, c1, w2, c2))
        team_id = cur.lastrowid
        token = new_token()
        con.execute("INSERT INTO players(team_id,handle,token,created_ts) VALUES(?,?,?,?)",
                    (team_id, handle, token, time.time()))
        log(con, "register", team_id, f"{mode} '{name}' by {handle}")
    resp = JSONResponse({"ok": True, "team": name, "code": code, "mode": mode})
    resp.set_cookie("token", token, httponly=True, samesite="lax", max_age=60*60*12)
    return resp

@app.post("/api/join")
def join(code: str = Form(...), handle: str = Form(...)):
    code = code.strip().upper()
    handle = handle.strip() or "player"
    with db() as con:
        team = con.execute("SELECT * FROM teams WHERE code=?", (code,)).fetchone()
        if not team:
            raise HTTPException(404, "no team with that code")
        if team["mode"] == "single":
            raise HTTPException(403, "that is a single-player entry, can't join")
        token = new_token()
        con.execute("INSERT INTO players(team_id,handle,token,created_ts) VALUES(?,?,?,?)",
                    (team["id"], handle, token, time.time()))
        log(con, "join", team["id"], f"{handle} joined")
    resp = JSONResponse({"ok": True, "team": team["name"], "code": code})
    resp.set_cookie("token", token, httponly=True, samesite="lax", max_age=60*60*12)
    return resp

@app.post("/api/start")
def start(token: str = Cookie(default=None)):
    with db() as con:
        team = team_by_token(con, token)
        if not team:
            raise HTTPException(401, "not logged in")
        if not team["started"]:
            con.execute("UPDATE teams SET started=1, start_ts=? WHERE id=?",
                        (time.time(), team["id"]))
            log(con, "start", team["id"], "clock started")
    return {"ok": True}

@app.post("/api/logout")
def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("token")
    return resp

# ----------------------------------------------------------------- participant state
def build_stage_view(con, team):
    """Return the current stage payload for the team (brief + unlocked hints + coords)."""
    stage = team["stage"]
    if team["escaped"]:
        return {"escaped": True}
    if stage > CH.TOTAL_STAGES:
        # at the final passphrase prompt
        return {
            "final": True,
            "title": "FINAL // ESCAPE",
            "brief": ("You have every digital word. Assemble the master passphrase: the five "
                      "digital stage words (stages 1,2,4,5,7) in order, joined by underscores. "
                      "Enter it to escape."),
        }
    s = CH.STAGES[stage]
    # elapsed minutes on THIS stage
    last_solve = con.execute(
        "SELECT MAX(ts) FROM solves WHERE team_id=?", (team["id"],)).fetchone()[0]
    stage_entered = last_solve or team["start_ts"] or time.time()
    mins_on_stage = (time.time() - stage_entered) / 60.0 if team["started"] else 0
    hints = [h["text"] for h in s.get("hints", []) if mins_on_stage >= h["after_min"]]
    next_hint_in = None
    for h in s.get("hints", []):
        if mins_on_stage < h["after_min"]:
            next_hint_in = int(h["after_min"] - mins_on_stage) + 1
            break
    view = {
        "stage": stage, "total": CH.TOTAL_STAGES,
        "title": s["title"], "category": s["category"], "type": s["type"],
        "brief": s["brief"],
        "hints": hints, "next_hint_in_min": next_hint_in,
        "has_asset": bool(s.get("asset")),
        "endpoint": s.get("endpoint"),
    }
    if s["type"] == "physical":
        if stage == CH.PHYSICAL_STAGES[0]:
            view["coords"] = team["phys1_coords"]
            view["location"] = "STAFF ROOM DOOR"
        else:
            view["coords"] = team["phys2_coords"]
            view["location"] = "SECOND ROOM (named in previous stage's output)"
    return view

@app.get("/api/state")
def state(token: str = Cookie(default=None)):
    with db() as con:
        team = team_by_token(con, token)
        if not team:
            raise HTTPException(401, "not logged in")
        sc = solved_count(con, team["id"])
        status = "active"
        if team["escaped"]:        status = "escaped"
        elif team["frozen"]:       status = "frozen"
        elif is_time_up(team):     status = "time_up"
        elif not team["started"]:  status = "ready"
        payload = {
            "team": team["name"], "code": team["code"], "mode": team["mode"],
            "started": bool(team["started"]),
            "status": status,
            "time_left": time_left(team),
            "duration": duration_for(team),
            "solved": sc,
            "total": CH.TOTAL_STAGES,
            "current": build_stage_view(con, team),
        }
    return payload

@app.post("/api/submit")
def submit(flag: str = Form(...), token: str = Cookie(default=None)):
    flag = flag.strip()
    with db() as con:
        team = team_by_token(con, token)
        if not team:
            raise HTTPException(401, "not logged in")
        if team["escaped"]:
            return {"ok": False, "msg": "You already escaped."}
        if team["frozen"]:
            return {"ok": False, "msg": "Your team is FROZEN by control. Call a proctor."}
        if not team["started"]:
            return {"ok": False, "msg": "Hit START MISSION first."}
        if is_time_up(team):
            return {"ok": False, "msg": "Time is up. Submissions locked."}

        stage = team["stage"]

        # Final passphrase gate
        if stage > CH.TOTAL_STAGES:
            if CH.normalise(flag) == CH.normalise(CH.FINAL_PASSPHRASE):
                con.execute("UPDATE teams SET escaped=1, finished_ts=? WHERE id=?",
                            (time.time(), team["id"]))
                log(con, "escape", team["id"], "ESCAPED")
                return {"ok": True, "escaped": True, "msg": "SYSTEM BREACHED. YOU ARE OUT."}
            return {"ok": False, "msg": "Wrong passphrase. Re-check the five words and their order."}

        s = CH.STAGES[stage]
        # expected flag: physical stages are per-team
        if s["type"] == "physical":
            word = team["phys1_word"] if stage == CH.PHYSICAL_STAGES[0] else team["phys2_word"]
            expected = f"CYBER_ESCAPE_ROOM{{{word.lower()}}}"
        else:
            expected = s["flag"]

        if flag_match(flag, expected):
            con.execute("INSERT INTO solves(team_id,stage,ts) VALUES(?,?,?)",
                        (team["id"], stage, time.time()))
            con.execute("UPDATE teams SET stage=stage+1 WHERE id=?", (team["id"],))
            log(con, "solve", team["id"], f"stage {stage}")
            nxt = "final passphrase prompt" if stage == CH.TOTAL_STAGES else f"stage {stage+1}"
            return {"ok": True, "msg": f"CORRECT. Advancing to {nxt}.", "advanced": True}
        return {"ok": False, "msg": "Rejected. That is not the flag for this stage."}

# ----------------------------------------------------------------- gated asset download
@app.get("/api/asset/{stage}")
def asset(stage: int, token: str = Cookie(default=None)):
    with db() as con:
        team = team_by_token(con, token)
        if not team:
            raise HTTPException(401, "not logged in")
        if stage > team["stage"]:
            raise HTTPException(403, "locked")   # can't fetch future stage files
    s = CH.STAGES.get(stage)
    if not s or not s.get("asset"):
        raise HTTPException(404, "no asset")
    fp = ASSET_DIR / s["asset"]
    if not fp.exists():
        raise HTTPException(404, "asset missing on server")
    return FileResponse(fp, filename=s["asset"])

# ----------------------------------------------------------------- SQL-injection vault
# Deliberately vulnerable. Runs against an ISOLATED in-memory db so real injection
# payloads work but cannot touch the real cer.db.
@app.post("/api/vault")
def vault(username: str = Form(...), password: str = Form(...), token: str = Cookie(default=None)):
    with db() as con:
        team = team_by_token(con, token)
        if not team:
            raise HTTPException(401, "not logged in")
        if team["stage"] != 6:
            return {"ok": False, "msg": "The vault is not your current objective."}
    # isolated sandbox
    sb = sqlite3.connect(":memory:")
    sb.execute("CREATE TABLE vault(username TEXT, password TEXT, secret TEXT)")
    sb.execute("INSERT INTO vault VALUES('root','S3cr3t-N3v3r-Gu3ss','locked')")
    # VULNERABLE: string-concatenated query (this is the whole point of the stage)
    q = ("SELECT username FROM vault WHERE username='%s' AND password='%s'"
         % (username, password))
    try:
        rows = sb.execute(q).fetchall()
    except Exception as e:
        return {"ok": False, "msg": f"SQL error: {e}", "query": q}
    finally:
        sb.close()
    if rows:
        return {"ok": True,
                "msg": "ACCESS GRANTED. Vault open.",
                "flag": CH.STAGES[6]["flag"],
                "note": "Submit this flag in your Stage 6 box.",
                "query": q}
    return {"ok": False, "msg": "Access denied. Those credentials failed.", "query": q}

# ----------------------------------------------------------------- Sanctum (cookie tamper)
# Stage 9. The server trusts a client-side 'clearance' cookie. Classic broken access control.
@app.get("/api/sanctum")
def sanctum(request: Request, token: str = Cookie(default=None)):
    with db() as con:
        team = team_by_token(con, token)
        if not team:
            raise HTTPException(401, "not logged in")
        if team["stage"] != 9:
            return JSONResponse({"ok": False, "msg": "The sanctum is not your current objective."})
    clearance = request.cookies.get("clearance")
    if clearance is None:
        # first knock: issue the initiate badge so there is something to forge
        resp = JSONResponse({"ok": False, "clearance": "initiate",
                             "msg": "The guard stamps your badge: INITIATE. Only OVERSEER may enter. Come back when you are more than you are."})
        resp.set_cookie("clearance", "initiate", httponly=False, samesite="lax", max_age=60*60*12)
        return resp
    if clearance.strip().lower() == CH.SANCTUM_REQUIRED:
        return JSONResponse({"ok": True, "clearance": clearance,
                             "msg": "The guard steps aside. You walk into the sanctum.",
                             "flag": CH.STAGES[9]["flag"],
                             "note": "Submit this flag in your Stage 9 box."})
    return JSONResponse({"ok": False, "clearance": clearance,
                         "msg": f"Badge reads '{clearance}'. The guard does not move. OVERSEER only."})

# ----------------------------------------------------------------- leaderboard (public)
@app.get("/api/leaderboard")
def leaderboard():
    with db() as con:
        teams = con.execute("SELECT * FROM teams").fetchall()
        rows = []
        for t in teams:
            sc = solved_count(con, t["id"])
            last = con.execute("SELECT MAX(ts) FROM solves WHERE team_id=?", (t["id"],)).fetchone()[0]
            rows.append({
                "name": t["name"], "mode": t["mode"],
                "solved": sc, "total": CH.TOTAL_STAGES,
                "escaped": bool(t["escaped"]),
                "finished_ts": t["finished_ts"],
                "last_ts": last or t["start_ts"] or t["created_ts"],
                "frozen": bool(t["frozen"]),
                "started": bool(t["started"]),
            })
    def sort_key(r):
        # escaped first (by finish time), then by solved desc, then earliest last-solve
        return (
            0 if r["escaped"] else 1,
            r["finished_ts"] if r["escaped"] else float("inf"),
            -r["solved"],
            r["last_ts"],
        )
    rows.sort(key=sort_key)
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return {"updated": time.time(), "teams": rows}

# ----------------------------------------------------------------- admin
def check_admin(admin: str):
    if admin != ADMIN_PW:
        raise HTTPException(401, "bad admin password")

@app.post("/api/admin/login")
def admin_login(password: str = Form(...)):
    check_admin(password)
    resp = JSONResponse({"ok": True})
    # cookie value = hash(secret+pw) so we don't store raw pw in cookie
    tok = hashlib.sha256((SECRET + password).encode()).hexdigest()
    resp.set_cookie("admin", tok, httponly=True, samesite="lax", max_age=60*60*12)
    return resp

def require_admin(admin_cookie):
    expected = hashlib.sha256((SECRET + ADMIN_PW).encode()).hexdigest()
    if admin_cookie != expected:
        raise HTTPException(401, "admin auth required")

@app.get("/api/admin/teams")
def admin_teams(admin: str = Cookie(default=None)):
    require_admin(admin)
    with db() as con:
        teams = con.execute("SELECT * FROM teams ORDER BY id").fetchall()
        out = []
        for t in teams:
            sc = solved_count(con, t["id"])
            players = [r["handle"] for r in con.execute(
                "SELECT handle FROM players WHERE team_id=? ORDER BY id", (t["id"],))]
            solves = con.execute(
                "SELECT stage,skipped,ts FROM solves WHERE team_id=? ORDER BY stage", (t["id"],)).fetchall()
            status = ("escaped" if t["escaped"] else "frozen" if t["frozen"]
                      else "time_up" if is_time_up(t) else "active" if t["started"] else "ready")
            out.append({
                "id": t["id"], "name": t["name"], "code": t["code"], "mode": t["mode"],
                "players": players,
                "stage": t["stage"], "solved": sc, "total": CH.TOTAL_STAGES,
                "status": status, "escaped": bool(t["escaped"]),
                "time_left": time_left(t), "extra_sec": t["extra_sec"],
                "started": bool(t["started"]),
                "solve_stages": [{"stage": s["stage"], "skipped": bool(s["skipped"])} for s in solves],
                "phys1": t["phys1_word"], "phys2": t["phys2_word"],
            })
    return {"updated": time.time(), "duration_min": DURATION_SEC // 60,
            "extend_min": EXTEND_SEC // 60, "teams": out}

def _get_team(con, team_id):
    t = con.execute("SELECT * FROM teams WHERE id=?", (team_id,)).fetchone()
    if not t:
        raise HTTPException(404, "no such team")
    return t

@app.post("/api/admin/freeze")
def admin_freeze(team_id: int = Form(...), admin: str = Cookie(default=None)):
    require_admin(admin)
    with db() as con:
        _get_team(con, team_id)
        con.execute("UPDATE teams SET frozen=1 WHERE id=?", (team_id,))
        log(con, "admin_freeze", team_id, "STOPPED by admin")
    return {"ok": True}

@app.post("/api/admin/unfreeze")
def admin_unfreeze(team_id: int = Form(...), admin: str = Cookie(default=None)):
    require_admin(admin)
    with db() as con:
        _get_team(con, team_id)
        con.execute("UPDATE teams SET frozen=0 WHERE id=?", (team_id,))
        log(con, "admin_unfreeze", team_id, "resumed")
    return {"ok": True}

@app.post("/api/admin/extend")
def admin_extend(team_id: int = Form(...), admin: str = Cookie(default=None)):
    require_admin(admin)
    with db() as con:
        _get_team(con, team_id)
        con.execute("UPDATE teams SET extra_sec=extra_sec+? WHERE id=?", (EXTEND_SEC, team_id))
        log(con, "admin_extend", team_id, f"+{EXTEND_SEC//60}m")
    return {"ok": True, "added_min": EXTEND_SEC // 60}

@app.post("/api/admin/extend_all")
def admin_extend_all(admin: str = Cookie(default=None)):
    require_admin(admin)
    with db() as con:
        con.execute("UPDATE teams SET extra_sec=extra_sec+?", (EXTEND_SEC,))
        log(con, "admin_extend_all", None, f"+{EXTEND_SEC//60}m to ALL")
    return {"ok": True, "added_min": EXTEND_SEC // 60}

@app.post("/api/admin/skip")
def admin_skip(team_id: int = Form(...), admin: str = Cookie(default=None)):
    """Escape hatch: push a stuck team past its current stage."""
    require_admin(admin)
    with db() as con:
        t = _get_team(con, team_id)
        if t["stage"] <= CH.TOTAL_STAGES:
            con.execute("INSERT INTO solves(team_id,stage,ts,skipped) VALUES(?,?,?,1)",
                        (team_id, t["stage"], time.time()))
            con.execute("UPDATE teams SET stage=stage+1 WHERE id=?", (team_id,))
            log(con, "admin_skip", team_id, f"skipped stage {t['stage']}")
    return {"ok": True}

@app.post("/api/admin/reset")
def admin_reset(team_id: int = Form(...), admin: str = Cookie(default=None)):
    """Reset a team's clock/progress (rare, e.g. tech failure). Keeps registration."""
    require_admin(admin)
    with db() as con:
        _get_team(con, team_id)
        con.execute("DELETE FROM solves WHERE team_id=?", (team_id,))
        con.execute("""UPDATE teams SET stage=1, escaped=0, started=0, start_ts=NULL,
                       extra_sec=0, frozen=0, finished_ts=NULL WHERE id=?""", (team_id,))
        log(con, "admin_reset", team_id, "full reset")
    return {"ok": True}

@app.get("/api/admin/grid")
def admin_grid(admin: str = Cookie(default=None)):
    require_admin(admin)
    return {"grid": grid_rows()}

@app.get("/api/health")
def health():
    return {"ok": True, "ts": time.time()}
