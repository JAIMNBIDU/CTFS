# Capture the PEAK :: PRO

The bonus tier. 5 camps, all hard, each worth 300 points, each roughly as tough
as the main event's final boss. Crypto-heavy with one reversing finale.

At the live event this was a locked second tier you only reached after clearing
all 20 main camps, behind a secret URL (`/onlyforpro`) and an unlock code.
Running solo, that gate is pointless. The live event is over, so the gate is open.

**Entry key: `peak-pro-open`**

Pass it as `-e PEAK_ADMIN_PASS=peak-pro-open` when running the container (see
[`SETUP.md`](SETUP.md)), then navigate to `http://localhost:8200/onlyforpro` and
enter the key above. That's the only thing standing between you and the five camps.

## The five camps

| # | Camp | Category | What it is |
|---|------|----------|-----------|
| 1 | THE LEAKING SEAL | Crypto | CBC padding oracle |
| 2 | TOO CLOSE TO HOME | Crypto | RSA, Fermat factorization (near-twin primes) |
| 3 | SHUFFLE THE BADGE | Crypto | AES-ECB cut-and-paste |
| 4 | A KEY BY ANY NAME | Web | JWT RS256→HS256 alg confusion |
| 5 | THE MACHINE THAT LIES | Pwn / Rev | reverse a serial-check VM |

Flag format: `acqu1redP34k{snake_case_lesson}`. All five need a short script (except
camp 5's final run) ... no AI one-liner clears these, you have to write and run
the attack.

## Heads up on the shipped compose

The `docker-compose.yml` in this folder is a stale copy of the main event's and
will NOT run PRO correctly (wrong ports, no gate). Ignore it and follow
[`SETUP.md`](SETUP.md), which gives the correct local run.

## Next

Build and run: [`SETUP.md`](SETUP.md). Answer key: [`SOLUTIONS.md`](SOLUTIONS.md).
