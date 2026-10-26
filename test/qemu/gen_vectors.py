#!/usr/bin/env python3
"""Generate state-in vectors for the QEMU differential.

    gen_vectors.py <arch sh2e|sh3|sh3e> <big|little> <outprefix> [states-per-word] [seed]

The straight-line instructions of the architecture are the 16-bit words GNU objdump (-m <arch>)
accepts, minus control flow, privileged or PC-relative forms and anything that mentions r15.
Operand registers used as pointers are pointed into a 256-byte scratch area.  Writes
<outprefix>.txt (one hex line per vector, read by SHEmuState.java) and <outprefix>.bin (the
records for test/qemu/runner.S in the target byte order).
"""
import os
import random
import re
import struct
import subprocess
import sys

arch, endian, prefix = sys.argv[1], sys.argv[2], sys.argv[3]
nstates = int(sys.argv[4]) if len(sys.argv) > 4 else 2
rnd = random.Random(int(sys.argv[5]) if len(sys.argv) > 5 else 1)
OBJDUMP = os.environ.get("OBJDUMP", "objdump")
SCR = 0x10000000
E = ">" if endian == "big" else "<"

tmp = prefix + ".words.bin"
open(tmp, "wb").write(b"".join(struct.pack(">H", i) for i in range(65536)))
dis = subprocess.check_output([OBJDUMP, "-D", "-b", "binary", "-m", arch, "-EB", tmp]).decode()
os.remove(tmp)
text = {}
for line in dis.splitlines():
    m = re.match(r"\s*([0-9a-f]+):\t[0-9a-f ]+\t(.*)$", line)
    if m:
        t = re.sub(r"\s+", " ", m.group(2).split("\t! ")[0]).strip()
        text[int(m.group(1), 16) // 2] = t

CONTROL = re.compile(r"^(bra|bsr|bt|bf|braf|bsrf|jmp|jsr|rts|rte|trapa|sleep|ldtlb|pref|mova|sets|clrs)\b")
BAD = re.compile(r"\b(r15|pc|sr|ssr|spc|vbr)\b|_bank|,fpscr$")


def classify(w):
    t = text.get(w)
    if not t or t.startswith(".word"):
        return None
    if CONTROL.match(t) or BAD.search(t):
        return None
    if re.search(r"@\([0-9a-z]+,pc\)", t) or re.match(r"^mov\.[wl] 0x", t):
        return None
    ops = t.split(" ", 1)[1] if " " in t else ""
    ptr = set(int(x) for x in re.findall(r"@-?r(\d+)", ops))
    ptr |= set(int(x) for x in re.findall(r"@\(\d+,r(\d+)\)", ops))
    ptr |= set(int(x) for x in re.findall(r"@\(r0,r(\d+)\)", ops))
    gbr = None
    m = re.search(r"@\((\d+),gbr\)", ops)
    if m:
        gbr = int(m.group(1))
        if gbr > 124:
            return None
    if "@(r0,gbr)" in ops:
        gbr = 0
    idx0 = "@(r0," in ops
    return t, ptr, gbr, idx0


words = [(w, classify(w)) for w in range(65536)]
words = [(w, c) for w, c in words if c]
EDGE = [0, 1, 2, 3, 0x7f, 0x80, 0xff, 0x7fff, 0x8000, 0xffff, 0x10000, 0x7fffffff, 0x80000000,
        0x80000001, 0xfffffffe, 0xffffffff, 0x55555555, 0xaaaaaaaa, 0x12345678, 0xdeadbeef]


def rv():
    r = rnd.random()
    if r < 0.45:
        return rnd.choice(EDGE)
    if r < 0.6:
        return rnd.randrange(0, 64)
    if r < 0.7:
        return (-rnd.randrange(1, 64)) & 0xffffffff
    return rnd.getrandbits(32)


def fv():
    r = rnd.random()
    if r < 0.15:
        return rnd.choice([0x00000000, 0x80000000, 0x3f800000, 0xbf800000, 0x40000000, 0x3f000000])
    if r < 0.25:  # large, for ftrc saturation
        return struct.unpack(">I", struct.pack(">f", rnd.choice([1, -1]) * rnd.uniform(1e9, 1e10)))[0]
    if r < 0.55:  # small integers
        return struct.unpack(">I", struct.pack(">f", float(rnd.randrange(-100, 100))))[0]
    x = rnd.choice([1, -1]) * 10 ** rnd.uniform(-10, 10)
    return struct.unpack(">I", struct.pack(">f", x))[0]


with open(prefix + ".labels", "w") as lf:
    for w, (t, _p, _g, _i) in words:
        lf.write("%x %s\n" % (w, t))
txt = open(prefix + ".txt", "w")
binf = open(prefix + ".bin", "wb")
count = 0
for w, (t, ptr, gbr, idx0) in words:
    is_fp = bool(re.match(r"^f", t))
    for _ in range(nstates):
        regs = [rv() for _ in range(15)]
        for p in ptr:
            regs[p] = SCR + 64 + rnd.randrange(0, 9) * 4
        if idx0:
            regs[0] = rnd.randrange(0, 9) * 4
            if 0 in ptr:  # @(r0,r0): the address is twice r0
                regs[0] = (SCR + 64 + rnd.randrange(0, 9) * 4) // 2
        T, S, Q, M = (rnd.getrandbits(1) for _ in range(4))
        mach, macl, pr = rv(), rv(), rv()
        gb = rv()
        if gbr is not None:
            gb = SCR + 64 if "@(r0,gbr)" in t else SCR + rnd.randrange(0, 9) * 4
        fr = [fv() for _ in range(16)] if is_fp or rnd.random() < 0.1 else [0] * 16
        fpul = rv() if rnd.random() < 0.5 else fv()
        if not is_fp:
            fpul = 0
        rec = regs + [w, T, mach, macl, gb, pr, S, Q, M, fpul, 0] + fr
        txt.write(" ".join("%x" % x for x in rec) + "\n")
        # binary record: in1 (15 regs + insn), in2 (T MACH MACL GBR PR S Q M FPUL FPSCR), in3 FR
        b = struct.pack(E + "16I", *regs, w)
        # div0s r1,r0 sets Q from r0's msb and M from r1's msb; the runner reads them as words
        in2 = [T, mach, macl, gb, pr, S, Q << 31, M << 31, fpul, 0]
        b += struct.pack(E + "10I", *in2) + b"\0" * (64 - 40)
        b += struct.pack(E + "16I", *fr)
        b += b"\0" * (640 - len(b))
        binf.write(b)
        count += 1
txt.close()
binf.close()
print("%s %s: %d words, %d vectors" % (arch, endian, len(words), count), file=sys.stderr)
