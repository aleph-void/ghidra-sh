#!/usr/bin/env python3
"""Emulator cases for the SH-3 / SH-3E / SH-2E modules.

Each case is a short assembly program (encoded by GNU as 2.45, sh-elf, used only as an encoder;
nothing from binutils is copied) plus register/memory expectations worked out by hand from the
Hitachi SH-3/SH-3E/SH-2E programming manuals.  Expected values are literals written here, never
produced by the module.

    cases.py > cases.txt            all cases
    cases.py --broken > bad.txt     the same with one deliberately wrong expectation (the harness
                                    must report exactly that case)

Run-time layout: the code is placed at ram:00001000 and runs until the PC reaches the symbol
main_end (default: the end of the code); data lives around ram:2000; R15 starts at 8000h.
Code is written as 16-bit words; the harness stores them in the language's byte order.
Variants: all = SH-2E, SH-3, SH-3E; fpu = SH-2E and SH-3E; sh3 = SH-3 and SH-3E.
"""
import os
import struct
import subprocess
import sys
import tempfile

TOOLS = os.environ.get("SH_TOOLS", os.path.expanduser("~/.cache/ghidra-rare-scratch/tools/x-sh-elf/bin"))
AS = os.path.join(TOOLS, "sh-elf-as")
NM = os.path.join(TOOLS, "sh-elf-nm")
OBJCOPY = os.path.join(TOOLS, "sh-elf-objcopy")

LANGS = {"all": "sh2e sh3 sh3e", "fpu": "sh2e sh3e", "sh3": "sh3 sh3e", "sh2e": "sh2e",
         "sh3e": "sh3e", "sh3plain": "sh3"}
CASES = []
BASE = 0x1000


def F(x):
    return struct.unpack(">I", struct.pack(">f", x))[0]


def case(name, asm, sets=(), expect=(), langs="all", isa=None):
    CASES.append((name, asm, list(sets), list(expect), langs, isa))


def assemble(asm, isa):
    d = tempfile.mkdtemp(prefix="shcase", dir=os.environ.get("TMPDIR"))
    src = os.path.join(d, "a.s")
    open(src, "w").write(".text\n" + asm + "\n")
    subprocess.check_call([AS, "-isa=" + isa, "-big", src, "-o", d + "/a.o"])
    subprocess.check_call([OBJCOPY, "-O", "binary", "-j", ".text", d + "/a.o", d + "/a.bin"])
    code = open(d + "/a.bin", "rb").read()
    syms = {}
    for line in subprocess.check_output([NM, d + "/a.o"]).decode().splitlines():
        p = line.split()
        if len(p) == 3:
            syms[p[2]] = int(p[0], 16) + BASE
    return code, syms


def val(v, syms):
    return v(syms) if callable(v) else v


# ---------------------------------------------------------------- arithmetic
case("add_overflow_keeps_t", "add r1,r2", [("R1", 0x7fffffff), ("R2", 1), ("T", 1)],
     [("R2", 0x80000000), ("T", 1)])
case("add_imm_negative", "add #-3,r2", [("R2", 2)], [("R2", 0xffffffff)])
case("addc_carry_in_and_out", "addc r1,r2", [("R1", 0xffffffff), ("R2", 0), ("T", 1)],
     [("R2", 0), ("T", 1)])
case("addc_no_carry", "addc r1,r2", [("R1", 3), ("R2", 5), ("T", 1)], [("R2", 9), ("T", 0)])
case("addc_carry_from_add", "addc r1,r2", [("R1", 0xffffffff), ("R2", 2), ("T", 0)],
     [("R2", 1), ("T", 1)])
case("addv_overflow", "addv r1,r2", [("R1", 1), ("R2", 0x7fffffff), ("T", 0)],
     [("R2", 0x80000000), ("T", 1)])
case("addv_carry_without_overflow", "addv r1,r2", [("R1", 0xffffffff), ("R2", 1), ("T", 1)],
     [("R2", 0), ("T", 0)])
case("sub_keeps_t", "sub r1,r2", [("R1", 5), ("R2", 3), ("T", 1)], [("R2", 0xfffffffe), ("T", 1)])
case("subc_borrow", "subc r1,r2", [("R1", 5), ("R2", 3), ("T", 0)], [("R2", 0xfffffffe), ("T", 1)])
case("subc_t_in_no_borrow", "subc r1,r2", [("R1", 3), ("R2", 5), ("T", 1)], [("R2", 1), ("T", 0)])
case("subc_borrow_from_t", "subc r1,r2", [("R1", 0), ("R2", 0), ("T", 1)],
     [("R2", 0xffffffff), ("T", 1)])
case("subv_overflow", "subv r1,r2", [("R1", 1), ("R2", 0x80000000), ("T", 0)],
     [("R2", 0x7fffffff), ("T", 1)])
case("subv_no_overflow", "subv r1,r2", [("R1", 3), ("R2", 5), ("T", 1)], [("R2", 2), ("T", 0)])
case("neg", "neg r1,r2", [("R1", 5)], [("R2", 0xfffffffb)])
case("negc_zero_with_t", "negc r1,r2", [("R1", 0), ("T", 1)], [("R2", 0xffffffff), ("T", 1)])
case("negc_nonzero", "negc r1,r2", [("R1", 1), ("T", 0)], [("R2", 0xffffffff), ("T", 1)])
case("negc_zero", "negc r1,r2", [("R1", 0), ("T", 0)], [("R2", 0), ("T", 0)])
case("cmp_eq_imm_sign_extended", "cmp/eq #-5,r0", [("R0", 0xfffffffb), ("T", 0)], [("T", 1)])
case("cmp_eq_imm_not_zero_extended", "cmp/eq #-5,r0", [("R0", 0xfb), ("T", 1)], [("T", 0)])
case("cmp_signedness", """cmp/hs r1,r2
movt r3
cmp/ge r1,r2
movt r4
cmp/hi r1,r2
movt r5
cmp/gt r1,r2
movt r6""", [("R1", 1), ("R2", 0xffffffff)],
     [("R3", 1), ("R4", 0), ("R5", 1), ("R6", 0)])
