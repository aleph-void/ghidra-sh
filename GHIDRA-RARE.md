# Hitachi/Renesas SH-3, SH-3E and SH-2E for Ghidra

SLEIGH processor module for three SuperH cores Ghidra does not ship (SH-1, SH-2, SH-2A and SH-4
are Ghidra's own). Target: **Ghidra 12.1.4**; also compiles and passes its tests on 12.1.3 and
12.2. Based on [will07c5/ghidra-sh](https://github.com/will07c5/ghidra-sh) (MIT), rewritten and
verified by Ghidra-Rare. See [CREDITS.md](CREDITS.md) for provenance and the list of changes.

## Languages

| ID | Core |
|---|---|
| `sh3:BE:32:default`, `sh3:LE:32:default` | SH-3 (SH-2 instruction set plus SSR/SPC, register banks, SHAD/SHLD, PREF, LDTLB, CLRS/SETS) |
| `sh3e:BE:32:default`, `sh3e:LE:32:default` | SH-3E: SH-3 plus FR0-FR15, FPUL, FPSCR and the single-precision FPU (FSQRT included) |
| `sh2e:BE:32:default` | SH-2E: SH-2 plus the same FPU without FSQRT; SR has no MD/RB/BL |

Loading: ELF `e_machine` 42 with `e_flags` SH3 (3, 0x14, 0x16), SH3E (8, 0x18), SH2E (11); PE
machine types 0x1a2 and 0x1a4 (Windows CE, little endian). Compiler spec: the GCC ABI (R4-R7 and,
on the E cores, FR4-FR7 for arguments, stack arguments from offset 0, results in R0/FR0). DWARF
register numbers as gcc emits them. ELF relocations are applied by Ghidra's own SuperH handler
(it handles R_SH_RELATIVE, GLOB_DAT, JMP_SLOT, DIR32 etc. for these languages as well). The
*SuperH PLT Stubs* analyzer makes every PLT stub a thunk of its import, so calls show the
imported name instead of `FUN_xxxxxxxx`.

## Semantics

P-code throughout; operations left as pcodeops: `sleep` (SLEEP) and `load_tlb` (LDTLB), which
act on power-mode and TLB state. PREF is a no-op. SR is split into the flags T, S, Q, M, IMASK
(and MD, RB, BL, FD) with exact LDC/STC/RTE composition; switching RB exchanges R0-R7 with
R0_BANK-R7_BANK, so `Rn_BANK` is always the inactive bank. Delay slots latch their condition or
target first. FTRC saturates; FMAC is fused (computed in 80-bit precision). TRAPA/RTE follow
each core: vector table and stack on the SH-2E; TRA/EXPEVT/SSR/SPC and VBR+0x100 on the SH-3.

## How to test

`GHIDRA_INSTALL_DIR=<ghidra with this directory linked under Ghidra/Processors/SH3>
test/run-tests.sh [--real <workdir>]` (details in the script header). Needs GNU binutils with the
sh target (`OBJDUMP`), and for the optional steps an sh-elf gcc/binutils (`SH_TOOLS`), the
sh4-linux-gnu / sh4eb-linux-gnu linkers, `qemu-sh4`/`qemu-sh4eb`. Steps that lack a tool are
skipped and say so.

## Results

| Area | Result |
|---|---|
| Builds | All five `.slaspec` compile on Ghidra 12.1.3, 12.1.4 and 12.2; `.sla` 12-15 KB each. Release zips: `tools/build-module.sh --standard --name SH3` |
| Decode vs GNU objdump 2.45 (`-m sh2e`, `sh3`, `sh3e`), **all 65,536 words** in each of the 5 languages | sh2e BE: 16,888 exact + 40,704 semantic + 7,944 invalid in both; sh3 BE/LE: 15,755 + 39,168 + 10,613; sh3e BE/LE: 18,075 + 40,704 + 6,757. **0 unexplained, 0 explained differences.** "Semantic" = same instruction spelled differently (hex vs decimal numbers, `@(addr,PC)` vs bare address, `bt/s` vs `bt.s`, `fmov.s` vs `fmov`) |
| Every-entry | **174/174** (SH-2E), **162/162** (SH-3), **193/193** (SH-3E) constructors reached |
| Emulator, hand-computed (`test/emu/cases.py`, code encoded with GNU as) | 128 cases (SH-2E), 119 (SH-3, each byte order), 142 (SH-3E, each byte order): ALU and flags, MAC/DIV/DMUL, shifts, every addressing mode, delay slots (taken, not taken, condition and target latching), BSR/JSR/BRAF/BSRF/RTS, SR/bank switching, RTE/TRAPA, FPU. **All pass.** One deliberately wrong expectation is reported in every language. Five source mutations (compare operand order, delay-slot latching, NEGC carry, SHAD fill, BSR's PR) were each caught |
| State differential vs QEMU 10.2.1 user mode (`test/qemu`) | 677,080 random instruction/state vectors (every straight-line word the oracle accepts, 4 states each; R0-R14, T, MAC, GBR, PR, FPUL, FR0-FR15 and 256 bytes of memory compared): 676,305 identical, 775 explained (below), **0 unexplained** |
| Real third-party code: NetBSD 10.1 sh3el/sh3eb `ls`, `awk`, `ksh`, `ld.elf_so`, `libm`, `libz`, `libc`, `libcrypto` | 16 files (8 per byte order) auto-detected as `sh3:LE/BE` (ELF flags 0x16); 2,445,755 analysed instructions, every one identical to objdump at the same address (0 unexplained); decompilation (20 s limit): 43,811 functions succeed, 0 fail, 2 time out; relocations all APPLIED. (NetBSD's `bzip2` is flagged SH-2 and goes to Ghidra's SuperH4, as it should) |
| Real code built with the free toolchain: zlib 1.3.1 and Lua 5.4.7 + newlib, for SH-3 LE/BE, SH-3E LE/BE and SH-2E BE | 10 static ELF files, auto-detected as the right language; 29-108 thousand instructions each, all identical to objdump; all functions decompile (0 failures, 0 timeouts at 20 s) |
| Spec files | cspec with `<global>` and GCC prototype, pspec, `.dwarf` (checked against gcc 14.3 `-g` on 3 languages: prototypes, `float` arguments in FR4/FR5, stack arguments at Stack[0x0]/[0x4]), ELF/PE opinions (ELF checked on gcc output for the 3 cores, PE on synthetic files), relocations of a `-fPIC` shared object (DIR32, GLOB_DAT, JMP_SLOT, GOT) applied and PLT stub thunked |
| Upstream before the rewrite | does not compile with Ghidra 12.1.4; with one label added, 18,658 of 65,536 words differ from objdump and 46 of the 119 emulator cases fail |

### Explained QEMU differences (`test/qemu/qemu-explained.txt`)

Of the 677,080 vectors, 4 classes (all accepted individually in the file):

- `rotl`/`rotr`: QEMU never sets T (the manual: the rotated-out bit goes to T; covered by the
  emulator cases `rotl_rotr`, `rotcr_t_out`). **QEMU bug.**
- `mac.w`/`mac.l` with Rm = Rn: QEMU loads both operands before post-incrementing; the manual's
  pseudo-code reads and increments Rn, then Rm (the module). No hardware to settle it.
- `div1` with a zero divisor, and with Rm = Rn: QEMU's T differs; the module equals an
  independent transcription of the manual's pseudo-code, and the 99.99% other cases agree.

### Confirmed bugs in reference tools

- QEMU 10.2.1 `qemu-sh4`/`qemu-sh4eb`: ROTL and ROTR leave T = 0.
- GNU objdump: none found. It accepts FSQRT on `sh3e` (the module follows it; see Unverified).

## Doesn't work (and why)

- SLEEP and LDTLB are pcodeops (power mode and TLB are hardware state).
- Not modelled: FPSCR rounding mode, FP flags/cause/enable and exceptions, denormal behaviour
  (p-code has no rounding control); SR.FD/BL/MD effects (privileged-instruction and FPU-disabled
  exceptions), address errors, interrupts, the MMU and the memory-mapped on-chip registers other
  than TRA/EXPEVT written by TRAPA.
- Remaining items of the upstream list, out of scope: SH-DSP and SH3-DSP instructions (a different
  core with its own parallel formats; objdump supports `-m sh3-dsp` for a later module), SH-4/4A
  instructions (Ghidra's `SuperH4`), SH-2A (Ghidra's `SuperH`).
- Bad-instruction bookmarks: lua has 79-89 per build and zlib 1, NetBSD `awk` 15; all but a few
  are literal-pool words after a `jsr`/`bsrf` to a function that Ghidra had not yet proved
  non-returning (for example `luaD_throw`); the rest are further pool words in the same chain.
  They are data, objdump comparison is clean, and the flow is Ghidra's.
- Relocatable objects (`.o`) import with Ghidra's SuperH handler, which does not support
  R_SH_GOT32/PLT32/GOTPC and ignores the in-place addend of R_SH_DIR32 (an SH quirk of the
  relocation format). Linked executables and shared objects are fine; this is in Ghidra core.
- Decompiler: tail-call stubs show "Could not recover jumptable ... Treating indirect jump as
  call" when the target register is set before the function fragment Ghidra created.

## Unverified

- Hardware behaviour: no SH-3/SH-2E hardware or full-system simulator was available. The
  SH-3 exception model (RTE order of SR restore and delay slot, TRAPA, bank switching) follows
  the manuals and is tested only against hand-computed cases. Same for the SR reserved bits
  (SH-3 `0x700003f3`, SH-3E `0x700083f3` with FD), the FPSCR width (`0x3ffff`) and FTRC of NaN
  (`0x7fffffff`); QEMU is an SH-4 model and cannot confirm them.
- FSQRT on the SH-3E is accepted because objdump and GCC accept it; it is not on the SH-2E.
- MAC.W/MAC.L when Rm = Rn (see above).
- PE support only on synthetic files (no freely licensed Windows CE SH-3 binary).
- No third-party SH-2E or SH-3E binary: those cores were exercised with self-built code and QEMU.
- FMAC rounding on exotic operands (extended intermediate, a double rounding is theoretically
  possible); agrees with QEMU's fused result on all random vectors.
