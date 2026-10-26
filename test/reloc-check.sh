#!/usr/bin/env bash
# Relocation check: builds test/elf/reloc.c and reloc_ext.c with the sh-elf gcc (-fPIC), links
# them into a shared object with the sh4-linux-gnu / sh4eb-linux-gnu linkers (binutils 2.45) (R_SH_DIR32, GLOB_DAT, JMP_SLOT, and
# the PLT/GOT code), imports it (auto-detected) for SH-3 (LE), SH-3E (BE) and SH-2E (BE) and
# checks that every relocation was applied, that the data pointers point at the right symbols
# and that the PLT stubs became thunks of the imports.
#   SH_TOOLS=<sh-elf bin dir> SH_LINUX_LD_LE=<sh4-linux-gnu-ld> SH_LINUX_LD_BE=<sh4eb-linux-gnu-ld> test/reloc-check.sh <workdir>
set -euo pipefail
: "${GHIDRA_INSTALL_DIR:?set GHIDRA_INSTALL_DIR}"
HERE=$(cd "$(dirname "$0")" && pwd)
W=$(readlink -m "$1"); mkdir -p "$W"
CC=${SH_TOOLS:-$HOME/.cache/ghidra-rare-scratch/tools/x-sh-elf/bin}/sh-elf-gcc
LDLE=${SH_LINUX_LD_LE:-$HOME/.cache/ghidra-rare-scratch/tools/x-sh-linux/bin/sh4-linux-gnu-ld}
LDBE=${SH_LINUX_LD_BE:-$HOME/.cache/ghidra-rare-scratch/tools/x-sh-linux-eb/bin/sh4eb-linux-gnu-ld}
rc=0
for v in "sh3 -m3 -ml shlelf_linux" "sh3e -m3e -mb shelf_linux" "sh2e -m2e -mb shelf_linux"; do
	set -- $v; n=$1; m1=$2; m2=$3; emu=$4
	"$CC" $m1 $m2 -O1 -fPIC -c "$HERE/elf/reloc.c" -o "$W/reloc_$n.o"
	"$CC" $m1 $m2 -O1 -fPIC -c "$HERE/elf/reloc_ext.c" -o "$W/reloc_ext_$n.o"
	LD=$LDBE; [[ $emu == shlelf_linux ]] && LD=$LDLE
	"$LD" -m $emu -shared -o "$W/reloc_$n.so" "$W/reloc_$n.o" "$W/reloc_ext_$n.o"
	"$HERE/ghidra-elf.sh" "$W/reloc_$n.so" RelocCheck.java "$W/$n.reloc.txt" 2>/dev/null
	echo "== $n"; cat "$W/$n.reloc.txt"
	grep -q WRONG "$W/$n.reloc.txt" && rc=1
	grep -q "FAILURE\|UNSUPPORTED" "$W/$n.reloc.txt" && rc=1
done
exit $rc
