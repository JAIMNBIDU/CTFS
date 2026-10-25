"""
CYBER ESCAPE ROOM - challenge definitions (10-stage edition).
Flags live ONLY here on the server. Never shipped to the client until a stage is solved.

Difficulty curve tuned for a MIXED junior crowd (1st/2nd yr + some 3rd):
  S1-S2  EASY     on-ramp, instant wins (base64, Caesar)
  S3-S7  MEDIUM   stego, Vigenere, physical, SQLi, Atbash
  S8      PHYSICAL
  S9      HARD     web cookie/privilege tamper (for the sharp teams)
  S10     HARD     audio spectrogram finale

  8 DIGITAL stages carry the themed words -> final passphrase.
  2 PHYSICAL stages (5 and 8) use PER-TEAM grid words -> copy-proof.

Flag format everywhere:  CYBER_ESCAPE_ROOM{word}  (lowercase inside braces)
"""

TOTAL_STAGES    = 10
PHYSICAL_STAGES = [5, 8]              # stage numbers that use per-team grid words

# Final passphrase = the 8 digital words, in stage order (1,2,3,4,6,7,9,10)
FINAL_PASSPHRASE = "every_signal_was_always_buried_inside_white_noise"
DIGITAL_FLAG_WORDS_IN_ORDER = [
    "every", "signal", "was", "always", "buried", "inside", "white", "noise"
]

PHYSICAL_WORD_POOL = [
    "RAVENS", "CIPHER", "BINARY", "GHOSTS", "PHANTM", "VECTOR",
    "KERNEL", "DAEMON", "SHADOW", "BEACON", "WRAITH", "SPHINX",
    "ORACLE", "FALCON", "VORTEX", "PRISMS", "CRYPTS", "HOLLOW",
    "GLITCH", "STATIC", "ECHOES", "ZEROES", "PULSES", "RELICS",
    "SPECTR", "NEXUST", "CARBON", "MATRIX", "COBALT", "ARGENT",
]

# The clearance value the Stage 9 web challenge requires (cookie tamper).
SANCTUM_REQUIRED = "overseer"

