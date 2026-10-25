# Capture the PEAK

A scored, multi-camp CTF across five categories. Originally run as a hosted
multi-team event; this repo is the self-hostable build so you can run the whole
thing on your own machine and solve it at your own pace.

```
Penetration . Exploitation . Analysis . Kryptography
```

20 camps. Attack them in any order (board mode) or one-unlocks-the-next (linear
mode). A live leaderboard and an in-browser Linux terminal are built in, so you
need nothing installed except Docker and a browser.

## The twenty camps

| Category | Camps |
|---|---|
| Forensics / OSINT | 01 BASE CAMP · 02 THE WIRE · 03 LOST & FOUND · 14 BEACON IN THE STORM |
| Steganography | 04 BENEATH THE SNOW · 05 WHITE NOISE · 15 THE BURIED KEY |
| Web | 06 THIN AIR · 07 CREVASSE · 08 SWITCHBACK · 13 THE MIRROR WALL · 20 SILENT LEDGER |
| Pwn | 09 THE LADDER · 10 CORNICE · 16 THE GLASS BOX · 19 DEAD RECKONING |
| Crypto | 18 THE VAULT DOOR |
| Hashing | 11 THIN CRUST · 12 THE SUMMIT · 17 SALTED ICE |

Hardest camps (no AI shortcut... you still have to run the script):
**18** (AES-ECB byte-at-a-time oracle), **19** (keygen reversing),
**20** (blind boolean SQLi), plus **13** (SSTI) and **16** (Python sandbox escape).

Flag format: `acqu1redP34k{snake_case_lesson}`

## Note on Camp 03

At the live event, Camp 03 was out-of-band: you messaged a keyword to a marshal
on WhatsApp who replied with the flag by hand. That doesn't work solo, so for this
self-hosted build it's been converted to a self-contained OSINT stage... the flag
now lives (base64-wrapped) in the photo's EXIF metadata. `exiftool` → decode →
submit. No marshal, no phone number. All 20 camps are fully self-serve.

## Next

Build and run: [`SETUP.md`](SETUP.md). Stuck or done: [`SOLUTIONS.md`](SOLUTIONS.md).
For the 5-camp hard bonus tier, see [`../capture-the-peak-pro/`](../capture-the-peak-pro/).
