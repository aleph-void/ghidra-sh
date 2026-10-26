// Prints the instruction text, p-code and references at the given addresses.
// Script args: <out.txt> <hexaddr>...
//@category Testing

import java.io.PrintStream;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.pcode.PcodeOp;
import ghidra.program.model.symbol.Reference;

public class RefDump extends GhidraScript {
	@Override
	protected void run() throws Exception {
		String[] args = getScriptArgs();
		PrintStream out = new PrintStream(args[0]);
		for (int i = 1; i < args.length; i++) {
			Address a = toAddr(Long.parseLong(args[i], 16));
			Instruction ins = getInstructionAt(a);
			out.printf("%s: %s flow=%s%n", a, ins, ins == null ? "-" : ins.getFlowType());
			if (ins == null) {
				continue;
			}
			for (PcodeOp op : ins.getPcode()) {
				out.printf("    %s%n", op);
			}
			for (Reference r : ins.getReferencesFrom()) {
				out.printf("    ref -> %s %s%n", r.getToAddress(), r.getReferenceType());
			}
			Address ft = ins.getFallThrough();
			out.printf("    fallthrough %s%n", ft);
		}
		out.close();
	}
}
