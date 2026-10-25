"""CAMP 04 BENEATH THE SNOW - steghide, passphrase hidden in a sibling file."""
import subprocess
import numpy as np
from PIL import Image
PASS = "snowline-echo-42"
def build(ctx):
    d = ctx.stage_dir
    arr = (np.random.rand(600, 800, 3) * 45 + 12).astype("uint8")
    cover = d / "snowfield.jpg"
    Image.fromarray(arr, "RGB").save(cover, "JPEG", quality=92)
    secret = d / "_peak.txt"
    secret.write_text(ctx.flag + "\n")
    subprocess.run(["steghide", "embed", "-cf", str(cover), "-ef", str(secret),
                    "-p", PASS, "-sf", str(cover), "-f"],
                   check=True, capture_output=True)
    secret.unlink()
    notes = ("CAMP 04 FIELD NOTES\n" + "routine ascent, nothing to report.\n" * 5 +
             f"\x00\x00ops reminder: image passphrase = {PASS}\x00\x00\n" +
             "weather holding. visibility good.\n" * 3)
    d.joinpath("notes.txt").write_bytes(notes.encode())
