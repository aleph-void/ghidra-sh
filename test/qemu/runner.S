! State-in/state-out runner for QEMU user mode (sh4 / sh4eb).  Executes the 16-bit instruction
! in each record of vectors.bin with the given register state and writes the records back to
! stdout.  Record layout, 640 bytes (little/big endian words as the target):
!     0 in1   R0..R14 (15 words), word 15 = the instruction
!    64 in2   T MACH MACL GBR PR S Q M FPUL FPSCR
!   128 in3   FR0..FR15
!   192 out1  R0..R14
!   256 out2  T MACH MACL GBR PR FPUL FPSCR
!   320 out3  FR0..FR15
!   384 out4  the 256-byte scratch area (0x10000000) after the instruction
	.section .rwtext,"awx",@progbits
	.globl _start
_start:
	mov.l	vecp,r15
loop:
	mov.l	@(60,r15),r0
	mov.l	slotp,r1
	mov.w	r0,@r1
	mov.l	pattp,r1
	mov.l	scrp,r2
	mov	#64,r3
cp1:	mov.l	@r1+,r0
	mov.l	r0,@r2
	add	#4,r2
	dt	r3
	bf	cp1
	add	#64,r15
	mov.l	@(4,r15),r0
	lds	r0,mach
	mov.l	@(8,r15),r0
	lds	r0,macl
	mov.l	@(12,r15),r0
	ldc	r0,gbr
	mov.l	@(16,r15),r0
	lds	r0,pr
	mov.l	@(20,r15),r0
	tst	r0,r0
	bt	clrs_
	sets
	bra	sdone
	nop
clrs_:	clrs
sdone:
	mov.l	@(24,r15),r0
	mov.l	@(28,r15),r1
	div0s	r1,r0
	mov.l	@(36,r15),r1
	lds	r1,fpscr
	mov.l	@(32,r15),r0
	lds	r0,fpul
	add	#64,r15
	mov	r15,r2
	fmov.s	@r2+,fr0
	fmov.s	@r2+,fr1
	fmov.s	@r2+,fr2
	fmov.s	@r2+,fr3
	fmov.s	@r2+,fr4
	fmov.s	@r2+,fr5
	fmov.s	@r2+,fr6
	fmov.s	@r2+,fr7
	fmov.s	@r2+,fr8
	fmov.s	@r2+,fr9
	fmov.s	@r2+,fr10
	fmov.s	@r2+,fr11
	fmov.s	@r2+,fr12
	fmov.s	@r2+,fr13
	fmov.s	@r2+,fr14
	fmov.s	@r2+,fr15
	add	#-64,r15
	mov.l	@(0,r15),r0
	cmp/eq	#1,r0
	add	#-64,r15
	mov.l	@(56,r15),r14
	mov.l	@(52,r15),r13
	mov.l	@(48,r15),r12
	mov.l	@(44,r15),r11
	mov.l	@(40,r15),r10
	mov.l	@(36,r15),r9
	mov.l	@(32,r15),r8
	mov.l	@(28,r15),r7
	mov.l	@(24,r15),r6
	mov.l	@(20,r15),r5
	mov.l	@(16,r15),r4
	mov.l	@(12,r15),r3
	mov.l	@(8,r15),r2
	mov.l	@(4,r15),r1
	mov.l	@(0,r15),r0
	.globl slot
slot:	.word	0x0009
	nop
	nop
	add	#127,r15
	add	#65,r15
	mov.l	r14,@(56,r15)
	mov.l	r13,@(52,r15)
	mov.l	r12,@(48,r15)
	mov.l	r11,@(44,r15)
	mov.l	r10,@(40,r15)
	mov.l	r9,@(36,r15)
	mov.l	r8,@(32,r15)
	mov.l	r7,@(28,r15)
	mov.l	r6,@(24,r15)
	mov.l	r5,@(20,r15)
	mov.l	r4,@(16,r15)
	mov.l	r3,@(12,r15)
	mov.l	r2,@(8,r15)
	mov.l	r1,@(4,r15)
	mov.l	r0,@(0,r15)
	movt	r0
	add	#64,r15
	mov.l	r0,@(0,r15)
	sts	mach,r0
	mov.l	r0,@(4,r15)
	sts	macl,r0
	mov.l	r0,@(8,r15)
	stc	gbr,r0
	mov.l	r0,@(12,r15)
	sts	pr,r0
	mov.l	r0,@(16,r15)
	sts	fpul,r0
	mov.l	r0,@(20,r15)
	sts	fpscr,r0
	mov.l	r0,@(24,r15)
	mov	r15,r2
	add	#64,r2
	add	#64,r2
	fmov.s	fr15,@-r2
	fmov.s	fr14,@-r2
	fmov.s	fr13,@-r2
	fmov.s	fr12,@-r2
	fmov.s	fr11,@-r2
	fmov.s	fr10,@-r2
	fmov.s	fr9,@-r2
	fmov.s	fr8,@-r2
	fmov.s	fr7,@-r2
	fmov.s	fr6,@-r2
	fmov.s	fr5,@-r2
	fmov.s	fr4,@-r2
	fmov.s	fr3,@-r2
	fmov.s	fr2,@-r2
	fmov.s	fr1,@-r2
	fmov.s	fr0,@-r2
	mov.l	scrp,r1
	mov	r15,r2
	add	#64,r2
	add	#64,r2
	mov	#64,r3
cp2:	mov.l	@r1+,r0
	mov.l	r0,@r2
	add	#4,r2
	dt	r3
	bf	cp2
	mov.l	recadv,r0
	add	r0,r15
	mov.l	endp,r0
	cmp/eq	r0,r15
	bt	finish
	bra	loop
	nop
finish:
	mov	#4,r3
	mov	#1,r4
	mov.l	vecp,r5
	mov.l	vlen,r6
	trapa	#0x13
	mov	#1,r3
	mov	#0,r4
	trapa	#0x11
	.align	2
vecp:	.long	vectors
slotp:	.long	slot
pattp:	.long	pattern
scrp:	.long	0x10000000
recadv:	.long	384
endp:	.long	vectors_end
vlen:	.long	vectors_end-vectors
	.data
	.align	2
pattern:
	.set	i,0
	.rept	64
	.byte	(i*7+3)&0xff, (i*7+4)&0xff, (i*7+5)&0xff, (i*7+6)&0xff
	.set	i,i+4
	.endr
	.align	2
vectors:
	.incbin	"vectors.bin"
vectors_end:
	.section .scratch,"aw",@nobits
	.space	256
