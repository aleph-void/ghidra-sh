#!/usr/bin/env bash
# QEMU user-mode differential: test/qemu/run-qemu.sh <workdir> [states-per-word] [seed]
# For SH-2E, SH-3, SH-3E (both byte orders where the language has them) it builds the runner
# for QEMU's sh4 user mode, runs every straight-line instruction the GNU objdump accepts for the
# architecture on random register/memory states, runs the same states in Ghidra's emulator and
# compares registers, T, MAC, GBR, PR, FPUL, FR0-FR15 and the scratch memory.
# Needs qemu-sh4/qemu-sh4eb, an sh-elf binutils (sh-elf-as/ld) and OBJDUMP.
set -euo pipefail
: "${GHIDRA_INSTALL_DIR:?set GHIDRA_INSTALL_DIR}"
HERE=$(cd "$(dirname "$0")" && pwd)
TESTDIR=$(dirname "$HERE")
W=$(readlink -m "$1"); N=${2:-2}; SEED=${3:-1}
TOOLS=${SH_TOOLS:-$HOME/.cache/ghidra-rare-scratch/tools/x-sh-elf/bin}
AS=$TOOLS/sh-elf-as; LD=$TOOLS/sh-elf-ld
LDF="-e _start -z max-page-size=0x1000 --section-start=.rwtext=0x400000 --section-start=.data=0x402000 --section-start=.scratch=0x10000000 --no-warn-rwx-segments"
mkdir -p "$W"
head -c 65536 /dev/zero >"$W/zero.bin"
rc=0
for c in sh2e:BE sh3:BE sh3:LE sh3e:BE sh3e:LE; do
	proc=${c%%:*}; e=${c##*:}
	if [[ $e == BE ]]; then end=big; Q=qemu-sh4eb; M=shelf; else end=little; Q=qemu-sh4; M=shlelf; fi
	tag=${proc}_$e
	python3 "$HERE/gen_vectors.py" $proc $end "$W/v_$tag" $N $SEED
	cp "$W/v_$tag.bin" "$W/vectors.bin"
	(cd "$W" && "$AS" -isa=sh4 -$end "$HERE/runner.S" -o "r_$tag.o" && "$LD" -m $M $LDF "r_$tag.o" -o "r_$tag.elf")
	"$Q" "$W/r_$tag.elf" >"$W/q_$tag.out"
	P=$(mktemp -d "${TMPDIR:-/tmp}/sh-qemu.XXXXXX")
	"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" "$P" p -import "$W/zero.bin" -loader BinaryLoader \
		-processor "$proc:$e:32:default" -noanalysis -scriptPath "$TESTDIR" \
		-postScript SHEmuState.java "$W/v_$tag.txt" "$W/g_$tag.out" -deleteProject >"$P/log.txt" 2>&1 \
		|| { tail -30 "$P/log.txt" >&2; rm -rf "$P"; exit 1; }
	rm -rf "$P"
	echo "== $proc $e"
	NOFPU=0; [[ $proc == sh3 ]] && NOFPU=1
	SH_NOFPU=$NOFPU python3 -I "$HERE/compare_state.py" $end "$W/v_$tag.txt" "$W/g_$tag.out" "$W/q_$tag.out" "$W/v_$tag.labels" \
		"$HERE/qemu-explained.txt" || rc=1
	rm -f "$W/v_$tag.bin" "$W/q_$tag.out"
done
exit $rc
