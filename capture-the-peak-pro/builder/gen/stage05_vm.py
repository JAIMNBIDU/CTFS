"""PRO CAMP 5 THE MACHINE THAT LIES - obfuscated keygen. The serial is checked
through a per-index transform against a baked-in table; neither the serial nor
the flag appear in `strings`. Reverse the transform to produce the serial.

Check (per index i, 0..15):  ((serial[i] ^ 0x3C) + i*5) & 0xFF == TABLE[i]
Inverse:                     serial[i] = ((TABLE[i] - i*5) & 0xFF) ^ 0x3C
"""
import subprocess

SERIAL = "PR0_V4ULT_K3Y_99"      # 16 chars
XOR = 0x5A


def _table():
    return [((ord(SERIAL[i]) ^ 0x3C) + i * 5) & 0xFF for i in range(16)]


def build(ctx):
    enc = ",".join(str(b ^ XOR) for b in ctx.flag.encode())
    n = len(ctx.flag.encode())
    tbl = ",".join(str(b) for b in _table())
    c = f'''#include <stdio.h>
#include <string.h>
static const unsigned char enc[] = {{{enc}}};
static const unsigned char TBL[16] = {{{tbl}}};
int main(int argc, char **argv) {{
    int n = {n};
    if (argc < 2) {{ printf("usage: ./vault_vm <serial>\\n"); return 1; }}
    const char *s = argv[1];
    if (strlen(s) != 16) {{ printf("rejected.\\n"); return 1; }}
    for (int i = 0; i < 16; i++) {{
        unsigned char r = (unsigned char)((((unsigned char)s[i] ^ 0x3C) + i * 5) & 0xFF);
        if (r != TBL[i]) {{ printf("rejected.\\n"); return 1; }}
    }}
    char out[256];
    for (int i = 0; i < n; i++) out[i] = enc[i] ^ {XOR};
    out[n] = 0;
    printf("%s\\n", out);
    return 0;
}}'''
    src = ctx.stage_dir / "_vm.c"
    src.write_text(c)
    out = ctx.stage_dir / "vault_vm"
    r = subprocess.run(["gcc", "-O2", "-s", "-o", str(out), str(src)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gcc failed for pro camp 5:\n{r.stderr}")
    src.unlink()
    out.chmod(0o755)
