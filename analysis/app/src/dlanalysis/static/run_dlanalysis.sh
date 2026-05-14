#!/bin/bash
#src/dlanalysis/static/run_dlanalysis.sh src/dlanalysis/binaries        

#BIN_PATH=$1
script_dir=$(dirname "$(realpath "$0")")
cd "$script_dir/../../../"
USE_LOADER=0 make
cd src/dlanalysis/static
BINARY=$1
DLOUT=$2        
echo "Dlanalysis for ${BINARY}"

resolve_dynsym() {
	local binary="$1"
	local default_sym="$2"
	local base_sym="${default_sym%%@*}"
	local resolved=""
	local libc_path=""

	# Syspart resolves libc symbols as exported by libc itself, typically with default '@@' versions.
	libc_path=$(ldd "$binary" 2>/dev/null | awk '/libc\.so/ {print $3; exit}')
	if [ -n "$libc_path" ] && command -v nm >/dev/null 2>&1; then
		resolved=$(nm -D "$libc_path" 2>/dev/null | awk -v b="$base_sym" '$NF ~ ("^" b "@@") { print $NF; exit }')
		if [ -z "$resolved" ]; then
			resolved=$(nm -D "$libc_path" 2>/dev/null | awk -v b="$base_sym" '$NF ~ ("^" b "@") { print $NF; exit }')
		fi
	fi

	if [ -n "$resolved" ]; then
		echo "$resolved"
	else
		echo "$default_sym"
	fi
}

dlopen_default=$(cat "$script_dir/../dlopen.txt")
dlsym_default=$(cat "$script_dir/../dlsym.txt")
dlopen=$(resolve_dynsym "$BINARY" "$dlopen_default")
dlsym=$(resolve_dynsym "$BINARY" "$dlsym_default")

"$script_dir/../../../syspart" -p "${BINARY}" -i -s main -a 6,"${dlopen}",7 > "$DLOUT/dlopen_static.txt" && echo OK

"$script_dir/../../../syspart" -p "${BINARY}" -i -s main -a 6,"${dlsym}",6 > "$DLOUT/dlsym_static.txt" && echo OK

python3 process_result.py "$DLOUT/dlopen_static.txt" "${dlopen}" > "$DLOUT/dlopen_args.txt" && echo OK

python3 process_result.py "$DLOUT/dlsym_static.txt" "${dlsym}" > "$DLOUT/dlsym_args.txt" && echo OK

"$script_dir/generate_libnames.sh" "${BINARY}" && echo OK

"$script_dir/match_libs_with_syms.sh" "$DLOUT/dlsym_args.txt" > "$DLOUT/libraries_matching_syms.txt" && echo OK
