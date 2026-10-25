"""
Capture the PEAK - data layer (SQLite, stdlib only).

One shared server, many teams. A team is one shared login (solo = team of 1).
State we keep per team: solves (with locked-in points), hint tiers taken,
timer start, and an audit log. Scoring and the leaderboard are computed from
these tables, never stored denormalised.
"""
import os
import sqlite3
import hashlib
import hmac
import secrets
import threading
import time
from datetime import datetime, timezone

DB_PATH = os.environ.get("PEAK_DB", "/var/peak/peak.db")
_LOCK = threading.RLock()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _mono():
    return time.time()


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=5000")
    return c


SCHEMA = """
CREATE TABLE IF NOT EXISTS teams (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT UNIQUE NOT NULL,
    name_lc     TEXT UNIQUE NOT NULL,
    passhash    TEXT NOT NULL,
    salt        TEXT NOT NULL,
    is_solo     INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    started_epoch REAL NOT NULL,         -- timer anchor (unix seconds)
    banned      INTEGER NOT NULL DEFAULT 0,
    extra_seconds INTEGER NOT NULL DEFAULT 0   -- admin time grants (+30 min etc)
);
CREATE TABLE IF NOT EXISTS settings (
    k TEXT PRIMARY KEY,
    v TEXT
);
CREATE TABLE IF NOT EXISTS solves (
    team_id     INTEGER NOT NULL,
    stage       INTEGER NOT NULL,
    points      INTEGER NOT NULL,
    solved_at   TEXT NOT NULL,
    solved_epoch REAL NOT NULL,
    PRIMARY KEY (team_id, stage)
);
CREATE TABLE IF NOT EXISTS hints (
    team_id     INTEGER NOT NULL,
    stage       INTEGER NOT NULL,
    tier        INTEGER NOT NULL,       -- max tier revealed (1..3)
    early       INTEGER NOT NULL DEFAULT 0,  -- how many were force-revealed early
    PRIMARY KEY (team_id, stage)
);
CREATE TABLE IF NOT EXISTS camp_open (
    team_id     INTEGER NOT NULL,
    stage       INTEGER NOT NULL,
    opened_epoch REAL NOT NULL,         -- when the team first opened this camp (hint clock)
    PRIMARY KEY (team_id, stage)
);
CREATE TABLE IF NOT EXISTS team_ips (
    team_id     INTEGER NOT NULL,
    ip          TEXT NOT NULL,
    PRIMARY KEY (team_id, ip)
);
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id     INTEGER,
    ts          TEXT NOT NULL,
    kind        TEXT NOT NULL,
    detail      TEXT
);
"""


def init_db():
    with _LOCK, _conn() as c:
        c.executescript(SCHEMA)
        # migrate older DBs that predate these columns
        cols = {r["name"] for r in c.execute("PRAGMA table_info(teams)").fetchall()}
        if "banned" not in cols:
            c.execute("ALTER TABLE teams ADD COLUMN banned INTEGER NOT NULL DEFAULT 0")
        if "extra_seconds" not in cols:
            c.execute("ALTER TABLE teams ADD COLUMN extra_seconds INTEGER NOT NULL DEFAULT 0")
        if "paused" not in cols:
            c.execute("ALTER TABLE teams ADD COLUMN paused INTEGER NOT NULL DEFAULT 0")
        hcols = {r["name"] for r in c.execute("PRAGMA table_info(hints)").fetchall()}
        if hcols and "early" not in hcols:
            c.execute("ALTER TABLE hints ADD COLUMN early INTEGER NOT NULL DEFAULT 0")


# ---- password hashing (salted PBKDF2, stdlib) -----------------------------
def _hash_pw(pw, salt):
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 120_000).hex()


def create_team(name, passphrase, is_solo=False):
    name = name.strip()
    name_lc = name.lower()
    if not name or len(name) > 40:
        return None, "team name must be 1-40 characters"
    if len(passphrase) < 3:
        return None, "passphrase too short"
    salt = secrets.token_hex(8)
    ph = _hash_pw(passphrase, salt)
    with _LOCK, _conn() as c:
        try:
            cur = c.execute(
                "INSERT INTO teams (name,name_lc,passhash,salt,is_solo,created_at,started_epoch)"
                " VALUES (?,?,?,?,?,?,?)",
                (name, name_lc, ph, salt, 1 if is_solo else 0, _now(), _mono()),
            )
        except sqlite3.IntegrityError:
            return None, "that name is already taken"
        tid = cur.lastrowid
        c.execute("INSERT INTO events (team_id,ts,kind,detail) VALUES (?,?,?,?)",
                  (tid, _now(), "register", f"solo={is_solo}"))
    return tid, None


