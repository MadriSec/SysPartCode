#!/usr/bin/env bash
set -euo pipefail

repo=$(cd "$(dirname "$0")/../.." && pwd)
out="$(cd "$(dirname "$0")" && pwd)/build"
if [[ -e "$out/app" ]]; then
    echo "A/B build already exists: $out/app" >&2
    exit 1
fi
if [[ ! -x "$repo/analysis/app/syspart" ]]; then
    echo "Build the baseline SysPart executable first" >&2
    exit 1
fi

mkdir -p "$out/tools"
ln -s "$repo/analysis/tools/egalito" "$out/tools/egalito"
cp -a "$repo/analysis/app" "$out/app"
cp "$repo/analysis/app/syspart" "$out/baseline-syspart"

python3 - "$out/app/src/ipcallgraph.cpp" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
old = '''    if (it != childrenMap.end()) {
        childrenMap[iaddr] = listManager.addChild(it -> second, t);
'''
new = '''    if (it != childrenMap.end()) {
        if (std::find(it->second->begin(), it->second->end(), t) != it->second->end())
            return;
        childrenMap[iaddr] = listManager.addChild(it -> second, t);
'''
text = source.read_text()
if text.count(old) != 1:
    raise SystemExit("Expected insertion point not found exactly once")
source.write_text(text.replace(old, new, 1))
PY

make -C "$out/app" -j1
printf 'Baseline: %s\nFixed: %s\n' "$out/baseline-syspart" "$out/app/syspart"
