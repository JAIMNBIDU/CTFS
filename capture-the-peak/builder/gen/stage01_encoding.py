"""CAMP 01 BASE CAMP - layered encoding: base32(base64(hex(rot13(flag))))."""
import base64, codecs
def build(ctx):
    r = codecs.encode(ctx.flag, "rot13")
    h = r.encode().hex()
    b = base64.b64encode(h.encode())
    b32 = base64.b32encode(b).decode()
    hdr = ("# BASE CAMP LOG // sealed before the storm\n"
           "# four coats of paint. peel outside-in.\n"
           "# (the outer two are both common ways to pack bytes into text.)\n")
    ctx.write("basecamp.txt", hdr + b32 + "\n")