case("cmp_equal_operands", """cmp/hs r1,r2
movt r3
cmp/ge r1,r2
movt r4
cmp/hi r1,r2
movt r5
cmp/gt r1,r2
movt r6
cmp/eq r1,r2
movt r7""", [("R1", 7), ("R2", 7)],
     [("R3", 1), ("R4", 1), ("R5", 0), ("R6", 0), ("R7", 1)])
case("cmp_operand_order", """cmp/gt r1,r2
movt r3
cmp/gt r2,r1
movt r4""", [("R1", 3), ("R2", 5)], [("R3", 1), ("R4", 0)])
case("cmp_pl_pz", """cmp/pl r1
movt r4
cmp/pz r1
movt r5
cmp/pl r2
movt r6
cmp/pz r2
movt r7
cmp/pl r3
movt r8
cmp/pz r3
movt r9""", [("R1", 0), ("R2", 0x80000000), ("R3", 1)],
     [("R4", 0), ("R5", 1), ("R6", 0), ("R7", 0), ("R8", 1), ("R9", 1)])
case("cmp_str", """cmp/str r1,r2
movt r5
cmp/str r3,r4
movt r6""", [("R1", 0x11223344), ("R2", 0xaa22bbcc), ("R3", 0x01020304), ("R4", 0x05060708)],
     [("R5", 1), ("R6", 0)])
case("dt", """dt r1
movt r3
dt r2
movt r4""", [("R1", 1), ("R2", 0)], [("R1", 0), ("R3", 1), ("R2", 0xffffffff), ("R4", 0)])
case("extend", """exts.b r1,r2
extu.b r1,r3
exts.w r4,r5
extu.w r6,r7""", [("R1", 0x000000ff), ("R4", 0x00008000), ("R6", 0x12348000)],
     [("R2", 0xffffffff), ("R3", 0xff), ("R5", 0xffff8000), ("R7", 0x8000)])
case("mul_l", "mul.l r1,r2", [("R1", 0x10000), ("R2", 0x10001), ("MACH", 0x55)],
     [("MACL", 0x00010000), ("MACH", 0x55)])
case("dmulu_l", "dmulu.l r1,r2", [("R1", 0xffffffff), ("R2", 0xffffffff)],
     [("MACH", 0xfffffffe), ("MACL", 1)])
case("dmuls_l_small", "dmuls.l r1,r2", [("R1", 0xffffffff), ("R2", 2)],
     [("MACH", 0xffffffff), ("MACL", 0xfffffffe)])
case("dmuls_l_pow2", "dmuls.l r1,r2", [("R1", 0xffff0000), ("R2", 0x10000)],
     [("MACH", 0xffffffff), ("MACL", 0)])
case("muls_w", "muls.w r1,r2", [("R1", 0x1234ffff), ("R2", 3)], [("MACL", 0xfffffffd)])
case("mulu_w", "mulu.w r1,r2", [("R1", 0xffff), ("R2", 0x12340003)], [("MACL", 0x2fffd)])
case("clrmac", "clrmac", [("MACH", 5), ("MACL", 6)], [("MACH", 0), ("MACL", 0)])

MW = [("ram:2000/2", 3), ("ram:2010/2", 4), ("R1", 0x2000), ("R2", 0x2010)]
case("mac_w_accumulates_64_bit", "mac.w @r1+,@r2+", MW + [("S", 0), ("MACH", 1), ("MACL", 0xfffffff0)],
     [("MACH", 1), ("MACL", 0xfffffffc), ("R1", 0x2002), ("R2", 0x2012)])
case("mac_w_negative", "mac.w @r1+,@r2+",
     [("ram:2000/2", 0xfffe), ("ram:2010/2", 5), ("R1", 0x2000), ("R2", 0x2010), ("S", 0),
      ("MACH", 0), ("MACL", 0)], [("MACH", 0xffffffff), ("MACL", 0xfffffff6)])
case("mac_w_saturating_no_overflow", "mac.w @r1+,@r2+",
     MW + [("S", 1), ("MACH", 0), ("MACL", 0x7ffffff0)], [("MACH", 0), ("MACL", 0x7ffffffc)])
case("mac_w_saturating_positive", "mac.w @r1+,@r2+",
     [("ram:2000/2", 0x7fff), ("ram:2010/2", 0x7fff), ("R1", 0x2000), ("R2", 0x2010), ("S", 1),
      ("MACH", 0), ("MACL", 0x7ffffff0)], [("MACH", 1), ("MACL", 0x7fffffff)])
case("mac_w_saturating_negative", "mac.w @r1+,@r2+",
     [("ram:2000/2", 0xfffd), ("ram:2010/2", 4), ("R1", 0x2000), ("R2", 0x2010), ("S", 1),
      ("MACH", 0), ("MACL", 0x80000000)], [("MACH", 1), ("MACL", 0x80000000)])
ML = [("R1", 0x2000), ("R2", 0x2010)]
case("mac_l_accumulates", "mac.l @r1+,@r2+",
     ML + [("ram:2000/4", 6), ("ram:2010/4", 7), ("S", 0), ("MACH", 0), ("MACL", 0x10)],
     [("MACH", 0), ("MACL", 0x3a), ("R1", 0x2004), ("R2", 0x2014)])
