# Credits

## Upstream

This module is [will07c5/ghidra-sh](https://github.com/will07c5/ghidra-sh), "Very preliminary
SuperH processor plugin for Ghidra", imported at commit
`b2e7e0d10c282b00aad0eedb283c157e9bcdea6f` (2019-05-29, "Updating ldefs file to have SH1, SH2 and
SH3"; the repository has had no commits since). License: MIT (`LICENSE`, unchanged; the
copyright line "Copyright (c) 2019 William Hahne" stays in `data/languages/sh.sinc`).

Original author (from the upstream history, 6 commits, 2019-05-28 to 2019-05-29):

- William Hahne ([@will07c5](https://github.com/will07c5); git author names "Will Hahne" and
  "will07c5"): the module, its token layout and register model, the instruction table (written
  from http://www.shared-ptr.com/sh_insns.html) and the build setup.

Upstream files keep their copyright and license headers. Changes made here are also licensed
under the MIT License and exist as commits on top of the upstream history (branch
`ghidra-rare`).

Other SuperH work found while checking for alternatives (none is used here): Ghidra's own
`SuperH` (SH-1, SH-2, SH-2A) and `SuperH4` modules (Apache-2.0; their SLEIGH sources were not
read or copied; the language IDs of this fork do not collide with them),
[VGKintsugi/Ghidra-SegaSaturn-Processor](https://github.com/VGKintsugi/Ghidra-SegaSaturn-Processor)
(MIT, SH-2 only), and [PabloSoage/sh705x-emu](https://github.com/PabloSoage/sh705x-emu) (GPL-3.0,
an SH-2E ECU emulator, not a Ghidra module). No other SH-3 or SH-2E SLEIGH module exists on
GitHub as far as a search could find.

## Reference material

- *SH-3, SH-3E, SH-2E programming manuals* (Hitachi/Renesas): instruction descriptions,
  condition-bit behaviour, operation pseudo-code, register layouts. The SH-2E instructions (the
  FPU set) were written from the manual and checked against the oracle's output as a black box.
- GNU binutils 2.45 `objdump -m sh2e|sh3|sh3e` as the decode oracle, `sh-elf-as` to encode the
  emulator test programs, and a `sh-elf`, `sh4-linux-gnu` and `sh4eb-linux-gnu` binutils/gcc 14.3
  toolchain built from the GNU sources (with newlib 4.5) to produce test programs. binutils and
  gcc are GPL; nothing from them is copied into this module.
- QEMU 10.2.1 `qemu-sh4` / `qemu-sh4eb` (user mode) as an execution oracle for register state
  differentials. GPL, not copied.
- NetBSD 10.1 `evbsh3-sh3el` / `evbsh3-sh3eb` userland (BSD licence), zlib 1.3.1 and Lua 5.4.7 as
  real code; fetched or built by `test/fetch-samples.sh` / `test/build-samples.sh`, never committed.

## Ghidra-Rare changes

Commits on branch `ghidra-rare` (upstream `b2e7e0d..`):

1. Rewrite of the SLEIGH for the SH-3, SH-3E and SH-2E (`data/languages/sh.sinc`, the five
   `.slaspec` files); removal of the SH-1, SH-2 and SH-2A builds, which Ghidra provides.
   Fixes found by the tests (the original compiled only after adding a label, and then 18,658 of
   65,536 words decoded differently from objdump and 46 of 119 hand-computed emulator cases
   failed): compare operand order, carry/overflow flags of ADDC/ADDV/SUBC/SUBV/NEGC, DIV1 (including
   T) and the DIV1 label, MAC.W/MAC.L saturation and the overflow flag, SHAD/SHLD, SWAP.B, XTRCT,
   store widths and pre-decrement stores, scaled displacements, STS/LDS direction, MOVA, BT/S and
   BF/S, delay-slot latching, PR after BSR/JSR/BSRF, RTE, TRAPA, SLEEP (decoded as SETT), and the
   SH-3 features and the FPU listed in the commit message.
2. Language definitions and GCC-ABI compiler specs.
3. ELF/PE opinions, DWARF register mapping, and the PLT-stub analyzer (`SHPltAnalyzer`).
4. Build files (`build.gradle`, `extension.properties`), `.gitignore`, `README.md` updates, this
   file, `GHIDRA-RARE.md` and the test suite in `test/`.
