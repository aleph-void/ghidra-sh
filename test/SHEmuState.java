// State-in/state-out runner for the QEMU differential (test/qemu): reads vectors written by
// gen_vectors.py and runs each instruction once in Ghidra's p-code emulator.
//   vector line (hex): R0..R14 insn T MACH MACL GBR PR S Q M FPUL FPSCR FR0..FR15
//   output line (hex): R0..R14 T MACH MACL GBR PR FPUL FR0..FR15 <256 scratch bytes>
// The scratch area is ram:10000000..+255 and is initialised with the runner's byte pattern.
// Script args: <vectors.txt> <out.txt>
//@category Testing

import java.io.PrintStream;
import java.math.BigInteger;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import ghidra.app.emulator.EmulatorHelper;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.lang.Register;

public class SHEmuState extends GhidraScript {
	static final int BATCH = 2048;
	private boolean be;
	private boolean fpu;

	private byte[] word(int w) {
		return be ? new byte[] { (byte) (w >> 8), (byte) w } : new byte[] { (byte) w, (byte) (w >> 8) };
	}

	private Register reg(String n) {
		Register r = currentProgram.getRegister(n);
		if (r == null) {
			throw new IllegalArgumentException("no register " + n);
		}
		return r;
	}

	private void wr(EmulatorHelper emu, String n, long v) {
		emu.writeRegister(reg(n), BigInteger.valueOf(v & 0xffffffffL));
	}

	private String rd(EmulatorHelper emu, String n) {
		return Long.toHexString(emu.readRegister(reg(n)).longValue() & 0xffffffffL);
	}

	@Override
	protected void run() throws Exception {
		String[] args = getScriptArgs();
		be = currentProgram.getLanguage().isBigEndian();
		fpu = currentProgram.getRegister("FR0") != null;
		List<String> lines = new ArrayList<>();
		for (String l : Files.readAllLines(Path.of(args[0]))) {
			if (!l.isBlank()) {
				lines.add(l.trim());
			}
		}
		byte[] pattern = new byte[256];
		for (int i = 0; i < 256; i++) {
			pattern[i] = (byte) (i * 7 + 3 - 0);
		}
		// the runner's pattern: word k holds bytes (4k*7+3, +4, +5, +6) -> pattern[i] = (7*(i&~3) + 3 + (i&3))
		for (int i = 0; i < 256; i++) {
			pattern[i] = (byte) (7 * (i & ~3) + 3 + (i & 3));
		}
		Address scratch = toAddr(0x10000000L);
		PrintStream out = new PrintStream(args[1]);
		for (int base = 0; base < lines.size(); base += BATCH) {
			int n = Math.min(BATCH, lines.size() - base);
			EmulatorHelper emu = new EmulatorHelper(currentProgram);
			try {
				for (int i = 0; i < n; i++) {
					String[] f = lines.get(base + i).split(" ");
					Address a = toAddr(0x1000L + 8L * i);
					emu.writeMemory(a, word(Integer.parseInt(f[15], 16)));
					emu.writeMemory(a.add(2), word(0x0009));
					emu.writeMemory(a.add(4), word(0x0009));
				}
				for (int i = 0; i < n; i++) {
					String[] f = lines.get(base + i).split(" ");
					long[] v = new long[f.length];
					for (int k = 0; k < f.length; k++) {
						v[k] = Long.parseLong(f[k], 16);
					}
					for (int k = 0; k < 15; k++) {
						wr(emu, "R" + k, v[k]);
					}
					wr(emu, "R15", 0x8000);
					wr(emu, "T", v[16]);
					wr(emu, "MACH", v[17]);
					wr(emu, "MACL", v[18]);
					wr(emu, "GBR", v[19]);
					wr(emu, "PR", v[20]);
					wr(emu, "S", v[21]);
					wr(emu, "Q", v[22]);
					wr(emu, "M", v[23]);
					if (fpu) {
						wr(emu, "FPUL", v[24]);
						wr(emu, "FPSCR", v[25]);
						for (int k = 0; k < 16; k++) {
							wr(emu, "FR" + k, v[26 + k]);
						}
					}
					emu.writeMemory(scratch, pattern);
					Address a = toAddr(0x1000L + 8L * i);
					emu.writeRegister(emu.getPCRegister(), a.getOffset());
					boolean ok;
					try {
						ok = emu.step(monitor);
					}
					catch (Exception e) {
						ok = false;
					}
					if (!ok) {
						out.println("ERR " + String.valueOf(emu.getLastError()).replace('\n', ' '));
						continue;
					}
					StringBuilder sb = new StringBuilder();
					for (int k = 0; k < 15; k++) {
						sb.append(rd(emu, "R" + k)).append(' ');
					}
					sb.append(Long.toHexString(emu.readRegister(reg("T")).longValue() & 1)).append(' ');
					for (String nme : new String[] { "MACH", "MACL", "GBR", "PR" }) {
						sb.append(rd(emu, nme)).append(' ');
					}
					if (fpu) {
						sb.append(rd(emu, "FPUL"));
						for (int k = 0; k < 16; k++) {
							sb.append(' ').append(rd(emu, "FR" + k));
						}
					}
					else {
						sb.append("0");
						for (int k = 0; k < 16; k++) {
							sb.append(" 0");
						}
					}
					sb.append(' ');
					for (byte b : emu.readMemory(scratch, 256)) {
						sb.append(String.format("%02x", b & 0xff));
					}
					out.println(sb);
				}
			}
			finally {
				emu.dispose();
			}
			monitor.setMessage("vector " + (base + n));
		}
		out.close();
	}
}
