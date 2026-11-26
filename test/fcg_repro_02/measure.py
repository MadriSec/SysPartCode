#!/usr/bin/env python3
"""Run the mode-23 fixture once and report peak child RSS on Linux."""

import resource
import subprocess
import sys
import time
from pathlib import Path


count = int(sys.argv[1])
here = Path(__file__).resolve().parent
binary = here / "build" / f"branches_{count}"
roots = here / "build" / "roots.txt"
syspart = here.parent.parent / "analysis" / "app" / "syspart"
if not binary.is_file() or not roots.is_file() or not syspart.is_file():
    raise SystemExit("Build the fixture and SysPart first")

out = here / "build" / f"mode23_{count}.out"
err = here / "build" / f"mode23_{count}.err"
start = time.monotonic()
with out.open("w") as stdout, err.open("w") as stderr:
    try:
        result = subprocess.run(
            [str(syspart), "-p", str(binary), "-s", str(roots), "-i", "-a", "23"],
            stdout=stdout,
            stderr=stderr,
            timeout=300,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise SystemExit(f"Timed out after 300 seconds; see {err}")

targets = set()
edges = 0
with out.open() as output:
    for line in output:
        fields = line.split()
        if len(fields) >= 6 and fields[0] == "INDIRECT_RESOLVED" and fields[3] == "main":
            edges += 1
            targets.add(fields[5])

print(f"exit={result.returncode} seconds={time.monotonic() - start:.2f} "
      f"peak_rss_kb={resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss} "
      f"main_resolved_edges={edges} unique_main_targets={len(targets)}")
print(f"stdout={out} stderr={err}")
if result.returncode:
    raise SystemExit(result.returncode)
