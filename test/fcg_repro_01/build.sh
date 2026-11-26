#!/usr/bin/env bash
set -euo pipefail

# Build only. SysPart is deliberately invoked separately by the investigator.
targets=${1:-4}
sites=${2:-2}
case $targets in ''|*[!0-9]*) echo 'targets must be a positive integer' >&2; exit 2;; esac
case $sites in ''|*[!0-9]*) echo 'sites must be a positive integer' >&2; exit 2;; esac
if (( targets < 1 || sites < 1 )); then
    echo 'targets and sites must be positive' >&2
    exit 2
fi

out="$(cd "$(dirname "$0")" && pwd)/build"
mkdir -p "$out"
src="$out/at_${targets}_sites_${sites}.c"
bin="${src%.c}"

{
    echo 'typedef void (*callback)(void);'
    for (( i = 0; i < targets; i++ )); do
        printf '__attribute__((noinline, used)) void target_%d(void) { __asm__ volatile("" ::: "memory"); }\n' "$i"
    done
    printf '__attribute__((used)) callback candidates[] = {'
    for (( i = 0; i < targets; i++ )); do
        (( i == 0 )) || printf ', '
        printf 'target_%d' "$i"
    done
    printf '};\n'
    echo 'int main(void) {'
    echo '    callback volatile selected = candidates[0];'
    for (( i = 0; i < sites; i++ )); do
        echo '    selected();'
    done
    echo '    return 0;'
    echo '}'
} > "$src"

gcc -O0 -g -fno-pie -no-pie "$src" -o "$bin"
printf 'Built %s (targets=%s, indirect callsites=%s)\n' "$bin" "$targets" "$sites"
