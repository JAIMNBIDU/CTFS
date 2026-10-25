"""CAMP 15 THE BURIED KEY - steghide, but the passphrase is hidden in the
cover image's EXIF (not in a sibling text file). The sibling notes.txt is a
decoy that explicitly says the key is no longer written down beside the image,
pushing teams to read the metadata instead.

steghide can abort (SIGABRT) on some cover images with certain libjpeg builds,
which would fail the whole self-testing build. We use a smooth gradient cover
(far more reliable than high-amplitude noise) and, belt-and-braces, retry with
a fresh cover until the embed succeeds. First attempt is seeded for a
reproducible image; retries vary.
"""
import os
import subprocess
import numpy as np
from PIL import Image

PASS = "ridge-echo-77-exif"


def _make_cover(path, seed):
    rng = np.random.default_rng(seed)
    yy = np.linspace(20, 205, 600).reshape(-1, 1)
    xx = np.linspace(10, 175, 800).reshape(1, -1)
    base = (yy + xx) / 2.0
    arr = np.stack([base, base * 0.8 + 15, base * 0.6 + 30], axis=-1)
    arr = np.clip(arr + rng.normal(0, 6, arr.shape), 0, 255).astype("uint8")
    Image.fromarray(arr, "RGB").save(path, "JPEG", quality=90)


def build(ctx):
    d = ctx.stage_dir
    cover = d / "summit.jpg"
    secret = d / "_peak.txt"
    secret.write_text(ctx.flag + "\n")

    seeds = [7] + [int.from_bytes(os.urandom(4), "big") for _ in range(120)]
    for seed in seeds:
        _make_cover(cover, seed)
        r = subprocess.run(["steghide", "embed", "-cf", str(cover), "-ef", str(secret),
                            "-p", PASS, "-sf", str(cover), "-f"], capture_output=True)
        if r.returncode == 0:
            break
    else:
        raise RuntimeError("steghide failed to embed camp 15 after many covers")
    secret.unlink()

    # write the passphrase into the image's OWN metadata (this is the key)
    subprocess.run(["exiftool", "-overwrite_original",
                    f"-UserComment=relay key rotation :: steghide passphrase = {PASS}",
                    "-Artist=ridge-ops", str(cover)], check=True, capture_output=True)

    # decoy sibling: tells teams the key is NOT written beside the image anymore
    notes = ("CAMP 15 FIELD NOTES\n"
             "after the notes.txt leak last season, ops stopped writing the\n"
             "image key into any file next to it. the key now travels WITH the\n"
             "photo itself. (no, grepping this file will not help you.)\n"
             "weather holding. visibility good.\n")
    d.joinpath("notes.txt").write_text(notes)
