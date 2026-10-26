#!/usr/bin/env python3
"""Write a minimal Windows CE style PE32 executable for an SH machine type (a few instructions
in .text) so the importer's language choice can be tested.   mkpe.py <out.exe> <machine hex>"""
import struct
import sys

machine = int(sys.argv[2], 16)
code = struct.pack("<8H", 0xe501, 0x6153, 0x7101, 0x000b, 0x0009, 0x0009, 0x0009, 0x0009)  # mov #1,r5 ... rts nop
code = code.ljust(0x200, b"\0")
dos = b"MZ" + b"\0" * 58 + struct.pack("<I", 0x40)
coff = struct.pack("<HHIIIHH", machine, 1, 0, 0, 0, 0xe0, 0x102)
opt = struct.pack("<HBB" + "I" * 9 + "H" * 6 + "I" * 4 + "HH" + "I" * 6,
                  0x10b, 6, 0,
                  0x200, 0, 0, 0x1000, 0x1000, 0x2000, 0x10000, 0x1000, 0x200,   # sizes, entry, bases
                  4, 0, 0, 0, 4, 0,                                              # versions
                  0, 0x2000, 0x200, 0,                                           # image size, headers
                  9, 0,                                                          # subsystem: WinCE GUI
                  0x100000, 0x1000, 0x100000, 0x1000, 0, 16)
opt += b"\0" * (0xe0 - len(opt))
sec = b".text\0\0\0" + struct.pack("<IIIIIIHHI", 0x200, 0x1000, 0x200, 0x200, 0, 0, 0, 0, 0x60000020)
hdr = (dos + b"PE\0\0" + coff + opt + sec).ljust(0x200, b"\0")
open(sys.argv[1], "wb").write(hdr + code)
