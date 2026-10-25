"""CAMP 05 WHITE NOISE - QR carried in the blue channel of a cover PNG."""
import numpy as np, qrcode
from PIL import Image
def build(ctx):
    d = ctx.stage_dir
    qr = qrcode.QRCode(border=4, box_size=6)
    qr.add_data(ctx.flag); qr.make(fit=True)
    q = np.array(qr.make_image(fill_color="black", back_color="white").convert("L"))
    H, W = q.shape
    base = np.zeros((H, W, 3), dtype="uint8")
    base[:, :, 0] = (np.random.rand(H, W) * 55 + 120).astype("uint8")  # R noise
    base[:, :, 1] = (np.random.rand(H, W) * 55 + 110).astype("uint8")  # G noise
    base[:, :, 2] = np.where(q < 128, 0, 255).astype("uint8")           # B = QR
    Image.fromarray(base, "RGB").save(d / "glacier.png")