case("mac_l_negative", "mac.l @r1+,@r2+",
     ML + [("ram:2000/4", 0xfffffffe), ("ram:2010/4", 5), ("S", 0), ("MACH", 0), ("MACL", 0)],
     [("MACH", 0xffffffff), ("MACL", 0xfffffff6)])
case("mac_l_full_64_bit", "mac.l @r1+,@r2+",
     ML + [("ram:2000/4", 0x7fffffff), ("ram:2010/4", 0x7fffffff), ("S", 0), ("MACH", 0), ("MACL", 0)],
     [("MACH", 0x3fffffff), ("MACL", 1)])
case("mac_l_saturates_48_bit_positive", "mac.l @r1+,@r2+",
     ML + [("ram:2000/4", 0x7fffffff), ("ram:2010/4", 0x7fffffff), ("S", 1), ("MACH", 0),
           ("MACL", 0)], [("MACH", 0x7fff), ("MACL", 0xffffffff)])
case("mac_l_saturates_48_bit_negative", "mac.l @r1+,@r2+",
     ML + [("ram:2000/4", 0x80000000), ("ram:2010/4", 0x7fffffff), ("S", 1), ("MACH", 0),
           ("MACL", 0)], [("MACH", 0xffff8000), ("MACL", 0)])

DIV16 = """shll16 r0
div0u
""" + "div1 r0,r1\n" * 16 + """rotcl r1
extu.w r1,r1"""
case("div_unsigned_32_by_16_a", DIV16, [("R0", 20), ("R1", 1000000)], [("R1", 50000)])
case("div_unsigned_32_by_16_b", DIV16, [("R0", 7), ("R1", 100)], [("R1", 14)])
case("div_unsigned_32_by_16_c", DIV16, [("R0", 0xffff), ("R1", 0xfffe0001)], [("R1", 0xffff)])
case("div0s_flags", "div0s r1,r2", [("R1", 0x80000000), ("R2", 0x7fffffff), ("T", 0), ("Q", 1), ("M", 0)],
     [("M", 1), ("Q", 0), ("T", 1)])
case("div0s_same_sign", "div0s r1,r2", [("R1", 0x80000000), ("R2", 0x80000000)],
     [("M", 1), ("Q", 1), ("T", 0)])
case("div0u_clears", "div0u", [("M", 1), ("Q", 1), ("T", 1)], [("M", 0), ("Q", 0), ("T", 0)])

# ---------------------------------------------------------------- logic and shifts
case("and_or_xor_not", """and r1,r2
or r1,r3
xor r1,r4
not r1,r5""", [("R1", 0xff00ff00), ("R2", 0x12345678), ("R3", 0x00ff00ff), ("R4", 0xffff0000)],
     [("R2", 0x12005600), ("R3", 0xffffffff), ("R4", 0x00ffff00), ("R5", 0x00ff00ff)])
case("logic_imm_zero_extended", """and #0xf0,r0
mov r0,r1
mov #1,r0
or #0x80,r0
mov r0,r2
mov #-1,r0
xor #0xff,r0""", [("R0", 0x12345678)], [("R1", 0x70), ("R2", 0x81), ("R0", 0xffffff00)])
case("tst", """tst r1,r2
movt r5
tst #1,r0
movt r6
tst #2,r0
movt r7""", [("R1", 0xf0), ("R2", 0x0f), ("R0", 2)], [("R5", 1), ("R6", 1), ("R7", 0)])
case("swap_xtrct", """swap.b r1,r2
swap.w r1,r3
xtrct r1,r4""", [("R1", 0x12345678), ("R4", 0x5678ef01)],
     [("R2", 0x12347856), ("R3", 0x56781234), ("R4", 0x56785678)])
case("xtrct", "xtrct r1,r2", [("R1", 0x1234abcd), ("R2", 0x5678ef01)], [("R2", 0xabcd5678)])
case("movt", "movt r1", [("T", 1), ("R1", 0xffffffff)], [("R1", 1)])
case("tas_b_zero", "tas.b @r1", [("R1", 0x2000), ("ram:2000/1", 0)], [("T", 1), ("ram:2000/1", 0x80)])
case("tas_b_nonzero", "tas.b @r1", [("R1", 0x2000), ("ram:2000/1", 1)], [("T", 0), ("ram:2000/1", 0x81)])
case("gbr_logic_in_memory", """and.b #0x0f,@(r0,gbr)
or.b #0x80,@(r0,gbr)
mov #5,r0
xor.b #0xff,@(r0,gbr)
tst.b #0x0f,@(r0,gbr)
movt r3""", [("GBR", 0x2000), ("R0", 4), ("ram:2004/1", 0xab), ("ram:2005/1", 0xf0)],
     [("ram:2004/1", 0x8b), ("ram:2005/1", 0x0f), ("R3", 0)])
case("shll_shal_shlr", """shll r1
movt r4
shlr r2
movt r5
shal r3
movt r6""", [("R1", 0x80000001), ("R2", 3), ("R3", 0x40000000)],
     [("R1", 2), ("R4", 1), ("R2", 1), ("R5", 1), ("R3", 0x80000000), ("R6", 0)])
case("shar", """shar r1
movt r2""", [("R1", 0x80000001)], [("R1", 0xc0000000), ("R2", 1)])
case("fixed_shifts", """shll2 r1
shll8 r2
shll16 r3
shlr2 r4
shlr8 r5
shlr16 r6""", [("R1", 0x12345678), ("R2", 0x12345678), ("R3", 0x12345678), ("R4", 0x12345678),
               ("R5", 0x12345678), ("R6", 0x12345678)],
     [("R1", 0x48d159e0), ("R2", 0x34567800), ("R3", 0x56780000), ("R4", 0x048d159e),
      ("R5", 0x00123456), ("R6", 0x1234)])
