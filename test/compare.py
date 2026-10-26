#!/usr/bin/env python3
"""Compare Ghidra's slot dump (DumpDisasm.java) with GNU objdump output, word by word.

    compare.py <ghidra.txt> <objdump.txt> [explained.txt]

Ghidra line:  "<offset-hex> <bytes-hex> <text>" or "<offset-hex> - BAD (...)".
objdump line: "   <addr>:\t<b0> <b1>\t<mnemonic>\t<operands>[\t! comment]"; ".word 0x...." means invalid.

exact    same text after lower-casing and removing blanks
semantic same instruction after normalising spellings (see norm())
Differences are bucketed by (ghidra mnemonic, objdump mnemonic); a bucket must be listed in
the 'explained' file (lines "ghidra-mnemonic objdump-mnemonic reason") or the run fails.
"""
import re
import sys
from collections import Counter, defaultdict

M32 = 0xffffffff


def num(m):
    t = m.group(0)
    return str(int(t, 16 if "0x" in t.lower() else 10) & M32 if not t.startswith("-") else int(t, 16 if "0x" in t.lower() else 10))


def norm(text):
    t = text.lower().strip()
    t = re.sub(r"^_", "", t)  # Ghidra marks a delay-slot instruction with a leading underscore
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\s*,\s*", ",", t)
    t = t.replace("fmov.s", "fmov")
    # Renesas syntax bt/s, bf/s; GNU objdump prints bt.s, bf.s
    t = re.sub(r"^(bt|bf)/s ", r"\1.s ", t)
    # pc-relative operands: ghidra "@(0x1234,pc)", objdump a bare address
    t = re.sub(r"@\((0x[0-9a-f]+),pc\)", r"\1", t)
    # numbers (not part of register names): compare by value
    def sub(m):
        s = m.group(0)
        v = int(s, 16) if "0x" in s else int(s)
        return str(v)
    t = re.sub(r"(?<![a-z0-9_])-?(0x[0-9a-f]+|\d+)(?![a-z0-9_])", sub, t)
    return t


def exact_key(text):
    return re.sub(r"\s+", "", text.lower().lstrip("_"))


def load_ghidra(p):
    d = {}
    for line in open(p):
        f = line.rstrip("\n").split(" ", 2)
        off = int(f[0], 16)
        if f[1] == "-":
            d[off] = None
        else:
            d[off] = f[2].strip()
    return d


def load_objdump(p):
    d = {}
    for line in open(p):
        m = re.match(r"\s*([0-9a-f]+):\t([0-9a-f ]+)\t(.*)$", line)
        if not m:
            continue
        txt = m.group(3).split("\t! ")[0]
        txt = re.sub(r"\t+", " ", txt).strip()
        d[int(m.group(1), 16)] = None if txt.startswith(".word") else txt
    return d


def addr_fix(gt, ot, off):
    """Branch/pc-relative targets: objdump prints the address as 32-bit hex."""
    return gt, ot


def main():
    g = load_ghidra(sys.argv[1])
    o = load_objdump(sys.argv[2])
    explained = {}
    if len(sys.argv) > 3:
        for line in open(sys.argv[3]):
            line = line.strip()
            if line and not line.startswith("#"):
                a, b, why = line.split(None, 2)
                explained[(a, b)] = why
    n = exact = sem = both_inv = 0
    buckets = defaultdict(list)
    for off in sorted(o):
        n += 1
        gt, ot = g.get(off), o[off]
        if gt is None and ot is None:
            both_inv += 1
            continue
        if gt is not None and ot is not None:
            if exact_key(gt) == exact_key(ot):
                exact += 1
                continue
            if norm(gt) == norm(ot):
                sem += 1
                continue
        gm = gt.split()[0].lower() if gt else "INVALID"
        om = ot.split()[0].lower() if ot else "INVALID"
        buckets[(gm, om)].append((off, gt, ot))
    unexpl = 0
    expl = 0
    for k, v in sorted(buckets.items()):
        why = explained.get(k)
        if why:
            expl += len(v)
        else:
            unexpl += len(v)
    print(f"words {n}: exact {exact}, semantic {sem}, both-invalid {both_inv}, "
          f"explained {expl}, unexplained {unexpl}")
    for k, v in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
        why = explained.get(k, "UNEXPLAINED")
        print(f"  {k[0]} / {k[1]}: {len(v)}  [{why}]  e.g. {v[0][0]:#06x}: ghidra={v[0][1]!r} objdump={v[0][2]!r}")
    return 1 if unexpl else 0


if __name__ == "__main__":
    sys.exit(main())
