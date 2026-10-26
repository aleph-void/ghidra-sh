#!/usr/bin/env bash
# SH-3 / SH-3E / SH-2E module test suite.  Exits non-zero on any failure.
#   GHIDRA_INSTALL_DIR=<ghidra with this module installed under Ghidra/Processors/SH3>
#       test/run-tests.sh [--real <workdir>]
# Steps: 1 the five specs compile (and each .sla is under 16 MB); 2 the Java builds; 3 the
# hand-computed emulator cases pass in all five languages and a deliberately broken expectation
# is reported; 4 every SLEIGH constructor is reached; 5 exhaustive decode differential (all
# 65,536 words per language) against GNU objdump with 0 unexplained differences; 6 state
# differential against QEMU user mode (when qemu-sh4 and an sh-elf toolchain are present);
# 7 DWARF/ABI, relocation and PE checks (needs the sh-elf gcc and, for relocations, the
# sh4-linux-gnu linkers); with --real, 8 NetBSD 10.1 sh3el/sh3eb binaries and zlib/Lua built with
# the sh-elf gcc: auto-detected import, analysis, decompilation, objdump comparison.
# Tools: OBJDUMP (binutils with the sh target; GNU binutils 2.45 built with all targets),
# SH_TOOLS (dir with sh-elf-gcc/as/ld), SH_LINUX_LD_LE / SH_LINUX_LD_BE, qemu-sh4 / qemu-sh4eb.
set -uo pipefail
: "${GHIDRA_INSTALL_DIR:?set GHIDRA_INSTALL_DIR}"
HERE=$(cd "$(dirname "$0")" && pwd)
MOD=$(cd "$HERE/.." && pwd)
REAL=""
[[ ${1:-} == --real ]] && REAL=$(readlink -m "${2:?--real needs a workdir}")
export OBJDUMP=${OBJDUMP:-$HOME/.cache/ghidra-rare-scratch/tools/binutils-all/bin/objdump}
export SH_TOOLS=${SH_TOOLS:-$HOME/.cache/ghidra-rare-scratch/tools/x-sh-elf/bin}
W=$(mktemp -d "${TMPDIR:-/tmp}/sh3-tests.XXXXXX")
trap 'rm -rf "$W"' EXIT
fail=0
step() { echo; echo "### $*"; }
check() { if "$@"; then echo "ok"; else echo "FAILED: $*"; fail=1; fi; }

step "1 SLEIGH compile"
for f in sh3 sh3_le sh3e sh3e_le sh2e; do
	check "$GHIDRA_INSTALL_DIR/support/sleigh" "$MOD/data/languages/$f.slaspec" "$W/$f.sla"
	sz=$(stat -c %s "$W/$f.sla" 2>/dev/null || echo 0)
	echo "$f.sla $sz bytes"
	(( sz > 0 && sz < 16000000 )) || { echo "FAILED: $f.sla size"; fail=1; }
done

step "2 Java (PLT analyzer)"
check "$HERE/build-jar.sh"

step "3 emulator cases"
check "$HERE/emu-test.sh" "$W/emu"
check "$HERE/emu-test.sh" --broken "$W/emu"

step "4 every constructor reached"
check "$HERE/every-entry.sh" "$W/every"

step "5 exhaustive decode differential vs objdump"
check "$HERE/run-decode.sh" "$W/dec"

step "6 state differential vs QEMU user mode"
if command -v qemu-sh4 >/dev/null && command -v qemu-sh4eb >/dev/null && [[ -x $SH_TOOLS/sh-elf-as ]]; then
	check "$HERE/qemu/run-qemu.sh" "$W/qemu" 4 7
else
	echo "skipped: needs qemu-sh4, qemu-sh4eb and $SH_TOOLS/sh-elf-as"
fi

step "7 DWARF / ABI, relocations, PE opinion"
if [[ -x $SH_TOOLS/sh-elf-gcc ]]; then
	check "$HERE/dwarf-check.sh" "$W/dwarf"
	LDLE=${SH_LINUX_LD_LE:-$HOME/.cache/ghidra-rare-scratch/tools/x-sh-linux/bin/sh4-linux-gnu-ld}
	LDBE=${SH_LINUX_LD_BE:-$HOME/.cache/ghidra-rare-scratch/tools/x-sh-linux-eb/bin/sh4eb-linux-gnu-ld}
	if [[ -x $LDLE && -x $LDBE ]]; then
		check "$HERE/reloc-check.sh" "$W/reloc"
	else
		echo "skipped relocations: needs $LDLE and $LDBE"
	fi
else
	echo "skipped: no sh-elf-gcc in $SH_TOOLS"
fi
check "$HERE/pe-check.sh" "$W/pe"

if [[ -n $REAL ]]; then
	step "8 real code"
	mkdir -p "$REAL"
	check "$HERE/fetch-samples.sh" "$REAL"
	real() {   # <file> <language> <objdump arch>
		echo "== $1"
		check "$HERE/real-check.sh" "$1" "$REAL/out" "$2" "$3" 20
	}
	for e in el:LE eb:BE; do
		d=$REAL/netbsd-sh3${e%%:*}/x; l=sh3:${e##*:}:32:default
		for f in bin/ls usr/bin/awk libexec/ld.elf_so lib/libm.so.0.13 lib/libz.so.1.0 bin/ksh lib/libc.so.12.220.1; do
			real "$d/$f" "$l" sh3
		done
	done
	check "$HERE/build-samples.sh" "$REAL/self"
	for n in sh3le:sh3:LE:sh3 sh3be:sh3:BE:sh3 sh3ele:sh3e:LE:sh3e sh3ebe:sh3e:BE:sh3e sh2ebe:sh2e:BE:sh2e; do
		IFS=: read -r tag proc end arch <<<"$n"
		for p in zlib lua; do
			real "$REAL/self/elf/${p}_$tag.elf" "$proc:$end:32:default" $arch
		done
	done
fi

echo
if (( fail )); then echo "SOME TESTS FAILED"; exit 1; fi
echo "all tests passed"
