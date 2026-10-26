// Relocation check for test/reloc-check.sh: prints the relocation statuses of a relocatable
// object and whether the data pointers were relocated to the right addresses.
// Script args: <out.txt>
//@category Testing

import java.io.PrintStream;
import java.util.Iterator;
import java.util.Map;
import java.util.TreeMap;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.reloc.Relocation;
import ghidra.program.model.symbol.Symbol;

public class RelocCheck extends GhidraScript {
	private long sym(String name) {
		// sh-elf prefixes C symbols with an underscore
		for (String n : new String[] { name, "_" + name }) {
			for (Symbol s : currentProgram.getSymbolTable().getSymbols(n)) {
				return s.getAddress().getOffset();
			}
		}
		return -1;
	}

	@Override
	protected void run() throws Exception {
		PrintStream out = new PrintStream(getScriptArgs()[0]);
		Map<String, Integer> st = new TreeMap<>();
		Iterator<Relocation> it = currentProgram.getRelocationTable().getRelocations();
		while (it.hasNext()) {
			Relocation r = it.next();
			st.merge(r.getType() + ":" + r.getStatus(), 1, Integer::sum);
		}
		out.println("relocations " + st);
		Address pt = toAddr(sym("ptr_to_table"));
		Address fp = toAddr(sym("fp"));
		long ptv = currentProgram.getMemory().getInt(pt) & 0xffffffffL;
		long fpv = currentProgram.getMemory().getInt(fp) & 0xffffffffL;
		out.printf("ptr_to_table -> table+8: %s%n", ptv == sym("table") + 8 ? "ok" : "WRONG");
		out.printf("fp -> ext_func: %s%n", fpv == sym("ext_func") ? "ok" : "WRONG " + Long.toHexString(fpv));
		// the PLT stub for ext_func (called from use) must be a thunk named after the import
		int plt = 0, thunks = 0;
		for (ghidra.program.model.listing.Function f : currentProgram.getFunctionManager().getFunctions(true)) {
			ghidra.program.model.mem.MemoryBlock b = currentProgram.getMemory().getBlock(f.getEntryPoint());
			if (b != null && b.getName().equals(".plt")) {
				plt++;
				if (f.isThunk()) {
					thunks++;
				}
			}
		}
		out.printf("plt functions %d, thunks %d: %s%n", plt, thunks, plt > 0 && plt == thunks ? "ok" : "WRONG");
		out.close();
	}
}