case("rotl_rotr", """rotl r1
movt r3
rotr r2
movt r4""", [("R1", 0x80000001), ("R2", 3)], [("R1", 3), ("R3", 1), ("R2", 0x80000001), ("R4", 1)])
case("rotcl_rotcr", """rotcl r1
movt r4
rotcl r2
movt r5
rotcr r3
rotcr r6
movt r7""",
     [("R1", 0x80000000), ("R2", 0x40000000), ("R3", 0), ("R6", 1), ("T", 1)],
     [("R1", 1), ("R4", 1), ("R2", 0x80000001), ("R5", 0), ("R3", 0), ("R6", 0), ("R7", 1)])
case("rotcr_t_in", "rotcr r3", [("R3", 0), ("T", 1)], [("R3", 0x80000000), ("T", 0)])
case("rotcr_t_out", "rotcr r3", [("R3", 3), ("T", 0)], [("R3", 1), ("T", 1)])
case("shad_shld_left", """shad r1,r2
shld r1,r3""", [("R1", 4), ("R2", 0x80000001), ("R3", 0x80000001)],
     [("R2", 0x00000010), ("R3", 0x00000010)], langs="sh3")
case("shad_shld_right", """shad r1,r2
shld r1,r3""", [("R1", 0xfffffffc), ("R2", 0x80000010), ("R3", 0x80000010)],
     [("R2", 0xf8000001), ("R3", 0x08000001)], langs="sh3")
case("shad_shld_right_by_32", """shad r1,r2
shld r1,r3
shad r1,r4
shld r1,r5""", [("R1", 0xffffffe0), ("R2", 0x80000000), ("R3", 0x80000000), ("R4", 0x7fffffff),
                ("R5", 0x7fffffff)],
     [("R2", 0xffffffff), ("R3", 0), ("R4", 0), ("R5", 0)], langs="sh3")
case("shad_shld_count_masked", """shad r1,r2
shld r1,r3""", [("R1", 0x20), ("R2", 5), ("R3", 6)], [("R2", 5), ("R3", 6)], langs="sh3")
case("shad_shld_left_31", """shad r1,r2
shld r1,r3""", [("R1", 0x1f), ("R2", 1), ("R3", 1)], [("R2", 0x80000000), ("R3", 0x80000000)],
     langs="sh3")
# ---------------------------------------------------------------- moves
case("mov_imm", """mov #-1,r1
mov #0x7f,r2
mov #0x80,r3
mov r2,r4""", [], [("R1", 0xffffffff), ("R2", 0x7f), ("R3", 0xffffff80), ("R4", 0x7f)])
case("load_sign_extension", """mov.b @r1,r2
mov.w @r3,r4
mov.l @r5,r6""", [("R1", 0x2000), ("ram:2000/1", 0x80), ("R3", 0x2002), ("ram:2002/2", 0x8001),
                  ("R5", 0x2004), ("ram:2004/4", 0x80018002)],
     [("R2", 0xffffff80), ("R4", 0xffff8001), ("R6", 0x80018002)])
case("store_widths_keep_neighbours", """mov.b r1,@r2
mov.w r1,@r3
mov.l r1,@r4""", [("R1", 0x1234abcd), ("R2", 0x2000), ("R3", 0x2010), ("R4", 0x2020),
                  ("ram:2000/4", 0xffffffff), ("ram:2010/4", 0xffffffff), ("ram:2020/4", 0)],
     [("ram:2000/1", 0xcd), ("ram:2001/1", 0xff), ("ram:2010/2", 0xabcd), ("ram:2012/2", 0xffff),
      ("ram:2020/4", 0x1234abcd)])
case("post_increment_loads", """mov.b @r1+,r2
mov.w @r5+,r3
mov.l @r6+,r4""", [("R1", 0x2000), ("ram:2000/1", 0xf0), ("R5", 0x2010), ("ram:2010/2", 0x8001),
                   ("R6", 0x2020), ("ram:2020/4", 0x11223344)],
     [("R1", 0x2001), ("R5", 0x2012), ("R6", 0x2024), ("R2", 0xfffffff0), ("R3", 0xffff8001),
      ("R4", 0x11223344)])
case("pre_decrement_stores", """mov.b r1,@-r2
mov.w r3,@-r2
mov.l r4,@-r2""", [("R2", 0x2010), ("R1", 0x11), ("R3", 0x2233), ("R4", 0x44556677)],
     [("R2", 0x2010 - 7), ("ram:200f/1", 0x11), ("ram:200d/2", 0x2233), ("ram:2009/4", 0x44556677)])
case("post_increment_into_itself", "mov.l @r1+,r1", [("R1", 0x2000), ("ram:2000/4", 0xcafe0001)],
     [("R1", 0xcafe0001)])
case("displacement_loads_scaled", """mov.l @(8,r1),r2
mov.w @(6,r1),r0
mov.b @(5,r1),r0
mov r0,r3""", [("R1", 0x2000), ("ram:2008/4", 0xdeadbeef), ("ram:2006/2", 0x8000), ("ram:2005/1", 0x81)],
     [("R2", 0xdeadbeef), ("R3", 0xffffff81)])
case("displacement_word_load", "mov.w @(6,r1),r0", [("R1", 0x2000), ("ram:2006/2", 0x8000)],
     [("R0", 0xffff8000)])