def auth_team(name, passphrase):
    with _LOCK, _conn() as c:
        r = c.execute("SELECT * FROM teams WHERE name_lc=?", (name.strip().lower(),)).fetchone()
        if not r:
            return None, "no such team"
        if not hmac.compare_digest(r["passhash"], _hash_pw(passphrase, r["salt"])):
            c.execute("INSERT INTO events (team_id,ts,kind,detail) VALUES (?,?,?,?)",
                      (r["id"], _now(), "bad_login", name))
            return None, "wrong passphrase"
        c.execute("INSERT INTO events (team_id,ts,kind,detail) VALUES (?,?,?,?)",
                  (r["id"], _now(), "login", None))
        return r["id"], None


def get_team(team_id):
    with _LOCK, _conn() as c:
        return c.execute("SELECT * FROM teams WHERE id=?", (team_id,)).fetchone()


# ---- per-team progress ----------------------------------------------------
def team_hints(team_id):
    with _LOCK, _conn() as c:
        rows = c.execute("SELECT stage,tier FROM hints WHERE team_id=?", (team_id,)).fetchall()
    return {r["stage"]: r["tier"] for r in rows}


def team_solves(team_id):
    with _LOCK, _conn() as c:
        rows = c.execute("SELECT stage,points,solved_epoch FROM solves WHERE team_id=?",
                         (team_id,)).fetchall()
    return {r["stage"]: {"points": r["points"], "epoch": r["solved_epoch"]} for r in rows}


def reveal_hint(team_id, stage, tier, is_early=False):
    with _LOCK, _conn() as c:
        r = c.execute("SELECT tier,early FROM hints WHERE team_id=? AND stage=?",
                      (team_id, stage)).fetchone()
        cur = r["tier"] if r else 0
        cur_early = r["early"] if r else 0
        new = max(cur, tier)
        new_early = cur_early + (1 if is_early else 0)
        if r:
            c.execute("UPDATE hints SET tier=?, early=? WHERE team_id=? AND stage=?",
                      (new, new_early, team_id, stage))
        else:
            c.execute("INSERT INTO hints (team_id,stage,tier,early) VALUES (?,?,?,?)",
                      (team_id, stage, new, new_early))
        c.execute("INSERT INTO events (team_id,ts,kind,detail) VALUES (?,?,?,?)",
                  (team_id, _now(), "hint",
                   f"stage={stage} tier={tier}{' EARLY(-30%)' if is_early else ' (free)'}"))
    return new


def team_early(team_id):
    with _LOCK, _conn() as c:
        rows = c.execute("SELECT stage,early FROM hints WHERE team_id=?", (team_id,)).fetchall()
    return {r["stage"]: r["early"] for r in rows}


# ---- camp open times (hint clock) ----------------------------------------
def record_open(team_id, stage):
    with _LOCK, _conn() as c:
        c.execute("INSERT OR IGNORE INTO camp_open (team_id,stage,opened_epoch) VALUES (?,?,?)",
                  (team_id, stage, _mono()))


def team_opens(team_id):
    with _LOCK, _conn() as c:
        rows = c.execute("SELECT stage,opened_epoch FROM camp_open WHERE team_id=?",
                         (team_id,)).fetchall()
    return {r["stage"]: r["opened_epoch"] for r in rows}


# ---- ip tracking (anti-cheat) --------------------------------------------
def record_ip(team_id, ip):
    if not ip:
        return
    with _LOCK, _conn() as c:
        c.execute("INSERT OR IGNORE INTO team_ips (team_id,ip) VALUES (?,?)", (team_id, ip))


def shared_ips():
    """IPs seen for more than one team -> [(ip, [team names])]."""
    with _LOCK, _conn() as c:
        rows = c.execute(
            "SELECT ti.ip AS ip, t.name AS name FROM team_ips ti "
            "JOIN teams t ON t.id=ti.team_id ORDER BY ti.ip").fetchall()
    by_ip = {}
    for r in rows:
        by_ip.setdefault(r["ip"], []).append(r["name"])
    return [(ip, names) for ip, names in by_ip.items() if len(set(names)) > 1]


