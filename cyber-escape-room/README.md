# Cyber Escape Room

A 10-stage chained CTF. Each stage hands you the thing you need for the next, and
the eight "digital" stages each give one word of a final escape passphrase. Solve
the chain, assemble the phrase, escape.

Built for a mixed junior crowd: starts easy (base64, Caesar), ramps through stego,
classical crypto, web, and finishes on a cookie-tamper and an audio-spectrogram
puzzle. Google and AI don't trivialize it ... the chain and the variety are what
make it take time.

Flag format: `CYBER_ESCAPE_ROOM{word}`

## The ten stages

| # | Stage | Type | Skill |
|---|-------|------|-------|
| 1 | FIRST CONTACT | digital | base64 |
| 2 | SHIFTWORK | digital | Caesar cipher |
| 3 | THE INVITATION | digital | stego (EXIF + LSB) |
| 4 | DEAD DROP | digital | base64 → Vigenère |
| 5 | THE DOOR THAT SPEAKS IN SQUARES | *physical → see below* | grid lookup |
| 6 | THE VAULT | digital | SQL injection |
| 7 | FRAGMENT | digital | hex → Atbash |
| 8 | THE SECOND ROOM | *physical → see below* | grid lookup |
| 9 | THE SANCTUM | digital | cookie / access-control tamper |
| 10 | THE SIGNAL IN THE NOISE | digital | audio spectrogram |

## The two "physical" stages run fine solo

Stages 5 and 8 were originally physical: teams walked to a printed letter-grid
taped on a door and read coordinates off it. Running locally there's no room and
no printout, but nothing breaks:

- The grid ships in this repo as [`challenges/grid.png`](challenges/grid.png) (it's
  the same grid the server uses, seed 1337).
- Your six coordinates for each stage show up **on your dashboard** when you reach
  the stage.
- Read `row,column` off `grid.png` for each coordinate, in order → your six-letter
  word → submit `CYBER_ESCAPE_ROOM{yourword}` lowercase.

So solo, stages 5 and 8 are just "grid lookup" puzzles. Zero code changes. (Note:
the two physical words are gates only ... they are NOT part of the final
passphrase, which is built from the eight digital words.)

## Next

Build and run: [`SETUP.md`](SETUP.md). Stuck or done: [`SOLUTIONS.md`](SOLUTIONS.md).
