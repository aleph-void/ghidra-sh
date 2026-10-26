#!/usr/bin/env bash
# Exhaustive decode differential: every 16-bit word, every language, against GNU objdump.
#   test/run-decode.sh <workdir>
# SH instructions are one 16-bit word, so "every encoding" is all 65536 words.  Exits non-zero
# on any difference not listed in test/decode-explained.txt.
set -euo pipefail
: "${GHIDRA_INSTALL_DIR:?set GHIDRA_INSTALL_DIR}"
HERE=$(cd "$(dirname "$0")" && pwd)
W=$(readlink -m "$1")
OBJDUMP=${OBJDUMP:-objdump}
mkdir -p "$W"
rc=0
# language id : endianness : objdump -m
for c in sh2e:BE:big:sh2e:EB sh3:BE:big:sh3:EB sh3:LE:little:sh3:EL sh3e:BE:big:sh3e:EB sh3e:LE:little:sh3e:EL; do
	IFS=: read -r proc e end arch eo <<<"$c"
	tag=${proc}_$e
	python3 "$HERE/gen_words.py" "$W/$tag.bin" $end
	"$HERE/ghidra-dis.sh" "$proc:$e:32:default" "$W/$tag.bin" "$W/$tag.ghidra.txt" 2
	"$OBJDUMP" -D -b binary -m $arch -$eo "$W/$tag.bin" >"$W/$tag.objdump.txt"
	echo "== $proc $e (objdump -m $arch -$eo)"
	python3 -I "$HERE/compare.py" "$W/$tag.ghidra.txt" "$W/$tag.objdump.txt" "$HERE/decode-explained.txt" | tee "$W/$tag.cmp.txt" | head -20 || rc=1
	[[ ${PIPESTATUS[0]} == 0 ]] || rc=1
done
exit $rc
