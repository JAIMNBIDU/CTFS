"""CAMP 11 THIN CRUST - unsalted md5 creds; one cracks to the flag."""
import hashlib
def build(ctx):
    md5 = lambda s: hashlib.md5(s.encode()).hexdigest()
    rows = [f"relay_admin:{md5(ctx.flag)}"]
    for u, pw in [("ops_dave", "summit2026"), ("ops_mei", "glacier!1"),
                  ("relay_svc", "password123"), ("night_watch", "letmein")]:
        rows.append(f"{u}:{md5(pw)}")
    ctx.write("creds.txt", "\n".join(rows) + "\n")
    ctx.wordlist.update([ctx.flag, "summit2026", "glacier!1", "password123", "letmein"])
