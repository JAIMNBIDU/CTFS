# CAPTURE THE PEAK :: PRO — ANSWER KEY (marshal only, never ships to players)

`<LAB>` = the pro relay, e.g. `http://20.40.44.235:9100`.

| # | Camp | Category | Flag | Solve |
|---|------|----------|------|-------|
| 1 | THE LEAKING SEAL | Crypto | `acqu1redP34k{padding_oracle_peeled_it}` | CBC padding-oracle: `<LAB>/pro/sealed` gives iv+ct; `<LAB>/pro/unseal?c=HEX` is the oracle (valid/bad padding). Standard attack → plaintext = flag. |
| 2 | TOO CLOSE TO HOME | Crypto | `acqu1redP34k{fermat_primes_too_close}` | `rsa.txt` has n,e,c. Fermat-factor n (near-twin primes), d=inv(e,φ), m=c^d mod n, long_to_bytes → flag. |
| 3 | SHUFFLE THE BADGE | Crypto | `acqu1redP34k{ecb_blocks_rearranged}` | ECB cut-and-paste. `<LAB>/pro/badge?user=` encrypts `user=NAME&role=guest`; build an `admin`+pad block and splice it over the guest block; POST to `<LAB>/pro/enter?badge=HEX`. |
| 4 | A KEY BY ANY NAME | Web | `acqu1redP34k{rs256_confused_for_hs256}` | JWT alg-confusion. Get PEM from `<LAB>/pro/pubkey`, forge `{"role":"admin"}` signed HS256 with the PEM bytes as the secret, send to `<LAB>/pro/vip?token=`. |
| 5 | THE MACHINE THAT LIES | Pwn/Rev | `acqu1redP34k{the_vm_gave_up_its_serial}` | Reverse the per-index transform `((s[i]^0x3C)+i*5)&0xFF == TABLE[i]`. Serial = **`PR0_V4ULT_K3Y_99`**. Run `./vault_vm PR0_V4ULT_K3Y_99`. |

## Scripts (ready to run — replace the host)
Camp 1 padding oracle and camp 3 cut-and-paste both need a short script; the
build's own `builder/verify.py` is a working reference solver for all five if
you want to copy from it.

## Notes
- All five are 300 pts each, time-gated hints (free at 10/20/30 min, −30% per early hint).
- Only reachable at the secret entrance `http://<host>:8100/onlyforpro` ... hand that URL
  out only to teams that have already cleared all 20 main-event camps.
