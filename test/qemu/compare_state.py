#!/usr/bin/env python3
"""Compare Ghidra's state-out lines (SHEmuState.java) with QEMU's records.

    compare_state.py <endian> <vectors.txt> <ghidra.out> <qemu.out.bin> <objdump text prefix>

Both sides produce, per vector, R0..R14, T, MACH, MACL, GBR, PR, FPUL, FR0..FR15 and the scratch
bytes.  NaN results compare equal whatever their payload.  Differences are listed per
instruction mnemonic.
"""
import os
import re
import struct
import sys
from collections import Counter, defaultdict

endian, vecs, gout, qout = sys.argv[1:5]
# explained differences: "<mnemonic> <field|*> <any|rm==rn|rm=0> <reason>" per line
EXPL = []
if len(sys.argv) > 6:
    for line in open(sys.argv[6]):
        line = line.strip()
        if line and not line.startswith("#"):
            mn, field, cond, reason = line.split(None, 3)
            EXPL.append((mn, field, cond, reason))
explained_count = Counter()


def explained(mn, field, w, v):
    rn, rm = (w >> 8) & 15, (w >> 4) & 15
    for m, f, cond, reason in EXPL:
        if m == mn and (f == "*" or f == field) and (cond == "any" or (cond == "rm==rn" and rn == rm) or (cond == "rm=0" and int(v[rm], 16) == 0 and rn != rm)):
            return reason
    return None

E = ">" if endian == "big" else "<"
labels = {}
if len(sys.argv) > 5:
    for line in open(sys.argv[5]):
        w, t = line.rstrip("\n").split(" ", 1)
        labels[int(w, 16)] = t


def isnan(x):
    return (x & 0x7f800000) == 0x7f800000 and (x & 0x7fffff) != 0


def qemu_records(path):
    data = open(path, "rb").read()
    for off in range(0, len(data), 640):
        rec = data[off:off + 640]
        out1 = struct.unpack(E + "15I", rec[192:252])
        out2 = struct.unpack(E + "7I", rec[256:284])  # T MACH MACL GBR PR FPUL FPSCR
        fr = struct.unpack(E + "16I", rec[320:384])
        scr = rec[384:640]
        yield list(out1) + [out2[0] & 1, out2[1], out2[2], out2[3], out2[4], out2[5]] + list(fr), scr


vec_lines = [l.split() for l in open(vecs)]
g_lines = [l.rstrip("\n") for l in open(gout)]
q = list(qemu_records(qout))
if not (len(vec_lines) == len(g_lines) == len(q)):
    print("length mismatch: vectors %d ghidra %d qemu %d" % (len(vec_lines), len(g_lines), len(q)))
    sys.exit(2)
NAMES = ["R%d" % i for i in range(15)] + ["T", "MACH", "MACL", "GBR", "PR", "FPUL"] + ["FR%d" % i for i in range(16)]
NOFPU = os.environ.get("SH_NOFPU") == "1"  # SH-3: no FPU registers to compare
total = same = 0
diffs = defaultdict(list)
errs = Counter()
for i, (v, g, (qs, qscr)) in enumerate(zip(vec_lines, g_lines, q)):
    total += 1
    w = int(v[15], 16)
    if g.startswith("ERR"):
        errs[labels.get(w, "%04x" % w).split(" ")[0]] += 1
        diffs[(labels.get(w, "").split(" ")[0], "ghidra error")].append((i, v, g))
        continue
    f = g.split()
    gs = [int(x, 16) for x in f[:-1]]
    gscr = bytes.fromhex(f[-1])
    bad = []
    for k, nme in enumerate(NAMES):
        if NOFPU and (nme.startswith("FR") or nme == "FPUL"):
            continue
        a, b = gs[k], qs[k]
        if a != b and not (nme.startswith("FR") and isnan(a) and isnan(b)) and not (nme == "FPUL" and False):
            bad.append("%s ghidra=%x qemu=%x" % (nme, a, b))
    if gscr != qscr:
        bad.append("scratch differs")
    mn = labels.get(w, "%04x" % w).split(" ")[0]
    if bad and all(explained(mn, b.split(" ")[0], w, v) for b in bad):
        explained_count[(mn, explained(mn, bad[0].split(" ")[0], w, v))] += 1
        same += 1
        continue
    if bad:
        diffs[(mn, bad[0].split(" ")[0])].append((i, w, bad, v))
    else:
        same += 1
nexp = sum(explained_count.values())
print("vectors %d, identical %d, explained %d, unexplained %d" % (total, same - nexp, nexp, total - same))
for (mn, reason), c in sorted(explained_count.items()):
    print("  explained: %-8s %5d  %s" % (mn, c, reason))
for (mn, what), lst in sorted(diffs.items(), key=lambda kv: -len(kv[1])):
    i, w, bad, v = lst[0]
    print("  %-12s %-8s %5d  e.g. %04x %s  in=%s" % (mn, what, len(lst), w if isinstance(w, int) else 0, "; ".join(bad[:3]) if isinstance(bad, list) else bad, " ".join(v[:4]) if isinstance(v, list) else ""))
sys.exit(1 if total != same else 0)
