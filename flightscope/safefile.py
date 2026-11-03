"""Writes that survive the power being cut (the panel switch kills power instantly): write a temp file,
fsync it, rename it over the old one, fsync the directory. A reader sees the old file or the new one, never half."""
from __future__ import annotations
import os, shutil
from pathlib import Path

def _sync_dir(d: Path):
    fd = os.open(d, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)

def write_text(path: Path, text: str):
    path = Path(path); tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as f:
        f.write(text); f.flush(); os.fsync(f.fileno())
    tmp.replace(path); _sync_dir(path.parent)

def copy_file(src, dst: Path):
    dst = Path(dst); tmp = dst.with_suffix(dst.suffix + ".tmp")
    with open(src, "rb") as a, open(tmp, "wb") as b:
        shutil.copyfileobj(a, b); b.flush(); os.fsync(b.fileno())
    tmp.replace(dst); _sync_dir(dst.parent)

def remove(path: Path):
    path = Path(path); path.unlink(); _sync_dir(path.parent)
