"""
Capture the PEAK - builder. Generates all stage artifacts, the validation
hashes, the lab flags, and the cracking wordlist into an output tree.

Usage:  python3 generate.py <OUT_DIR>   (default: ./_build)

Produces:
  <OUT>/ctf/stageNN/...        player artifacts (ship to /ctf)
  <OUT>/data/validation.json   {salt, flag_hashes}   (ship to /opt/peak/data)
  <OUT>/data/{prompts,hints,event}.yaml
  <OUT>/lab/flags.json         relay flags (6-9, 13, 16) (ship to /opt/peak/lab)
  <OUT>/wordlists/peak-mini.txt
"""
import os
import sys
import json
import shutil
import random
import hashlib
import importlib
from pathlib import Path

import warnings
import yaml
warnings.filterwarnings("ignore")   # quiet pyjwt key-length notices

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from gen._common import Ctx   # noqa

STAGE_MODULE = {
    1: "gen.stage01_encoding", 2: "gen.stage02_pcap_http", 3: "gen.stage03_osint_exif",
    4: "gen.stage04_steghide", 5: "gen.stage05_lsb_qr",
    6: "gen.stage_web", 7: "gen.stage_web", 8: "gen.stage_web", 9: "gen.stage_web",
    10: "gen.stage10_gatekeeper", 11: "gen.stage11_hashing", 12: "gen.stage12_jwt",
    # ---- expansion camps ----
    13: "gen.stage_web",            # SSTI, lives on the relay
    14: "gen.stage14_dns",          # DNS exfil pcap
    15: "gen.stage15_stego2",       # EXIF-key + steghide
    16: "gen.stage_web",            # python sandbox escape, lives on the relay
    17: "gen.stage17_salthash",     # salted sha256
    # ---- hard tier ----
    18: "gen.stage_web",            # AES-ECB byte-at-a-time oracle (relay)
    19: "gen.stage19_keygen",       # keygen-me binary
    20: "gen.stage_web",            # blind boolean SQLi (relay)
}
N_STAGES = len(STAGE_MODULE)

DECOY_WORDS = [
    "123456", "qwerty", "iloveyou", "dragon", "monkey", "sunshine", "princess",
    "football", "welcome", "admin", "trustno1", "whatever", "freedom", "ninja",
    "everest", "k2summit", "basecamp", "crampons", "altitude", "oxygen", "ridge",
    "snowpack", "icefall", "serac", "bivouac", "carabiner", "belay", "rappel",
]


def sha(salt, v):
    return hashlib.sha256((salt + v).encode()).hexdigest()


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "_build"
    if out.exists():
        shutil.rmtree(out)
    (out / "ctf").mkdir(parents=True)
    (out / "data").mkdir(parents=True)
    (out / "lab").mkdir(parents=True)
    (out / "wordlists").mkdir(parents=True)

    flags_cfg = yaml.safe_load(open(ROOT / "config" / "flags.yaml"))
    salt = flags_cfg["salt"]
    flags = {int(k): v for k, v in flags_cfg["flags"].items()}
    event = yaml.safe_load(open(ROOT / "config" / "event.yaml"))

    flag_hashes = {}
    lab_flags = {}
    wordlist = set()

    for n in range(1, N_STAGES + 1):
        ctx = Ctx(n, flags[n], flags, salt, out, event)
        mod = importlib.import_module(STAGE_MODULE[n])
        mod.build(ctx)
        flag_hashes[str(n)] = sha(salt, flags[n])
        lab_flags.update({str(k): v for k, v in ctx.lab_flags.items()})
        wordlist.update(ctx.wordlist)
        print(f"  camp {n:02d}  {STAGE_MODULE[n].split('.')[-1]:<20}  ok")

    # validation + public config
    json.dump({"salt": salt, "flag_hashes": flag_hashes},
              open(out / "data" / "validation.json", "w"), indent=2)
    for f in ("prompts.yaml", "hints.yaml", "event.yaml"):
        shutil.copy(ROOT / "config" / f, out / "data" / f)

    # lab flags (6-9, 13, 16)
    json.dump(lab_flags, open(out / "lab" / "flags.json", "w"), indent=2)

    # wordlist: real answers + decoys, shuffled
    words = list(wordlist) + DECOY_WORDS
    random.Random(1337).shuffle(words)
    (out / "wordlists" / "peak-mini.txt").write_text("\n".join(words) + "\n")

    print(f"\nflags hashed: {len(flag_hashes)}   lab flags: {sorted(lab_flags)}   "
          f"wordlist: {len(words)} words")
    print(f"build tree: {out}")


if __name__ == "__main__":
    main()
