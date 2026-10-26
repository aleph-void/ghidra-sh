// Lists functions: "<entry> <name> thunk=<bool> block=<name>"  Script args: <out.txt> [max]
//@category Testing

import java.io.PrintStream;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.mem.MemoryBlock;

public class ListFuncs extends GhidraScript {
	@Override
	protected void run() throws Exception {
		String[] a = getScriptArgs();
		PrintStream out = new PrintStream(a[0]);
		int max = a.length > 1 ? Integer.parseInt(a[1]) : 1000000;
		int n = 0;
		for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
			MemoryBlock b = currentProgram.getMemory().getBlock(f.getEntryPoint());
			out.printf("%s %s thunk=%s block=%s%n", f.getEntryPoint(), f.getName(), f.isThunk(),
				b == null ? "-" : b.getName());
			if (++n >= max) {
				break;
			}
		}
		out.close();
	}
}
