#!/usr/bin/env bash
# Fetch the third-party SH-3 real-code samples (never committed): the NetBSD 10.1 base sets for
# evbsh3-sh3el and evbsh3-sh3eb (BSD licensed, freely redistributable:
# https://www.netbsd.org/about/redistribution.html).  Each archive is pinned by URL and SHA-256;
# only the files the tests use are extracted.
#   test/fetch-samples.sh <workdir>   -> <workdir>/netbsd-sh3{el,eb}/{bin,usr/bin,libexec,lib}/...
set -euo pipefail
W=$(readlink -m "$1")
BASE=https://archive.netbsd.org/pub/NetBSD-archive/NetBSD-10.1
fetch() {   # <port> <sha256>
	local port=$1 sum=$2 d=$W/netbsd-${1#evbsh3-}
	mkdir -p "$d"
	if [[ ! -f $d/base.tgz ]] || ! echo "$sum  $d/base.tgz" | sha256sum -c --status; then
		curl -fsSL -o "$d/base.tgz.part" "$BASE/$port/binary/sets/base.tgz"
		echo "$sum  $d/base.tgz.part" | sha256sum -c --status || { echo "SHA-256 mismatch: $port" >&2; exit 1; }
		mv "$d/base.tgz.part" "$d/base.tgz"
	fi
	mkdir -p "$d/x"
	tar -xzf "$d/base.tgz" -C "$d/x" ./bin/ls ./bin/ksh ./usr/bin/awk ./libexec/ld.elf_so \
		./lib/libm.so.0.13 ./lib/libz.so.1.0 ./lib/libc.so.12.220.1 ./lib/libcrypto.so.15.0
}
fetch evbsh3-sh3el 6f89a8ed9528f49fc08c7949dbf0a14767661e6a18a68792c761407560539436
fetch evbsh3-sh3eb 432c95418828e633ddd35eeadb8625f8e278b1b46a31572f855ffac00064e74a
ls "$W"/netbsd-sh3el/x/bin/ls "$W"/netbsd-sh3eb/x/bin/ls >/dev/null
