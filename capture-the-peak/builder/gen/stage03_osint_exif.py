"""CAMP 03 LOST & FOUND - self-contained OSINT.

Originally an out-of-band stage (message a marshal, get the flag by hand). For a
self-hosted / solo run there is no marshal, so the flag lives in the photo's EXIF
metadata, base64-wrapped. exiftool -> read UserComment -> base64 decode -> flag.
No human, no phone number. Still a real metadata/OSINT puzzle.
"""
import base64
import subprocess
from PIL import Image


def build(ctx):
    p = ctx.stage_dir / "dropped.jpg"
    img = Image.new("RGB", (900, 600), (16, 18, 24))
    img.save(p, "JPEG", quality=85)

    b64 = base64.b64encode(ctx.flag.encode()).decode()
    note = ("TRAIL MARKER. The pixels are empty ... the camera wrote the real "
            "message into the file's metadata when the shot was taken. It is "
            "dressed up. Decode what follows.  b64=" + b64)

    subprocess.run(["exiftool", "-overwrite_original",
                    f"-UserComment={note}",
                    "-Artist=decoy // nothing hidden in the pixels",
                    str(p)], check=True, capture_output=True)