case("displacement_stores_scaled", """mov.l r2,@(8,r1)
mov.w r0,@(6,r1)
mov.b r0,@(5,r1)""", [("R1", 0x2000), ("R2", 0xdeadbeef), ("R0", 0x1234)],
     [("ram:2008/4", 0xdeadbeef), ("ram:2006/2", 0x1234), ("ram:2005/1", 0x34), ("ram:2004/1", 0)])
case("gbr_displacement_loads", """mov.l @(8,gbr),r0
mov r0,r1
mov.w @(6,gbr),r0
mov r0,r2
mov.b @(5,gbr),r0
mov r0,r3""", [("GBR", 0x2000), ("ram:2008/4", 0xdeadbeef), ("ram:2006/2", 0x8001), ("ram:2005/1", 0x80)],
     [("R1", 0xdeadbeef), ("R2", 0xffff8001), ("R3", 0xffffff80)])
case("gbr_displacement_stores", """mov.l r0,@(8,gbr)
mov.w r0,@(6,gbr)
mov.b r0,@(5,gbr)""", [("GBR", 0x2000), ("R0", 0x11223344)],
     [("ram:2008/4", 0x11223344), ("ram:2006/2", 0x3344), ("ram:2005/1", 0x44)])
case("indexed_loads", """mov.b @(r0,r1),r2
mov.w @(r0,r6),r3
mov.l @(r0,r7),r4""", [("R0", 0x10), ("R1", 0x2000), ("R6", 0x2100), ("R7", 0x2200),
                       ("ram:2010/1", 0x80), ("ram:2110/2", 0x8001), ("ram:2210/4", 0x80018002)],
     [("R2", 0xffffff80), ("R3", 0xffff8001), ("R4", 0x80018002)])
case("indexed_stores", """mov.b r2,@(r0,r1)
mov.w r3,@(r0,r6)
mov.l r4,@(r0,r7)""", [("R0", 0x10), ("R1", 0x2000), ("R6", 0x2100), ("R7", 0x2200), ("R2", 0x155),
                       ("R3", 0x16677), ("R4", 0x8899aabb), ("ram:2010/4", 0xffffffff),
                       ("ram:2110/4", 0xffffffff), ("ram:2210/4", 0xffffffff)],
     [("ram:2010/1", 0x55), ("ram:2011/1", 0xff), ("ram:2110/2", 0x6677), ("ram:2112/2", 0xffff),
      ("ram:2210/4", 0x8899aabb)])

case("pc_relative_literals", """mov.l lit,r1
mov.w wlit,r2
mova lit,r0
bra main_end
nop
.align 2
lit: .long 0
wlit: .word 0
main_end:""", [("ram:{lit}/4", 0x12345678), ("ram:{wlit}/2", 0x8001)],
     [("R1", 0x12345678), ("R2", 0xffff8001), ("R0", lambda s: s["lit"])])
case("pc_relative_unaligned_start", """nop
mov.l lit,r1
mova lit,r0
bra main_end
nop
.align 2
lit: .long 0
main_end:""", [("ram:{lit}/4", 0xcafebabe)], [("R1", 0xcafebabe), ("R0", lambda s: s["lit"])])
# ---------------------------------------------------------------- branches and delay slots
case("bra_executes_delay_slot", """bra L1
add #1,r1
add #100,r1
L1: add #10,r1""", [("R1", 0)], [("R1", 11)])
case("bt_taken", """sett
bt L1
add #1,r1
L1: add #10,r1""", [("R1", 0)], [("R1", 10)])
case("bt_not_taken", """clrt
bt L1
add #1,r1
L1: add #10,r1""", [("R1", 0)], [("R1", 11)])
case("bf_taken", """clrt
bf L1
add #1,r1
L1: add #10,r1""", [("R1", 0)], [("R1", 10)])
case("bf_not_taken", """sett
bf L1
add #1,r1
L1: add #10,r1""", [("R1", 0)], [("R1", 11)])
case("bt_s_taken_runs_slot", """sett
bt/s L1
add #1,r1
add #100,r1
L1: add #10,r1""", [("R1", 0)], [("R1", 11)])
case("bt_s_not_taken_runs_slot", """clrt
bt/s L1
add #1,r1
add #100,r1
L1: add #10,r1""", [("R1", 0)], [("R1", 111)])
case("bf_s_taken_runs_slot", """clrt
bf/s L1
add #1,r1
add #100,r1
L1: add #10,r1""", [("R1", 0)], [("R1", 11)])
case("bf_s_not_taken_runs_slot", """sett
bf/s L1
add #1,r1
add #100,r1
L1: add #10,r1""", [("R1", 0)], [("R1", 111)])
case("bt_s_condition_latched_before_slot", """sett
bt/s L1
clrt
add #100,r1
L1: movt r2""", [("R1", 0), ("R2", 9)], [("R1", 0), ("R2", 0), ("T", 0)])
case("bf_s_condition_latched_before_slot", """clrt
bf/s L1
sett
add #100,r1
L1: movt r2""", [("R1", 0), ("R2", 9)], [("R1", 0), ("R2", 1)])
case("bsr_rts_with_delay_slots", """bsr sub
add #1,r1
add #2,r1
bra main_end
nop
sub: add #4,r1
rts
add #8,r1
main_end:""", [("R1", 0)], [("R1", 15), ("PR", 0x1004)])
case("jsr_target_latched_before_slot", """jsr @r2
mov #0,r2
add #1,r1
bra main_end
nop
sub: add #4,r1
rts
nop
main_end:""", [("R1", 0), ("R2", lambda s: s["sub"])], [("R1", 5), ("PR", 0x1004), ("R2", 0)])
case("jmp_register", """jmp @r2
add #1,r1
add #100,r1
L1: add #10,r1""", [("R1", 0), ("R2", lambda s: s["L1"])], [("R1", 11)])
case("braf", """braf r2
add #1,r1
add #100,r1
L1: add #10,r1""", [("R1", 0), ("R2", lambda s: s["L1"] - (BASE + 4))], [("R1", 11)])
case("bsrf", """bsrf r2
add #1,r1
add #2,r1
bra main_end
nop
sub: add #4,r1
rts
add #8,r1
main_end:""", [("R1", 0), ("R2", lambda s: s["sub"] - (BASE + 4))], [("R1", 15), ("PR", 0x1004)])
case("rts_returns_to_pr", """rts
add #1,r1
add #100,r1
L1: add #10,r1""", [("R1", 0), ("PR", lambda s: s["L1"])], [("R1", 11)])
case("loop_with_dt_and_bf", """mov #5,r1
mov #0,r2
L1: add r1,r2
dt r1
bf L1""", [], [("R1", 0), ("R2", 15), ("T", 1)])

