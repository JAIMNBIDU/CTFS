"""CAMP 17 SALTED ICE - salted SHA-256 creds (hashcat -m 1410, sha256($pass.$salt)).
The salt ships right beside the hash in hash:salt form. The plaintext that
cracks the admin row IS the inner text of the flag. Decoy rows use the same
scheme with throwaway words."""
import hashlib

DECOYS = [("ops_dave", "glacier", "s1"),
          ("ops_mei", "crampons", "s2"),
          ("relay_svc", "altitude", "s3"),
          ("night_watch", "bivouac", "s4")]


def _h(plain, salt):
    return hashlib.sha256((plain + salt).encode()).hexdigest()


def build(ctx):
    inner = ctx.flag[len("acqu1redP34k{"):-1]     # salt_only_slows_you
    salt = "p34k-ice"
    rows = [f"summit_root:{_h(inner, salt)}:{salt}"]
    for user, pw, s in DECOYS:
        rows.append(f"{user}:{_h(pw, s)}:{s}")
        ctx.wordlist.add(pw)
    ctx.write("shadow.txt", "\n".join(rows) + "\n")
    ctx.wordlist.add(inner)
