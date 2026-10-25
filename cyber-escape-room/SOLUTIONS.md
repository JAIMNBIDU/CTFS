# Cyber Escape Room — SOLUTIONS (full spoiler)

STOP. Complete answer key for all 10 stages + the final escape. Read only the
stage you're stuck on.

Master escape passphrase (stage order 1,2,3,4,6,7,9,10):
`every_signal_was_always_buried_inside_white_noise`

Tools: any browser, CyberChef (gchq.github.io/CyberChef), exiftool, Audacity (or
any spectrogram viewer). All free, all browser/desktop.

---

## STAGE 1 // FIRST CONTACT — base64 — `CYBER_ESCAPE_ROOM{every}`
`clue1.txt` is Base64.
```bash
echo '<contents of clue1.txt>' | base64 -d
```
→ `CYBER_ESCAPE_ROOM{every} :: next message is shifted down the alphabet`

## STAGE 2 // SHIFTWORK — Caesar — `CYBER_ESCAPE_ROOM{signal}`
`clue2.txt` is a Caesar cipher, shift back **7**. CyberChef "ROT13 Brute Force" and
pick the readable line, or dcode.fr Caesar.
→ `CYBER_ESCAPE_ROOM{signal} :: next look inside the image the machine sees more`

## STAGE 3 // THE INVITATION — stego (EXIF + LSB) — `CYBER_ESCAPE_ROOM{was}`  [+ KEY]
`invitation.png`. Step 1, metadata:
```bash
exiftool invitation.png
```
The **Comment** field is Base64 → `look where the eye cannot see :: method=LSB :: channel=blue`.
Step 2, pull LSB data from the blue channel (zsteg, stegsolve, aperisolve.com, or
a few lines of Python):
→ `CYBER_ESCAPE_ROOM{was} :: KEY=RUNGTA :: proceed to the dead drop`
**Keep `RUNGTA`** ... it's the Stage 4 Vigenère key.

## STAGE 4 // DEAD DROP — base64 → Vigenère — `CYBER_ESCAPE_ROOM{always}`
`transmission.txt` is Base64 → Vigenère ciphertext. CyberChef: `From Base64` then
`Vigenère Decode` key `RUNGTA`.
→ `FLAG CYBER_ESCAPE_ROOM{always} :: NEXT ... read your coordinates off the grid`

## STAGE 5 // THE DOOR THAT SPEAKS IN SQUARES — grid lookup — *per-player*
Your dashboard shows **6 coordinates** (row,column), unique to you. Open
`challenges/grid.png` and read each coordinate (row first, then column), in order.
Six letters = your word. Submit `CYBER_ESCAPE_ROOM{yourword}` lowercase.

The grid (seed 1337, same for everyone):
```
     1  2  3  4  5  6
 1   1  4  O  S  I  H
 2   9  B  F  A  7  E
 3   R  P  5  T  3  Q
 4   C  0  N  D  2  6
 5   G  W  M  J  L  Z
 6   U  Y  V  K  X  8
```
**Worked example** ... coords `2,2  1,5  4,3  2,4  3,1  6,2`:
```
2,2=B  1,5=I  4,3=N  2,4=A  3,1=R  6,2=Y   ->  BINARY
```
submit `CYBER_ESCAPE_ROOM{binary}`. Your coords spell a different word; use yours.

## STAGE 6 // THE VAULT — SQL injection — `CYBER_ESCAPE_ROOM{buried}`
Login box in the dashboard. Auth-bypass in the **username** field (any password):
```
admin' OR '1'='1' -- 
```
(space after `--`). Vault opens → `CYBER_ESCAPE_ROOM{buried}`.

## STAGE 7 // FRAGMENT — hex → Atbash — `CYBER_ESCAPE_ROOM{inside}`
`fragment.txt` is hex. CyberChef `From Hex` + `Atbash Cipher`.
→ `CYBER_ESCAPE_ROOM{inside} :: NEXT ... read your coordinates` (sends you to stage 8)

## STAGE 8 // THE SECOND ROOM — grid lookup — *per-player*
Identical mechanic to Stage 5, a **different** set of 6 coordinates on your
dashboard. Same `challenges/grid.png`, read off your word, submit lowercase.

## STAGE 9 // THE SANCTUM — cookie / access-control tamper — `CYBER_ESCAPE_ROOM{white}`
1. Click **KNOCK**. The guard stamps you `initiate` and drops a cookie
   `clearance=initiate`; says only `overseer` may enter.
2. Forge it: DevTools → Application → Cookies → change `clearance` to `overseer`
   (or console: `document.cookie='clearance=overseer'`).
3. KNOCK again → `CYBER_ESCAPE_ROOM{white}`.
Lesson: the server trusted a value living on the client.

## STAGE 10 // THE SIGNAL IN THE NOISE — audio spectrogram — `CYBER_ESCAPE_ROOM{noise}`
`final_transmission.wav` sounds like static. Open it in a **spectrogram** view,
not a player. Audacity: open → track dropdown → Spectrogram. The frequencies draw
the word **NOISE** in the 2-6 kHz band (raise contrast if faint).
→ `CYBER_ESCAPE_ROOM{noise}`

---

## FINAL ASSEMBLY + ESCAPE

Take the 8 digital-stage words in stage order (1,2,3,4,6,7,9,10), joined by
underscores:
```
every_signal_was_always_buried_inside_white_noise
```
Enter it → `SYSTEM BREACHED. YOU ARE OUT.`

(The two physical words from stages 5 and 8 are gates only, not part of the
passphrase ... which is why the final key is the same for everyone.)

---

## One-glance answer card

| # | Type | Flag / answer |
|---|------|---------------|
| 1 | base64 | `CYBER_ESCAPE_ROOM{every}` |
| 2 | Caesar -7 | `CYBER_ESCAPE_ROOM{signal}` |
| 3 | EXIF+LSB (key RUNGTA) | `CYBER_ESCAPE_ROOM{was}` |
| 4 | base64+Vigenère[RUNGTA] | `CYBER_ESCAPE_ROOM{always}` |
| 5 | grid lookup | per-player (your dashboard coords + grid.png) |
| 6 | SQLi `admin' OR '1'='1' -- ` | `CYBER_ESCAPE_ROOM{buried}` |
| 7 | hex+Atbash | `CYBER_ESCAPE_ROOM{inside}` |
| 8 | grid lookup | per-player (your dashboard coords + grid.png) |
| 9 | cookie clearance=overseer | `CYBER_ESCAPE_ROOM{white}` |
| 10 | spectrogram = NOISE | `CYBER_ESCAPE_ROOM{noise}` |
| F | assemble | `every_signal_was_always_buried_inside_white_noise` |
