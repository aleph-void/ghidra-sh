#!/usr/bin/env bash
# DWARF and calling-convention check: builds test/elf/dwarf.c with the sh-elf gcc (-g -O1) for
# SH-3 (little endian), SH-3E (big endian) and SH-2E, imports each (auto-detected, DWARF
# applied) and checks the recovered prototypes and parameter storage.
#   SH_TOOLS=<sh-elf bin dir> test/dwarf-check.sh <workdir>
set -euo pipefail
: "${GHIDRA_INSTALL_DIR:?set GHIDRA_INSTALL_DIR}"
HERE=$(cd "$(dirname "$0")" && pwd)
W=$(readlink -m "$1"); mkdir -p "$W"
CC=${SH_TOOLS:-$HOME/.cache/ghidra-rare-scratch/tools/x-sh-elf/bin}/sh-elf-gcc
rc=0
expect() { grep -qF -- "$2" "$W/$1.protos.txt" || { echo "MISSING ($1): $2"; rc=1; }; }
for v in "sh3 -m3 -ml" "sh3e -m3e -mb" "sh2e -m2e -mb"; do
	set -- $v
	n=$1; shift
	"$CC" "$@" -g -O1 -nostdlib -nostartfiles -Wl,-e,__start -static -o "$W/dwarf_$n.elf" "$HERE/elf/dwarf.c" -lgcc
	"$HERE/ghidra-elf.sh" "$W/dwarf_$n.elf" DwarfCheck.java "$W/$n.protos.txt" 2>/dev/null
	"$HERE/ghidra-elf.sh" "$W/dwarf_$n.elf" LangId.java "$W/$n.lang.txt" 2>/dev/null
	echo "== $n: $(cat "$W/$n.lang.txt")"; cat "$W/$n.protos.txt"
	case $n in sh3) want="sh3:LE:32:default";; sh3e) want="sh3e:BE:32:default";; sh2e) want="sh2e:BE:32:default";; esac
	grep -q "^language: $want " "$W/$n.lang.txt" || { echo "WRONG LANGUAGE (want $want)"; rc=1; }
	expect $n "int add3(int a, int b, int c) | a@R4:4 | b@R5:4 | c@R6:4"
	expect $n "int sum(int * p, int n) | p@R4:4 | n@R5:4"
	expect $n "int field(pt * p) | p@R4:4"
	expect $n "int many(int a, int b, int c, int d, int e, int f) | a@R4:4 | b@R5:4 | c@R6:4 | d@R7:4 | e@Stack[0x0]:4 | f@Stack[0x4]:4"
	if [[ $n != sh3 ]]; then
		expect $n "float fmuladd(float a, float b) | a@FR4:4 | b@FR5:4"
	fi
done
exit $rc