# ---------------------------------------------------------------- control registers
case("lds_sts_mac_pr", """lds r1,mach
lds r2,macl
lds r3,pr
sts mach,r4
sts macl,r5
sts pr,r6""", [("R1", 0x11), ("R2", 0x22), ("R3", 0x33)], [("R4", 0x11), ("R5", 0x22), ("R6", 0x33)])
case("ldc_stc_gbr_vbr", """ldc r1,gbr
ldc r2,vbr
stc gbr,r3
stc vbr,r4""", [("R1", 0xaaaa0000), ("R2", 0xbbbb0000)],
     [("GBR", 0xaaaa0000), ("VBR", 0xbbbb0000), ("R3", 0xaaaa0000), ("R4", 0xbbbb0000)])
case("ldc_l_stc_l_sts_l_lds_l", """stc.l gbr,@-r1
sts.l pr,@-r1
sts.l mach,@-r1
sts.l macl,@-r1
ldc.l @r1+,vbr
lds.l @r1+,mach
lds.l @r1+,macl
lds.l @r1+,pr""", [("R1", 0x2010), ("GBR", 0x01), ("PR", 0x02), ("MACH", 0x03), ("MACL", 0x04),
                   ("VBR", 0), ("ram:2000/4", 0)],
     [("R1", 0x2010), ("ram:200c/4", 0x01), ("ram:2008/4", 0x02), ("ram:2004/4", 0x03),
      ("ram:2000/4", 0x04), ("VBR", 0x04), ("MACH", 0x03), ("MACL", 0x02), ("PR", 0x01)])
case("sr_compose_decompose", """ldc r1,sr
stc sr,r2
stc.l sr,@-r3
ldc.l @r3+,sr""", [("R1", 0x000003f3), ("R3", 0x2010)],
     [("T", 1), ("S", 1), ("Q", 1), ("M", 1), ("IMASK", 0xf), ("R2", 0x3f3), ("R3", 0x2010),
      ("ram:200c/4", 0x3f3)])
case("sr_bits_individually", """ldc r1,sr
stc sr,r2""", [("R1", 0x00000250)], [("T", 0), ("S", 0), ("Q", 0), ("M", 1), ("IMASK", 5), ("R2", 0x250)])
case("sr_sets_flags_sett_clrt", """sett
stc sr,r1
clrt
stc sr,r2""", [("S", 0), ("IMASK", 0)], [("R1", 1), ("R2", 0)])
case("sr_reserved_bits_read_zero", """ldc r1,sr
stc sr,r2""", [("R1", 0xffffffff)], [("R2", 0x000003f3)], langs="sh2e")
case("sr_reserved_bits_read_zero_sh3", """ldc r8,sr
stc sr,r9""", [("R8", 0xffffffff), ("RB", 0)], [("R9", 0x700003f3)], langs="sh3plain")
case("sr_all_bits_sh3e", """ldc r8,sr
stc sr,r9""", [("R8", 0xffffffff), ("RB", 0)], [("R9", 0x700083f3), ("FD", 1)], langs="sh3e")
# ---------------------------------------------------------------- SH-3 system registers and banks
case("ssr_spc_roundtrip", """ldc r1,ssr
ldc r2,spc
stc ssr,r3
stc spc,r4
stc.l ssr,@-r5
stc.l spc,@-r5
ldc.l @r5+,ssr
ldc.l @r5+,spc""", [("R1", 0x12345678), ("R2", 0x9abcdef0), ("R5", 0x2010)],
     [("R3", 0x12345678), ("R4", 0x9abcdef0), ("ram:200c/4", 0x12345678), ("ram:2008/4", 0x9abcdef0),
      ("SSR", 0x9abcdef0), ("SPC", 0x12345678), ("R5", 0x2010)], langs="sh3")
case("bank_registers_are_the_other_bank", """ldc r8,r3_bank
stc r3_bank,r9
ldc.l @r10+,r5_bank
stc.l r5_bank,@-r11""", [("R8", 0xabcd0001), ("R10", 0x2000), ("ram:2000/4", 0x77), ("R11", 0x2020),
                          ("R3", 3), ("R5", 5)],
     [("R3_BANK", 0xabcd0001), ("R9", 0xabcd0001), ("R5_BANK", 0x77), ("R10", 0x2004),
      ("ram:201c/4", 0x77), ("R11", 0x201c), ("R3", 3), ("R5", 5)], langs="sh3")
