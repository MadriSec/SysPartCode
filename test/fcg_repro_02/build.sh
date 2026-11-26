#!/usr/bin/env bash
set -euo pipefail

# Build only: one indirect callsite with several statically possible targets.
count=${1:-4}
case $count in ''|*[!0-9]*) echo 'count must be a positive integer' >&2; exit 2;; esac
if (( count < 2 )); then
    echo 'count must be at least 2' >&2
    exit 2
fi

out="$(cd "$(dirname "$0")" && pwd)/build"
mkdir -p "$out"
src="$out/branches_${count}.c"
bin="${src%.c}"
{
    echo 'typedef void (*callback)(void);'
    for (( i = 0; i < count; i++ )); do
        printf '__attribute__((noinline, used)) void target_%d(void) { __asm__ volatile("" ::: "memory"); }\n' "$i"
    done
    echo 'int main(int argc, char **argv) {'
    echo '    (void)argv;'
    echo '    callback selected = target_0;'
    for (( i = 1; i < count; i++ )); do
        printf '    if (argc == %d) selected = target_%d;\n' "$((i + 1))" "$i"
    done
    echo '    selected();'
    echo '    return 0;'
    echo '}'
} > "$src"
printf 'main\n' > "$out/roots.txt"
gcc -O0 -g -fPIE -pie -Wl,--emit-relocs "$src" -o "$bin"
printf 'Built %s; roots: %s\n' "$bin" "$out/roots.txt"
