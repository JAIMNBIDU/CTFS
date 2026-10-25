# Capture the PEAK - player shell
export PS1='\[\e[38;5;203m\]climber\[\e[0m\]@peak:\[\e[38;5;141m\]\w\[\e[0m\]$ '
export PEAK_WORDLIST=/opt/peak/wordlists/peak-mini.txt
alias ll='ls -la'
cat <<'BANNER'

   ▲  CAPTURE THE PEAK  ::  player shell
   -------------------------------------------------
   Your downloadable camp files are in   ~/camps/
   The cracking wordlist is at           ~/peak-mini.txt
   Tools inside: tshark steghide exiftool binwalk imagemagick
                 zbarimg john hashcat fcrackzip curl strings ltrace
                 xxd openssl python3
   Keep pasted commands to ONE line.
   Submit flags back in the portal (:8000).
   -------------------------------------------------

BANNER
cd ~/camps 2>/dev/null || true
