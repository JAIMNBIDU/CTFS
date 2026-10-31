#!/usr/bin/env bash
# =====================================================================
#  CTF-00 : BOSS FLAG verifier   //   Rungta Cyber Security Club
#  Checks the user/group/ownership structure the player was asked to
#  build. Prints the BOSS flag only if everything is correct.
#  Run it (no sudo needed to READ the state):   bash ctf_verify.sh
# =====================================================================
BASE="$HOME/ctf-00"
DIR="$BASE/restricted/ops"
ok=1

check(){ if eval "$1"; then printf '  [+] %s\n' "$2"; else printf '  [-] %s\n' "$3"; ok=0; fi; }

echo "== BOSS checks =="
check "getent group redteam >/dev/null"              "group 'redteam' exists"            "group 'redteam' is missing"
check "id analyst >/dev/null 2>&1"                   "user 'analyst' exists"             "user 'analyst' is missing"
check "id -nG analyst 2>/dev/null | grep -qw redteam" "analyst is in the redteam group"   "analyst is NOT in redteam (usermod -aG)"
check "[ -d '$DIR' ]"                                 "$DIR exists"                       "$DIR is missing (mkdir -p)"

own=$(stat -c '%U:%G' "$DIR" 2>/dev/null)
check "[ \"$own\" = 'analyst:redteam' ]"              "owner:group is analyst:redteam"    "owner:group is '${own:-none}', want analyst:redteam (chown)"

mode=$(stat -c '%a' "$DIR" 2>/dev/null)
check "[ \"$mode\" = '770' ] || [ \"$mode\" = '2770' ]" "mode is $mode (770/2770)"       "mode is '${mode:-none}', want 770 or 2770 (chmod)"

echo
if [ "$ok" = "1" ]; then
  echo "  *** ALL CHECKS PASS ***"
  echo "  BOSS FLAG:  RCSC{y0u_4r3_r00t_n0w}"
else
  echo "  Not there yet. Fix the [-] lines above and run me again."
fi
