#!/usr/bin/env bash
# PE opinion check: writes minimal Windows CE style PE32 files with the SH-3 and SH-3E machine
# types (test/mkpe.py) and checks that an auto-detecting import picks the right language.
#   test/pe-check.sh <workdir>
set -euo pipefail
: "${GHIDRA_INSTALL_DIR:?set GHIDRA_INSTALL_DIR}"
HERE=$(cd "$(dirname "$0")" && pwd)
W=$(readlink -m "$1"); mkdir -p "$W"
rc=0
for c in "sh3 1a2 sh3:LE:32:default" "sh3e 1a4 sh3e:LE:32:default"; do
	set -- $c
	python3 "$HERE/mkpe.py" "$W/ce_$1.exe" $2
	"$HERE/ghidra-elf.sh" "$W/ce_$1.exe" LangId.java "$W/ce_$1.txt" 2>/dev/null
	cat "$W/ce_$1.txt"
	grep -q "^language: $3 " "$W/ce_$1.txt" || { echo "WRONG LANGUAGE (want $3)"; rc=1; }
done
exit $rc
