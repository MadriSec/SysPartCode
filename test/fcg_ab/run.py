#!/usr/bin/env python3
"""Measure one SysPart version without retaining its potentially huge FCG."""

import argparse
import resource
import subprocess
import threading
import time
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("version", choices=("baseline", "fixed"))
parser.add_argument("elf", type=Path)
parser.add_argument("roots", type=Path, help="absolute path to a file of root function names")
args = parser.parse_args()
here = Path(__file__).resolve().parent
syspart = here / "build" / ("baseline-syspart" if args.version == "baseline" else "app/syspart")
if not syspart.is_file() or not args.elf.is_file() or not args.roots.is_file():
    parser.error("SysPart, ELF, or roots file is missing")
if not args.roots.is_absolute():
    parser.error("roots must be an absolute path for SysPart -s")

stderr_path = here / "build" / f"{args.version}.err"
start = time.monotonic()
bytes_out = lines_out = 0
timed_out = False
with stderr_path.open("w") as stderr:
    proc = subprocess.Popen(
        [str(syspart), "-p", str(args.elf.resolve()), "-s", str(args.roots), "-i", "-a", "23"],
        stdout=subprocess.PIPE,
        stderr=stderr,
    )

    def stop_on_timeout():
        global timed_out
        timed_out = True
        proc.kill()

    timer = threading.Timer(1800, stop_on_timeout)
    timer.start()
    try:
        for chunk in iter(lambda: proc.stdout.read(1024 * 1024), b""):
            bytes_out += len(chunk)
            lines_out += chunk.count(b"\n")
        return_code = proc.wait()
    finally:
        timer.cancel()
        proc.stdout.close()

print(f"version={args.version} exit={return_code} timeout={timed_out} "
      f"seconds={time.monotonic() - start:.2f} "
      f"peak_rss_kb={resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss} "
      f"fcg_lines={lines_out} fcg_bytes={bytes_out} stderr={stderr_path}")