case("rb_change_swaps_banks", """ldc r8,sr
stc r3_bank,r9
stc sr,r10""", [("R8", 0x20000000), ("R3", 7), ("R3_BANK", 9), ("R0", 1), ("R0_BANK", 2),
                ("R7", 17), ("R7_BANK", 18), ("RB", 0)],
     [("R3", 9), ("R3_BANK", 7), ("R9", 7), ("R0", 2), ("R0_BANK", 1), ("R7", 18), ("R7_BANK", 17),
      ("RB", 1), ("R10", 0x20000000)], langs="sh3")
case("rb_unchanged_keeps_banks", """ldc r8,sr""", [("R8", 0x20000000), ("R3", 7), ("R3_BANK", 9), ("RB", 1)],
     [("R3", 7), ("R3_BANK", 9), ("RB", 1)], langs="sh3")
case("sr_privileged_bits", """ldc r8,sr
stc sr,r9""", [("R8", 0x50000003), ("RB", 0), ("MD", 0), ("BL", 0)],
     [("MD", 1), ("RB", 0), ("BL", 1), ("R9", 0x50000003), ("T", 1), ("S", 1)], langs="sh3")
case("fd_bit_in_sr", """ldc r8,sr
stc sr,r9""", [("R8", 0x00008000)], [("FD", 1), ("R9", 0x00008000)], langs="sh3e")
case("sets_clrs", """sets
stc sr,r1
clrs
stc sr,r2""", [("S", 0)], [("R1", 2), ("R2", 0)], langs="sh3")
case("rte_sh3_restores_sr_and_pc", """rte
nop
add #100,r1
L1: add #10,r1""", [("R1", 0), ("SPC", lambda s: s["L1"]), ("SSR", 0x000000f3)],
     [("R1", 10), ("T", 1), ("S", 1), ("IMASK", 0xf), ("Q", 0), ("M", 0)], langs="sh3")
case("rte_sh3_switches_bank", """rte
nop
add #100,r1
L1: add #10,r1""", [("R1", 0), ("SPC", lambda s: s["L1"]), ("SSR", 0x20000001), ("R0", 1), ("R0_BANK", 2),
                    ("RB", 0), ("MD", 1)],
     [("R1", 10), ("R0", 2), ("R0_BANK", 1), ("RB", 1), ("MD", 0), ("T", 1)], langs="sh3")
case("trapa_sh3_enters_vbr_plus_100", """trapa #5
add #1,r1
bra main_end
nop
.org 0x100
stc spc,r8
stc ssr,r9
rte
nop
main_end:""", [("R1", 0), ("VBR", 0x1000), ("T", 1), ("RB", 0), ("MD", 0), ("BL", 0), ("R8", 0), ("R9", 0),
               ("IMASK", 3)],
     [("R1", 1), ("ram:ffffffd0/4", 20), ("ram:ffffffd4/4", 0x160), ("R8", 0x1002),
      ("R9", 0x00000031)], langs="sh3")
case("trapa_sh2_pushes_sr_and_pc", """trapa #3
add #1,r1
bra main_end
nop
.org 0x100
add #7,r1
rte
nop
main_end:""", [("R1", 0), ("VBR", 0x2000), ("T", 1), ("IMASK", 5), ("R15", 0x8000),
               ("ram:200c/4", BASE + 0x100)],
     [("R1", 8), ("R15", 0x8000), ("ram:7ff8/4", 0x1002), ("ram:7ffc/4", 0x51)], langs="sh2e")
case("rte_sh2_pops_pc_then_sr", """rte
add #1,r1
add #100,r1
L1: add #10,r1""", [("R1", 0), ("R15", 0x7ff0), ("ram:7ff0/4", lambda s: s["L1"]), ("ram:7ff4/4", 0x000000f3)],
     [("R1", 11), ("R15", 0x7ff8), ("T", 1), ("S", 1), ("IMASK", 0xf), ("Q", 0), ("M", 0)], langs="sh2e")

# ---------------------------------------------------------------- floating point
FP = "fpu"
case("fadd", "fadd fr1,fr2", [("FR1", F(1.5)), ("FR2", F(2.25))], [("FR2", F(3.75)), ("FR1", F(1.5))], langs=FP)
case("fsub_operand_order", "fsub fr1,fr2", [("FR1", F(0.5)), ("FR2", F(2.0))], [("FR2", F(1.5))], langs=FP)
case("fmul", "fmul fr1,fr2", [("FR1", F(3.0)), ("FR2", F(2.5))], [("FR2", F(7.5))], langs=FP)
case("fdiv_operand_order", "fdiv fr1,fr2", [("FR1", F(4.0)), ("FR2", F(1.0))], [("FR2", F(0.25))], langs=FP)
case("fmac", "fmac fr0,fr1,fr2", [("FR0", F(2.0)), ("FR1", F(3.0)), ("FR2", F(4.0))], [("FR2", F(10.0))], langs=FP)
case("fcmp_eq_gt", """fcmp/eq fr1,fr2
movt r3
fcmp/gt fr1,fr2
movt r4
fcmp/gt fr2,fr1
movt r5""", [("FR1", F(1.0)), ("FR2", F(2.0))], [("R3", 0), ("R4", 1), ("R5", 0)], langs=FP)
case("fcmp_equal_values", """fcmp/eq fr1,fr2
movt r3
fcmp/gt fr1,fr2
movt r4""", [("FR1", F(-2.0)), ("FR2", F(-2.0))], [("R3", 1), ("R4", 0)], langs=FP)
case("fcmp_nan_is_false", """fcmp/eq fr1,fr2
movt r3
fcmp/gt fr1,fr2
movt r4
fcmp/gt fr2,fr1
movt r5""", [("FR1", 0x7fc00000), ("FR2", F(1.0)), ("R3", 7), ("R4", 7), ("R5", 7)],
     [("R3", 0), ("R4", 0), ("R5", 0)], langs=FP)
