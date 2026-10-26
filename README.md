# ghidra-sh

Very preliminary SuperH processor plugin for Ghidra. Only supports SH2A at the moment but extending it to support at least SH1, SH2 and SH3 should be fairly easy. Expect lots of bugs! Code also needs a fair bit of cleanup.

*(the paragraph above is the original author's text, 2019; see "Status in this fork" for what is
true now)*

## Status in this fork (Ghidra-Rare)

This fork is verified for **Ghidra 12.1.4** (it also compiles and passes its tests on 12.1.3 and
12.2). It is a SuperH module for the three cores Ghidra does not ship, and no longer a
preliminary SH-2A one:

| Language ID | Core | Byte order |
|---|---|---|
| `sh3:BE:32:default`, `sh3:LE:32:default` | Hitachi/Renesas SH-3 | big, little |
| `sh3e:BE:32:default`, `sh3e:LE:32:default` | SH-3E (SH-3 + single-precision FPU, FSQRT) | big, little |
| `sh2e:BE:32:default` | SH-2E (SH-2 + single-precision FPU) | big |

SH-1, SH-2, SH-2A and SH-4 come with Ghidra (`SuperH:*`, `SuperH4:*`), so the fork's SH-1/SH-2/SH-2A
languages were removed; the old `sh1:BE:32:default`, `sh2:BE:32:default` and `sh2a:BE:32:default`
IDs no longer exist. The SLEIGH was rewritten (the original had 18,658 of 65,536 words decoding
differently from GNU objdump and did not compile with Ghidra 12.1.4); the original author's
register names, token layout and style are kept where they were right.

See [GHIDRA-RARE.md](GHIDRA-RARE.md) for what is covered and how it was tested,
[CREDITS.md](CREDITS.md) for provenance and the list of changes, and the repository's
**Releases** page for ready-built extension zips (Ghidra 12.1.3, 12.1.4, 12.2). Install with
*File > Install Extensions > +*. To build it yourself:
`GHIDRA_INSTALL_DIR=<ghidra> gradle buildExtension` (the `.sla` files are compiled by Ghidra on
first use when a source checkout is placed under `Ghidra/Processors/`).

### The original limitations, one by one

| Original statement or TODO | Now |
|---|---|
| "Only supports SH2A at the moment" | **Fixed.** SH-3, SH-3E and SH-2E; the SH-2A parts were dropped because Ghidra has an SH-2A (`SuperH:BE:32:SH-2A`) |
| "extending it to support at least SH1, SH2 and SH3 should be fairly easy" | **Done** for SH-3 (the SH-2 instructions it contains are in the SH-3 and SH-2E languages); SH-1 and SH-2 themselves are Ghidra's |
| "Expect lots of bugs!" | **Fixed** (found by the tests, list in CREDITS.md): operand order of the unsigned/signed compares, ADDC/ADDV/SUBC/SUBV/NEGC flags, DIV1, MAC.W/MAC.L saturation, SHAD/SHLD, SWAP.B, scaled displacements, BT/S and BF/S, PR values of BSR/JSR/BSRF, RTE, SLEEP decoded as SETT, STS/LDS direction, and others |
| "Code also needs a fair bit of cleanup" | **Done** for the files this fork keeps: one `sh.sinc` for all three cores, instruction semantics organised by manual section, no copy-pasted flag logic |
| `sh.cspec`: `extrapop="2" stackshift="2"`, stack arguments at offset 4 | **Fixed**: the GCC ABI (R4-R7 and FR4-FR7 for arguments, stack arguments from offset 0, caller pops, R0/FR0 results) |
| Does not compile with Ghidra 12 (`Label <if_4_end> was referenced but never placed` in DIV1) | **Fixed** |
| `# unimplemented` bodies: CLRS, SETS, LDTLB, PREF, SLEEP (SH-3 relevant) | **Fixed**: CLRS/SETS set S; LDTLB, PREF and SLEEP are the only operations left as p-code operations (`load_tlb`, `prefetch`, `sleep`): they act on hardware state (TLB, cache, power mode) that p-code cannot express |
| "Unimplemented DSP instructions" (MOD/RE/RS/DSR/A0/X0.. registers, LDRE, LDRS, SETRC, parallel moves) | **Remaining, out of scope**: these belong to the SH-DSP and SH3-DSP, different cores with their own 32-bit parallel instruction formats. GNU objdump disassembles them (`-m sh-dsp`, `-m sh3-dsp`), so a later module could be checked against it |
| "Unimplemented SH4A instructions" (MOVLI, MOVCO, MOVUA, ICBI, PREFI, SGR, DBR) and SH-4 cache operations | **Out of scope**: SH-4/SH-4A are Ghidra's `SuperH4` module |
| Bank registers, SSR, SPC, `Rn_BANK` ("SH4A: unimplemented ldc/stc Rn_BANK") | **Fixed for SH-3**: SSR, SPC, R0_BANK-R7_BANK and the RB bank switch (on LDC/RTE/TRAPA) |
| Floating point (not present in the original) | **Added** for SH-2E and SH-3E |
| No loader information (ELF/PE), no DWARF mapping | **Added**: ELF `e_flags` opinion for the three cores, PE machine types 0x1a2/0x1a4, DWARF register numbers, and an analyzer that names the PLT stubs of SH ELF files after their imports |
| No issues were open on the upstream repository | - |

## Original description

The original repository contained `data/languages/sh.sinc` (the SLEIGH for all four cores,
selected with `@define SH1/SH2/SH2A/SH3`), one `.slaspec` per core, the language definition,
compiler and processor specs. Everything is MIT licensed (Copyright (c) 2019 William Hahne /
will07c5).
