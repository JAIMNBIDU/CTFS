"""Shared helpers for stage generators."""
import os
from pathlib import Path


class Ctx:
    def __init__(self, n, flag, all_flags, salt, out_root, event):
        self.n = n
        self.flag = flag
        self.all_flags = all_flags
        self.salt = salt
        self.out_root = Path(out_root)
        self.event = event
        self.stage_dir = self.out_root / "ctf" / f"stage{n:02d}"
        self.stage_dir.mkdir(parents=True, exist_ok=True)
        self.lab_flags = {}      # filled by web/pwn stages
        self.wordlist = set()    # filled by hashing stages

    def write(self, name, data):
        p = self.stage_dir / name
        if isinstance(data, bytes):
            p.write_bytes(data)
        else:
            p.write_text(data)
        return p