STAGES = {
    1: {
        "key": "s1", "title": "STAGE 01 // FIRST CONTACT", "category": "Encoding (easy)",
        "type": "digital", "flag": "CYBER_ESCAPE_ROOM{every}", "asset": "clue1.txt",
        "brief": (
            "Welcome, initiate. Every system leaks. Start small.\n\n"
            "Download the clue. It is not encrypted, just dressed up. One of the most common "
            "ways data hides in plain sight. Decode it and you have your first word."
        ),
        "hints": [
            {"after_min": 4,  "text": "Letters, digits, maybe a '=' at the end. That shape screams Base64."},
            {"after_min": 9,  "text": "Paste it into CyberChef 'From Base64', or run: echo '<blob>' | base64 -d"},
        ],
    },
    2: {
        "key": "s2", "title": "STAGE 02 // SHIFTWORK", "category": "Classical cipher (easy)",
        "type": "digital", "flag": "CYBER_ESCAPE_ROOM{signal}", "asset": "clue2.txt",
        "brief": (
            "The Romans did this two thousand years ago. You can do it in two minutes.\n\n"
            "The text is readable... just slid down the alphabet by a fixed amount. Slide it back."
        ),
        "hints": [
            {"after_min": 4,  "text": "It's a Caesar / shift cipher. Try every shift (there are only 25)."},
            {"after_min": 9,  "text": "dcode.fr Caesar brute-force, or CyberChef 'ROT13 Brute Force'. The readable one is your answer."},
        ],
    },
    3: {
        "key": "s3", "title": "STAGE 03 // THE INVITATION", "category": "Steganography",
        "type": "digital", "flag": "CYBER_ESCAPE_ROOM{was}", "asset": "invitation.png",
        "brief": (
            "Now it gets interesting. We sent you an image. Images lie about how empty they are.\n\n"
            "The eye sees a picture. The machine sees more. Hidden in it is the next word... and a "
            "KEY you must keep for the stage after this. Guard the key."
        ),
        "hints": [
            {"after_min": 7,  "text": "Metadata first. exiftool invitation.png ... read the Comment field."},
            {"after_min": 14, "text": "The EXIF comment is Base64 and tells you WHERE the real message hides (LSB, blue channel), not what."},
            {"after_min": 22, "text": "LSB stego: zsteg, stegsolve, or an online LSB extractor. Hidden text = flag + a word in CAPS. Those caps are your Stage 4 key."},
        ],
    },
    4: {
        "key": "s4", "title": "STAGE 04 // DEAD DROP", "category": "Cryptography",
        "type": "digital", "flag": "CYBER_ESCAPE_ROOM{always}", "asset": "transmission.txt",
        "brief": (
            "A courier left a dead drop. Looks like noise. It is layered.\n\n"
            "Outer shell is an encoding. Under it is a cipher that needs the KEY you pulled from "
            "the image. No key, no message."
        ),
        "hints": [
            {"after_min": 7,  "text": "Base64 first -> you'll get gibberish letters. That's the cipher layer."},
            {"after_min": 14, "text": "The cipher is Vigenere. Key = the CAPITALISED word from Stage 3's hidden message."},
            {"after_min": 22, "text": "Vigenere decrypt, key = RUNGTA (dcode.fr or CyberChef). Plaintext names the flag and sends you walking."},
        ],
    },
    5: {
        "key": "s5", "title": "STAGE 05 // THE DOOR THAT SPEAKS IN SQUARES",
        "category": "Physical / OSINT", "type": "physical", "flag": None,
        "brief": (
            "The next word is not on any screen. It lives on a door.\n\n"
            "Stage 4 told you which door. On it is a GRID of letters and numbers. Below are YOUR "
            "coordinates... nobody else's. Read row,column off the grid, in order, for your six-letter "
            "word. Submit CYBER_ESCAPE_ROOM{yourword} (lowercase).\n\n"
            "Copying another team is useless. Their coordinates spell a different word."
        ),
        "asset": None,
        "hints": [
            {"after_min": 8,  "text": "Coordinates are ROW,COLUMN. Row down the left, column across the top. First number = row."},
            {"after_min": 18, "text": "Six pairs = six letters = one word, lowercase in braces. Can't find the door? Ask a proctor for the LOCATION, never the answer."},
        ],
    },
    6: {
        "key": "s6", "title": "STAGE 06 // THE VAULT", "category": "Web / SQL Injection",
        "type": "digital", "flag": "CYBER_ESCAPE_ROOM{buried}", "endpoint": "/vault", "asset": None,
        "brief": (
            "A login you were never meant to pass. It trusts its input far too much.\n\n"
            "Open THE VAULT below. Don't guess credentials. Make the query lie."
        ),
        "hints": [
            {"after_min": 7,  "text": "It glues your text straight into the SQL. What if your input closes the string early?"},
            {"after_min": 14, "text": "Classic auth bypass: make the WHERE clause always true and comment out the rest."},
            {"after_min": 22, "text": "Username field:  admin' OR '1'='1' --   (space after --). Any password. Vault spills the flag."},
        ],
    },
    7: {
        "key": "s7", "title": "STAGE 07 // FRAGMENT", "category": "Encoding / Classical cipher",
        "type": "digital", "flag": "CYBER_ESCAPE_ROOM{inside}", "asset": "fragment.txt",
        "brief": (
            "A fragment of a destroyed file. Two walls.\n\n"
            "First wall you can nearly read with your eyes (hex). Second is a cipher so old it has "
            "no key... it just flips the alphabet on itself."
        ),
        "hints": [
            {"after_min": 7,  "text": "All chars are 0-9 a-f in pairs = hexadecimal. Hex -> ASCII."},
            {"after_min": 14, "text": "Output still scrambled. Keyless, self-inverse, A<->Z = Atbash."},
            {"after_min": 22, "text": "CyberChef: 'From Hex' then 'Atbash Cipher'. Reveals flag + the second physical room."},
        ],
    },
    8: {
        "key": "s8", "title": "STAGE 08 // THE SECOND ROOM",
        "category": "Physical / OSINT", "type": "physical", "flag": None,
        "brief": (
            "One more place your feet must carry you. Stage 7 named the room.\n\n"
            "Same rules as the door: find the GRID posted there, use YOUR coordinates below, read off "
            "your six-letter word, submit it lowercase in braces. Different grid spot, different word."
        ),
        "asset": None,
        "hints": [
            {"after_min": 8,  "text": "Row,Column again. Use the grid physically posted at THIS location."},
            {"after_min": 18, "text": "Six pairs, six letters, lowercase. Lost? A proctor gives directions, never letters."},
        ],
    },
    9: {
        "key": "s9", "title": "STAGE 09 // THE SANCTUM", "category": "Web / Access Control",
        "type": "digital", "flag": "CYBER_ESCAPE_ROOM{white}", "endpoint": "/sanctum", "asset": None,
        "brief": (
            "A room inside the system that only the OVERSEER may enter. You arrive as an INITIATE.\n\n"
            "The guard checks a badge you are carrying. The badge is on YOUR side of the wire... which "
            "means you can forge it. Open THE SANCTUM below and knock. It will tell you what you are. "
            "Change what you are."
        ),
        "hints": [
            {"after_min": 8,  "text": "The server trusts a cookie named 'clearance' that lives in YOUR browser. Open DevTools -> Application -> Cookies."},
            {"after_min": 16, "text": "Your clearance says 'initiate'. The door wants 'overseer'. You can edit the cookie value directly, then knock again."},
            {"after_min": 25, "text": "Set cookie clearance=overseer (DevTools, or document.cookie='clearance=overseer'), click KNOCK again. Door opens, flag drops."},
        ],
    },
    10: {
        "key": "s10", "title": "STAGE 10 // THE SIGNAL IN THE NOISE",
        "category": "Audio Steganography + Assembly", "type": "digital",
        "flag": "CYBER_ESCAPE_ROOM{noise}", "asset": "final_transmission.wav",
        "brief": (
            "The last transmission. It sounds like static because it is hiding in frequency.\n\n"
            "Download the audio. Don't just listen... LOOK at it in a spectrogram view. The noise "
            "draws the final word.\n\n"
            "Then assemble: every DIGITAL stage gave you a word. Eight words, in stage order, joined "
            "by underscores = the master passphrase. Enter the flag first; the escape prompt follows."
        ),
        "hints": [
            {"after_min": 8,  "text": "Spectrogram = frequency over time. Audacity: track dropdown -> Spectrogram. Or Sonic Visualiser / an online spectrogram viewer."},
            {"after_min": 16, "text": "The word is painted in the mid frequencies. Raise contrast / narrow the range if faint."},
            {"after_min": 25, "text": "Flag word in braces as usual. Final passphrase = the eight digital words (stages 1,2,3,4,6,7,9,10) joined by underscores."},
        ],
    },
}

def normalise(s: str) -> str:
    return "".join(ch for ch in s.strip().lower() if not ch.isspace())
