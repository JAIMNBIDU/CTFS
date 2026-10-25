"""CAMP 10 CORNICE - a gatekeeper ELF; key in plaintext (strings/ltrace), flag XOR'd."""
import subprocess
KEY = "BELAY-ON-9000"
XOR = 0x5A
def build(ctx):
    enc = ",".join(str(b ^ XOR) for b in ctx.flag.encode())
    n = len(ctx.flag.encode())
    c = f'''#include <stdio.h>
#include <string.h>
static const char *key = "{KEY}";
static const unsigned char enc[] = {{{enc}}};
int main(int argc, char **argv) {{
    int n = {n};
    if (argc < 2) {{ printf("usage: ./gatekeeper <pass-phrase>\\n"); return 1; }}
    if (strcmp(argv[1], key) == 0) {{
        char out[256];
        for (int i = 0; i < n; i++) out[i] = enc[i] ^ {XOR};
        out[n] = 0;
        printf("%s\\n", out);
        return 0;
    }}
    printf("denied. the cornice holds.\\n");
    return 1;
}}'''
    src = ctx.stage_dir / "_gate.c"
    src.write_text(c)
    out = ctx.stage_dir / "gatekeeper"
    # -O0 -fno-builtin keeps strcmp a real libc call (ltrace sees it) and keeps
    # the key literal in .rodata (strings leaks it). -s strips symbol names only.
    r = subprocess.run(["gcc", "-O0", "-fno-builtin", "-s", "-o", str(out), str(src)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(
            "gcc failed to build the camp-10 gatekeeper. Usually means the builder "
            "image is missing C headers (install libc6-dev / build-essential).\n"
            f"gcc stderr:\n{r.stderr}")
    src.unlink()
    out.chmod(0o755)