case("fneg_fabs", """fneg fr1
fabs fr2
fneg fr3""", [("FR1", F(1.5)), ("FR2", F(-1.5)), ("FR3", 0)], [("FR1", F(-1.5)), ("FR2", F(1.5)), ("FR3", 0x80000000)],
     langs=FP)
case("float_and_ftrc", """lds r1,fpul
float fpul,fr2
fneg fr2
ftrc fr2,fpul
sts fpul,r3""", [("R1", 3)], [("FR2", F(-3.0)), ("R3", 0xfffffffd)], langs=FP)
case("float_negative_int", """lds r1,fpul
float fpul,fr2""", [("R1", 0xfffffffe)], [("FR2", F(-2.0))], langs=FP)
case("ftrc_truncates_toward_zero", """ftrc fr1,fpul
sts fpul,r3
ftrc fr2,fpul
sts fpul,r4""", [("FR1", F(2.5)), ("FR2", F(-2.5))], [("R3", 2), ("R4", 0xfffffffe)], langs=FP)
case("ftrc_saturates", """ftrc fr1,fpul
sts fpul,r3
ftrc fr2,fpul
sts fpul,r4
ftrc fr5,fpul
sts fpul,r6""", [("FR1", F(4294967296.0)), ("FR2", F(-4294967296.0)), ("FR5", 0x7fc00000)],
     [("R3", 0x7fffffff), ("R4", 0x80000000), ("R6", 0x7fffffff)], langs=FP)
case("ftrc_exact_limits", """ftrc fr1,fpul
sts fpul,r3
ftrc fr2,fpul
sts fpul,r4""", [("FR1", F(2147483648.0)), ("FR2", F(-2147483648.0))],
     [("R3", 0x7fffffff), ("R4", 0x80000000)], langs=FP)
case("fldi", """fldi0 fr1
fldi1 fr2""", [("FR1", 0x12345678), ("FR2", 0)], [("FR1", 0), ("FR2", 0x3f800000)], langs=FP)
case("flds_fsts", """flds fr1,fpul
sts fpul,r2
fsts fpul,fr3""", [("FR1", 0xdeadbeef), ("FR3", 0)], [("R2", 0xdeadbeef), ("FR3", 0xdeadbeef)], langs=FP)
case("fmov_register", "fmov fr1,fr2", [("FR1", 0x40490fdb)], [("FR2", 0x40490fdb)], langs=FP)
case("fmov_loads", """fmov.s @r1,fr2
fmov.s @r1+,fr3
fmov.s @(r0,r4),fr5""", [("R1", 0x2000), ("R4", 0x2000), ("R0", 0x20), ("ram:2000/4", 0x3f800000),
                         ("ram:2020/4", 0x40000000)],
     [("FR2", 0x3f800000), ("FR3", 0x3f800000), ("R1", 0x2004), ("FR5", 0x40000000)], langs=FP)
case("fmov_stores", """fmov.s fr1,@r2
fmov.s fr1,@-r3
fmov.s fr1,@(r0,r4)""", [("FR1", 0x40490fdb), ("R2", 0x2000), ("R3", 0x2014), ("R4", 0x2000), ("R0", 0x30)],
     [("ram:2000/4", 0x40490fdb), ("R3", 0x2010), ("ram:2010/4", 0x40490fdb), ("ram:2030/4", 0x40490fdb)], langs=FP)
case("lds_sts_fpscr_masks_reserved_bits", """lds r1,fpscr
sts fpscr,r2
sts.l fpscr,@-r3
sts.l fpul,@-r3""", [("R1", 0xffffffff), ("R3", 0x2010), ("FPUL", 0x55)],
     [("R2", 0x3ffff), ("ram:200c/4", 0x3ffff), ("ram:2008/4", 0x55), ("R3", 0x2008)], langs=FP)
case("lds_l_fpul_fpscr", """lds.l @r1+,fpul
lds.l @r1+,fpscr""", [("R1", 0x2000), ("ram:2000/4", 0x1234), ("ram:2004/4", 0x20001)],
     [("FPUL", 0x1234), ("FPSCR", 0x20001), ("R1", 0x2008)], langs=FP)
case("fsqrt", """fsqrt fr1""", [("FR1", F(16.0))], [("FR1", F(4.0))], langs="sh3e")


def emit(broken=False):
    out = ["# generated by test/emu/cases.py; do not edit"]
    for i, (name, asm, sets, expect, langs, isa) in enumerate(CASES):
        if isa is None:
            isa = {"sh2e": "sh2e", "fpu": "sh2e", "all": "sh2e", "sh3": "sh3", "sh3plain": "sh3",
                   "sh3e": "sh3e"}[langs]
        code, syms = assemble(asm, isa)
        if len(code) % 2:
            code += b"\0"
        words = " ".join("%02x%02x" % (code[j], code[j + 1]) for j in range(0, len(code), 2))
        mainlen = (syms["main_end"] - BASE) if "main_end" in syms else len(code)
        out.append("case %s langs %s" % (name, LANGS[langs]))
        out.append("code " + words)
        out.append("main %d" % mainlen)
        hs = {n: "%x" % a for n, a in syms.items()}
        for k, v in sets:
            out.append("set %s 0x%x" % (k.format(**hs), val(v, syms)))
        for j, (k, v) in enumerate(expect):
            v = val(v, syms)
            if broken and i == 0 and j == 0:
                v ^= 1  # the one wrong expectation
            out.append("expect %s 0x%x" % (k.format(**hs), v))
        out.append("end")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    sys.stdout.write(emit("--broken" in sys.argv))
