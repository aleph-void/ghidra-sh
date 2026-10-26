#!/usr/bin/env python3
"""Write all 65536 16-bit words as a raw image: gen_words.py <out.bin> <big|little>"""
import struct
import sys
fmt = ">H" if sys.argv[2] == "big" else "<H"
open(sys.argv[1], "wb").write(b"".join(struct.pack(fmt, i) for i in range(65536)))
