/* Ghidra-Rare addition to will07c5/ghidra-sh, MIT License (see LICENSE). */
package ghidra.app.plugin.core.analysis;

import java.util.Iterator;

import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.cmd.function.CreateFunctionCmd;
import ghidra.app.services.AbstractAnalyzer;
import ghidra.app.services.AnalysisPriority;
import ghidra.app.services.AnalyzerType;
import ghidra.app.util.importer.MessageLog;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressOutOfBoundsException;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.address.AddressSetView;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Program;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryAccessException;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.reloc.Relocation;
import ghidra.program.model.symbol.Symbol;
import ghidra.util.exception.CancelledException;
import ghidra.util.task.TaskMonitor;

/**
 * Turns the SuperH ELF PLT stubs into thunks to the imported functions.
 *
 * A SuperH PLT entry loads its GOT slot through the PIC register R12
 * ({@code mov.l @(disp,pc),r0; mov.l @(r0,r12),r0; jmp @r0}) or, in non-PIC code, through the
 * slot's absolute address ({@code mov.l @(disp,pc),r0; mov.l @r0,r0; jmp @r0}).  R12 is only
 * known in the caller, so the jump cannot be resolved from the stub alone and every call into
 * the PLT shows up as FUN_xxxxxxxx.  This analyzer finds the stubs by their three-instruction
 * pattern, computes the slot (GOT base + literal, or the literal itself) and follows it: the ELF
 * loader has already applied the JMP_SLOT relocations, so the slot holds the address of the
 * import (an external thunk, or a function of the same file).  The PLT function becomes a thunk
 * of that function, which also gives it the import's name.
 */
public class SHPltAnalyzer extends AbstractAnalyzer {

	private static final String NAME = "SuperH PLT Stubs";
	private static final String DESCRIPTION =
		"Names the SH-2E/SH-3/SH-3E ELF PLT stubs after the functions they import.";

	private static final int MOVL_PC_R0 = 0xd000; // mov.l @(disp,pc),r0   (mask 0xff00)
	private static final int MOVL_R0_R12_R0 = 0x00ce; // mov.l @(r0,r12),r0
	private static final int MOVL_AT_R0_R0 = 0x6002; // mov.l @r0,r0
	private static final int JMP_AT_R0 = 0x402b; // jmp @r0

	public SHPltAnalyzer() {
		super(NAME, DESCRIPTION, AnalyzerType.INSTRUCTION_ANALYZER);
		setPriority(AnalysisPriority.FUNCTION_ANALYSIS.after());
		setDefaultEnablement(true);
	}

	@Override
	public boolean canAnalyze(Program program) {
		String proc = program.getLanguage().getProcessor().toString();
		return (proc.equals("SH3") || proc.equals("SH3E") || proc.equals("SH2E")) &&
			"Executable and Linking Format (ELF)".equals(program.getExecutableFormat());
	}

	@Override
	public boolean added(Program program, AddressSetView set, TaskMonitor monitor, MessageLog log)
			throws CancelledException {
		Memory mem = program.getMemory();
		MemoryBlock plt = mem.getBlock(".plt");
		if (plt == null || !plt.isInitialized()) {
			return false;
		}
		// R12 holds _GLOBAL_OFFSET_TABLE_, the start of .got.plt (or .got).  The blocks are used
		// rather than the symbol: it is an absolute symbol that is not moved with the image base.
		Address got = null;
		MemoryBlock gb = mem.getBlock(".got.plt");
		if (gb == null) {
			gb = mem.getBlock(".got");
		}
		if (gb != null) {
			got = gb.getStart();
		}
		else {
			for (Symbol s : program.getSymbolTable().getSymbols("_GLOBAL_OFFSET_TABLE_")) {
				got = s.getAddress();
				break;
			}
		}
		FunctionManager fm = program.getFunctionManager();
		for (Address a = plt.getStart(); a != null && a.add(6).compareTo(plt.getEnd()) <= 0;
				a = a.add(2)) {
			monitor.checkCancelled();
			Address slot = stubSlot(program, mem, a, got);
			if (slot == null) {
				continue;
			}
			Function stub = fm.getFunctionAt(a);
			if (stub != null && stub.isThunk()) {
				continue;
			}
			Function imported = importAt(program, mem, slot, plt, monitor);
			if (imported == null || imported.getEntryPoint().equals(a)) {
				continue;
			}
			if (stub == null) {
				new DisassembleCommand(a, null, true).applyTo(program, monitor);
				new CreateFunctionCmd(a).applyTo(program, monitor);
				stub = fm.getFunctionAt(a);
			}
			if (stub == null) {
				continue;
			}
			try {
				stub.setThunkedFunction(imported);
			}
			catch (IllegalArgumentException e) {
				log.appendMsg(NAME, "cannot thunk " + a + ": " + e.getMessage());
			}
		}
		return true;
	}

	/** The GOT slot the PLT stub at {@code a} jumps through, or null if there is no stub. */
	private static Address stubSlot(Program program, Memory mem, Address a, Address got) {
		try {
			int w0 = mem.getShort(a) & 0xffff;
			int w1 = mem.getShort(a.add(2)) & 0xffff;
			int w2 = mem.getShort(a.add(4)) & 0xffff;
			if ((w0 & 0xff00) != MOVL_PC_R0 || w2 != JMP_AT_R0 ||
				(w1 != MOVL_R0_R12_R0 && w1 != MOVL_AT_R0_R0)) {
				return null;
			}
			long lit = (a.getOffset() & ~3L) + 4 + 4L * (w0 & 0xff);
			long v = mem.getInt(a.getNewAddress(lit)) & 0xffffffffL;
			if (w1 == MOVL_AT_R0_R0) {
				return a.getNewAddress(v);
			}
			return got == null ? null : got.add(v);
		}
		catch (MemoryAccessException | AddressOutOfBoundsException e) {
			return null;
		}
	}

	/** The function a relocated GOT slot points at (an import or a function of this file). */
	private static Function importAt(Program program, Memory mem, Address slot, MemoryBlock plt,
			TaskMonitor monitor) {
		FunctionManager fm = program.getFunctionManager();
		try {
			Address target = slot.getNewAddress(mem.getInt(slot) & 0xffffffffL);
			if (!plt.contains(target)) {
				Function f = fm.getFunctionAt(target);
				if (f != null) {
					return f;
				}
				// a function of this file that analysis has not reached yet: it has a symbol
				MemoryBlock tb = mem.getBlock(target);
				if (tb != null && tb.isExecute() && !tb.getName().equals(MemoryBlock.EXTERNAL_BLOCK_NAME) &&
					program.getSymbolTable().getPrimarySymbol(target) != null) {
					new DisassembleCommand(target, null, true).applyTo(program, monitor);
					new CreateFunctionCmd(target).applyTo(program, monitor);
					return fm.getFunctionAt(target);
				}
			}
		}
		catch (MemoryAccessException | AddressOutOfBoundsException e) {
			// fall through to the relocation's symbol
		}
		// a slot still pointing into the PLT (lazy binding) keeps the symbol in its relocation
		Iterator<Relocation> it = program.getRelocationTable().getRelocations(slot).iterator();
		while (it.hasNext()) {
			String name = it.next().getSymbolName();
			if (name != null) {
				for (Function f : fm.getFunctions(true)) {
					if (f.getName().equals(name) && !plt.contains(f.getEntryPoint())) {
						return f;
					}
				}
			}
		}
		return null;
	}
}
