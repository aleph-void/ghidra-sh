import ghidra.app.script.GhidraScript;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import ghidra.program.model.reloc.*;
public class Probe extends GhidraScript {
  public void run() throws Exception {
    for (Symbol s : currentProgram.getSymbolTable().getSymbols("_GLOBAL_OFFSET_TABLE_")) println("GOT sym " + s.getAddress());
    for (Symbol s : currentProgram.getSymbolTable().getSymbols("_DYNAMIC")) println("DYN sym " + s.getAddress());
    Address g = toAddr(0x415288L);
    for (int i = 0; i < 8; i++) { Address a = g.add(4*i); println(a + " = " + Long.toHexString(currentProgram.getMemory().getInt(a) & 0xffffffffL) + " refs " + java.util.Arrays.toString(currentProgram.getReferenceManager().getReferencesFrom(a))); }
    for (Relocation r : currentProgram.getRelocationTable().getRelocations(toAddr(0x415294L))) println("reloc " + r.getType() + " " + r.getSymbolName() + " " + r.getStatus());
    println("PLT first: " + getInstructionAt(toAddr(0x4015fcL)) + " ; " + getInstructionAfter(toAddr(0x4015fcL)));
    for (Reference r : currentProgram.getReferenceManager().getReferencesFrom(toAddr(0x4015fcL))) println("ref " + r);
  }
}
