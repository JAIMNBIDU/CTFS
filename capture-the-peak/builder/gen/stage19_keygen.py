"""CAMP 19 DEAD RECKONING - a keygen-me. The accepted serial is never stored;
it is BUILT at runtime from a per-index formula, so strings/grep reveal nothing.
The flag is XOR-obfuscated and only decoded when the serial is correct. Players
must reverse the compare loop to reproduce the serial.

Serial rule (16 chars):  valid[i] = 'A' + ((i*7 + 3) % 26)
"""
import subprocess

XOR = 0x5A


def _serial():
    return "".join(chr(ord("A") + ((i * 7 + 3) % 26)) for i in range(16))


def build(ctx):
    enc = ",".join(str(b ^ XOR) for b in ctx.flag.encode())
    n = len(ctx.flag.encode())
    c = f'''#include <stdio.h>
#include <string.h>
static const unsigned char enc[] = {{{enc}}};
int main(int argc, char **argv) {{
    int n = {n};
    if (argc < 2) {{ printf("usage: ./keygen <serial>\\n"); return 1; }}
    const char *s = argv[1];
    if (strlen(s) != 16) {{ printf("denied. the reckoning fails.\\n"); return 1; }}
    for (int i = 0; i < 16; i++) {{
        char expect = (char)('A' + ((i * 7 + 3) % 26));
        if (s[i] != expect) {{ printf("denied. the reckoning fails.\\n"); return 1; }}
    }}
    char out[256];
    for (int i = 0; i < n; i++) out[i] = enc[i] ^ {XOR};
    out[n] = 0;
    printf("%s\\n", out);
    return 0;
}}'''
    src = ctx.stage_dir / "_keygen.c"
    src.write_text(c)
    out = ctx.stage_dir / "keygen"
    # -O2 + strip: the serial formula is inlined (reversible via disasm), but
    # the serial string and the flag never appear in `strings`.
    r = subprocess.run(["gcc", "-O2", "-s", "-o", str(out), str(src)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gcc failed to build camp-19 keygen:\n{r.stderr}")
    src.unlink()
    out.chmod(0o755)
