#!/usr/bin/env bash
# Every-entry test: test/every-entry.sh <workdir>
# Decodes all 65536 words in each language and lists the SLEIGH constructors no word used.
# Exits non-zero when any constructor is never reached.
set -euo pipefail
: "${GHIDRA_INSTALL_DIR:?set GHIDRA_INSTALL_DIR}"
HERE=$(cd "$(dirname "$0")" && pwd)
W=$(readlink -m "$1")
mkdir -p "$W"
rc=0
for c in sh2e:BE:big sh3:BE:big sh3:LE:little sh3e:BE:big sh3e:LE:little; do
	IFS=: read -r proc e end <<<"$c"
	tag=${proc}_$e
	python3 "$HERE/gen_words.py" "$W/$tag.bin" $end
	P=$(mktemp -d "${TMPDIR:-/tmp}/sh-ee.XXXXXX")
	"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" "$P" p -import "$W/$tag.bin" -loader BinaryLoader \
		-loader-baseAddr 0 -processor "$proc:$e:32:default" -noanalysis -scriptPath "$HERE" \
		-postScript EveryEntry.java "$W/$tag.every.txt" 2 default -deleteProject >"$P/log.txt" 2>&1 \
		|| { tail -40 "$P/log.txt" >&2; rm -rf "$P"; exit 1; }
	rm -rf "$P"
	echo "== $proc $e"
	grep -E "NOT REACHED|^every-entry" "$W/$tag.every.txt"
	grep -q " 0 not reached" "$W/$tag.every.txt" || rc=1
done
exit $rc