def record_solve(team_id, stage, points):
    with _LOCK, _conn() as c:
        exists = c.execute("SELECT 1 FROM solves WHERE team_id=? AND stage=?",
                           (team_id, stage)).fetchone()
        if exists:
            return False
        c.execute("INSERT INTO solves (team_id,stage,points,solved_at,solved_epoch)"
                  " VALUES (?,?,?,?,?)", (team_id, stage, points, _now(), _mono()))
        c.execute("INSERT INTO events (team_id,ts,kind,detail) VALUES (?,?,?,?)",
                  (team_id, _now(), "solve", f"stage={stage} pts={points}"))
    return True


def log_event(team_id, kind, detail=None):
    with _LOCK, _conn() as c:
        c.execute("INSERT INTO events (team_id,ts,kind,detail) VALUES (?,?,?,?)",
                  (team_id, _now(), kind, detail))


# ---- admin controls -------------------------------------------------------
def set_ban(team_id, banned):
    with _LOCK, _conn() as c:
        c.execute("UPDATE teams SET banned=? WHERE id=?", (1 if banned else 0, team_id))
        c.execute("INSERT INTO events (team_id,ts,kind,detail) VALUES (?,?,?,?)",
                  (team_id, _now(), "admin", "disqualified" if banned else "reinstated"))


def add_extra(team_id, seconds):
    with _LOCK, _conn() as c:
        c.execute("UPDATE teams SET extra_seconds=extra_seconds+? WHERE id=?", (seconds, team_id))
        c.execute("INSERT INTO events (team_id,ts,kind,detail) VALUES (?,?,?,?)",
                  (team_id, _now(), "admin", f"time +{int(seconds/60)}min"))


def set_pause(team_id, paused):
    with _LOCK, _conn() as c:
        c.execute("UPDATE teams SET paused=? WHERE id=?", (1 if paused else 0, team_id))
        c.execute("INSERT INTO events (team_id,ts,kind,detail) VALUES (?,?,?,?)",
                  (team_id, _now(), "admin", "paused (suspicious)" if paused else "unpaused"))


def get_setting(k, default=None):
    with _LOCK, _conn() as c:
        r = c.execute("SELECT v FROM settings WHERE k=?", (k,)).fetchone()
        return r["v"] if r else default


def set_setting(k, v):
    with _LOCK, _conn() as c:
        c.execute("INSERT INTO settings (k,v) VALUES (?,?) "
                  "ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, str(v)))


# ---- leaderboard / admin --------------------------------------------------
def all_teams():
    with _LOCK, _conn() as c:
        return c.execute("SELECT * FROM teams ORDER BY id").fetchall()


def leaderboard():
    """List of dicts: name, is_solo, score, solves, last_epoch, started_epoch."""
    with _LOCK, _conn() as c:
        teams = c.execute("SELECT id,name,is_solo,started_epoch,banned FROM teams").fetchall()
        out = []
        for t in teams:
            if t["banned"]:
                continue   # disqualified teams drop off the public board
            agg = c.execute(
                "SELECT COALESCE(SUM(points),0) AS score, COUNT(*) AS n,"
                " COALESCE(MAX(solved_epoch),0) AS last_epoch"
                " FROM solves WHERE team_id=?", (t["id"],)).fetchone()
            out.append({
                "id": t["id"], "name": t["name"], "is_solo": bool(t["is_solo"]),
                "score": agg["score"], "solves": agg["n"],
                "last_epoch": agg["last_epoch"], "started_epoch": t["started_epoch"],
            })
    # rank: score desc, then earliest last-solve (faster to that score) asc
    out.sort(key=lambda r: (-r["score"], r["last_epoch"] if r["last_epoch"] else 9e18))
    for i, r in enumerate(out, 1):
        r["rank"] = i
    return out


def recent_events(limit=200):
    with _LOCK, _conn() as c:
        rows = c.execute(
            "SELECT e.*, t.name AS team FROM events e LEFT JOIN teams t ON t.id=e.team_id"
            " ORDER BY e.id DESC LIMIT ?", (limit,)).fetchall()
    return rows
