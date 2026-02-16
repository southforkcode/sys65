from .ast import Program, Statement, Instruction, Directive, Label, Assignment, Unresolved, BinaryExpr, IfDef, EnumDef
from .opcodes import OPCODES, OPCODES_6502, OPCODES_65C02
from .bytes import ByteConverter
from .symtab import SymbolTable

class CompilerError(Exception):
    def __init__(self, msg: str, node: Statement = None):
        self.msg = msg
        self.node = node
    def __str__(self):
        loc = ""
        if self.node:
             if self.node.filename:
                 loc += f"{self.node.filename}:"
             if hasattr(self.node, 'line') and self.node.line:
                 loc += f"{self.node.line}: "
        return f"{loc}{self.msg}"

class Compiler:
    def __init__(self):
        self.symbols = SymbolTable()
        self.local_labels = {} # Map name -> List[int]
        self.bytes = bytearray()
        self.origin = 0
        self.pc = 0 # Program Counter
        self.pass_num = 1
        self.cpu_mode = "6502"
        self.opcodes = OPCODES_6502

    def compile(self, program: Program) -> bytearray:
        # Pass 1: Calculate addresses and define labels
        self.pass_num = 1
        self.pc = 0
        self.local_labels = {} # reset
        self.origin = 0 # reset
        self.start_origin = None # Track first .org
        self.cpu_mode = "6502"
        self.opcodes = OPCODES_6502
        self.visit_program(program)
        
        # Pass 2: Generate code
        self.pass_num = 2
        self.pc = 0
        self.origin = 0 # reset (though mostly unused in pass 2 logic except if referenced)
        # origin should ideally be preserved from pass 1 for reporting 
        self.cpu_mode = "6502"
        self.opcodes = OPCODES_6502
        self.visit_program(program)
        
        return self.bytes

    def visit_program(self, program: Program):
        for stmt in program.statements:
            self.visit_statement(stmt)

    def visit_statement(self, stmt: Statement):
        if isinstance(stmt, Label):
            if self.pass_num == 1:
                if stmt.name.isdigit():
                    if stmt.name not in self.local_labels:
                        self.local_labels[stmt.name] = []
                    self.local_labels[stmt.name].append(self.pc)
                else:
                    self.symbols.set(stmt.name, self.pc)
        elif isinstance(stmt, Assignment):
            # Resolve value immediately if possible
            val = stmt.value
            if isinstance(val, int):
                 self.symbols.set(stmt.name, val)
            else:
                 # Try to resolve if expression
                 resolved = self.resolve_expr(val)
                 if resolved is not None:
                      self.symbols.set(stmt.name, resolved)
        elif isinstance(stmt, Directive):
            self.visit_directive(stmt)
        elif isinstance(stmt, Instruction):
            self.visit_instruction(stmt)
        elif isinstance(stmt, IfDef):
            self.visit_ifdef(stmt)
        elif isinstance(stmt, EnumDef):
            self.visit_enum_def(stmt)

    def visit_ifdef(self, node: IfDef):
        # Check if symbol is defined
        is_defined = node.condition in self.symbols
        
        if is_defined:
            for stmt in node.then_block:
                self.visit_statement(stmt)
        else:
            for stmt in node.else_block:
                self.visit_statement(stmt)

    def visit_enum_def(self, node: EnumDef):
        # Only process enums in Pass 1 to define symbols
        if self.pass_num != 1:
            return

        current_value = 0
        
        for name, value_expr in node.members:
            # If explicit value, resolve it
            if value_expr is not None:
                # Resolve expression. Since it's pass 1, we might not have all symbols.
                # But enums usually depend on constants or previous enums.
                # If we fail to resolve, we can default to 0 or raise error?
                # For now, try resolve.
                val = self.resolve_expr(value_expr)
                if val is not None:
                    current_value = val
                else: 
                     # If unresolved in pass 1?
                     # Maybe forward reference?
                     # Let's assume 0 for now and it will be correct if it's constant?
                     # Actually if we can't resolve, we can't know the value for subsequent auto-increments.
                     # This is a limitation. Most assemblers require constant expressions for enums.
                     # But we'll follow resolve_expr logic which returns None if unresolved.
                     # If None, we can't set symbol accurately.
                     pass 
            
            # Define symbol
            # If enum has name: EnumName.MemberName

            
            # Always define MemberName (unscoped) as per request?
            # "The assembly program can refer to the enum by the name of its value (if the enum is not named) or by the enum name and value id"
            # "DOS_COMMANDS.FORMAT would resolve to 4"
            # The prompt implies:
            # 1. Named enum (`.enum Name`) -> access via `Name.Member` ??
            #    Or does it imply *also* `Member`?
            #    "refer to the enum by the name of its value (if the enum is not named)"
            #    This suggests if named, you MUST use Name.Value?
            #    BUT: "or by the enum name and value id"
            #    Let's re-read: "refer to the enum by the name of its value (if the enum is not named) or by the enum name and value id"
            #    This *could* mean:
            #    - Unnamed: `Member`
            #    - Named: `Name.Member`
            #    It acts like a namespace.
            #    However, often assemblers export both or just one.
            #    Let's stick to strict interpretation:
            #    - If named: `Name.Member` only?
            #    - If unnamed: `Member` only.
            #    Wait, "DOS_COMMANDS.FORMAT would resolve to 4" example.
            #    If I have `SEEK = 0`, can I access `SEEK` directly if it's inside `DOS_COMMANDS`?
            #    The prompt says: "refer to the enum by the name of its value (if the enum is not named)"
            #    This strictly implies: IF named, you CANNOT refer by name of value alone?
            #    Let's look at the example:
            #    .enum DOS_COMMANDS
            #       SEEK = 0
            #    .end
            #    "DOS_COMMANDS.FORMAT would resolve to 4."
            #    It doesn't explicitly say "SEEK would resolve to 0".
            #    So I will implement scoping:
            #    - Named: `Enum.Member`
            #    - Unnamed: `Member`
            #    Safe implementation.
            
            if node.name:
                 self.symbols.set(f"{node.name}.{name}", current_value)
            else:
                 self.symbols.set(name, current_value)
                 
            # Auto-increment
            current_value += 1

    def visit_directive(self, d: Directive):
        if d.name == '.org':
            val = self.resolve_expr(d.args[0])
            if val is None:
                 if self.pass_num == 1: val = 0 
                 else: raise CompilerError("Could not resolve .org value", d)
            
            self.pc = val
            if self.start_origin is None:
                self.start_origin = val
            self.origin = val # Update current origin context
            
        elif d.name == '.byte':
            for arg in d.args:
                # Handle string literals specially
                if isinstance(arg, str):
                    for char in arg:
                        self.emit_byte(ord(char))
                else:
                    val = self.resolve_expr(arg)
                    if val is None: val = 0
                    self.emit_byte(val)
        elif d.name == '.word':
            for arg in d.args:
                val = self.resolve_expr(arg)
                if val is None: 
                    if self.pass_num == 2: raise CompilerError("Unresolved symbol in .word", d)
                    val = 0
                self.emit_word(val)
        elif d.name == '.fill':
             count = self.resolve_expr(d.args[0]) or 0
             val = 0
             if len(d.args) > 1:
                 val = self.resolve_expr(d.args[1]) or 0
             for _ in range(count):
                 self.emit_byte(val)
        elif d.name == '.cpu':
             # Handle .cpu directive
             val = d.args[0]
             # val might be string or identifier (if unquoted)
             # Parser wraps strings in str?
             # If it's a string literal, it comes as string.
             # If it's ID, it comes as Unresolved?
             # Let's check parser. Parser returns Unresolved for IDs in expr.
             mode_str = ""
             if isinstance(val, str):
                 mode_str = val
             elif isinstance(val, Unresolved):
                 mode_str = val.name
             
             mode_str = mode_str.lower().strip('"\'')
             
             if mode_str == "6502":
                 self.cpu_mode = "6502"
                 self.opcodes = OPCODES_6502
             elif mode_str == "65c02":
                 self.cpu_mode = "65c02"
                 self.opcodes = OPCODES_65C02
             else:
                 raise CompilerError(f"Unknown CPU mode: {mode_str}", d)

        elif d.name == '.align':
             alignment = self.resolve_expr(d.args[0])
             if alignment is None:
                 if self.pass_num == 1: alignment = 1 
                 else: raise CompilerError("Could not resolve alignment value", d)
             
             if alignment <= 0:
                 raise CompilerError("Alignment must be positive", d)

             # Calculate padding needed to align PC
             # logical PC (self.pc) or output PC?
             # Assembler usually aligns current PC. 
             # .org changes PC.
             remainder = self.pc % alignment
             if remainder > 0:
                 padding = alignment - remainder
                 for _ in range(padding):
                     self.emit_byte(0) # Pad with 0

    def visit_instruction(self, inst: Instruction):
        opcode = 0
        mode = inst.mode
        operand = inst.operand
        operand_val = 0
        size = 1

        # Pre-check: parser might label branch targets as ABS.
        # If opcode only supports REL, switch mode.
        if inst.mnemonic in self.opcodes:
            supported = self.opcodes[inst.mnemonic]
            if mode == 'ABS' and 'REL' in supported and 'ABS' not in supported:
                mode = 'REL'

        # Determine mode and value
        if mode == 'IMP' or mode == 'ACC':
            size = 1
        elif mode == '#':
            size = 2
            operand_val = self.resolve_expr(operand)
            if operand_val is None:
                if self.pass_num == 2: raise CompilerError(f"Unresolved symbol in {inst.mnemonic}", inst)
                operand_val = 0
        elif mode == 'REL':
            size = 2
            if self.pass_num == 2:
                target = self.resolve_expr(operand)
                if target is None:
                     raise CompilerError(f"Unresolved branch target for {inst.mnemonic}", inst)
                
                # internal PC is currently at instruction start
                # offset = target - (pc + 2)
                offset = target - (self.pc + 2)
                if offset < -128 or offset > 127:
                    line_info = f" at line {inst.line}" if hasattr(inst, 'line') and inst.line else ""
                    raise CompilerError(f"Branch out of range: {offset}{line_info}", inst)
                operand_val = offset
        elif mode in ['ABS', 'ABSX', 'ABSY']:
            # Check ZP optimization
            # Only optimize if the instruction SUPPORTS ZP!
            # e.g. JMP supports ABS but not ZP.
            supports_zp = False
            if inst.mnemonic in self.opcodes:
                 # Check if equivalent ZP mode exists
                 # ABS->ZP, ABSX->ZPX, ABSY->ZPY
                 zp_mode = mode.replace('ABS', 'ZP')
                 if zp_mode in self.opcodes[inst.mnemonic]:
                     supports_zp = True
            
            val = self.resolve_expr(operand)
            # If val is known and < 256, switch to ZP
            if supports_zp and val is not None and val < 256:
                if mode == 'ABS': mode = 'ZP'
                if mode == 'ABSX': mode = 'ZPX'
                if mode == 'ABSY': mode = 'ZPY'
                size = 2
                operand_val = val
            else:
                 size = 3
                 if val is None:
                     if self.pass_num == 2: raise CompilerError(f"Unresolved symbol in {inst.mnemonic}", inst)
                     val = 0
                 operand_val = val
        elif mode in ['IND', 'INDX', 'INDY']:
             # IND (JMP) is 3 bytes. INDX/INDY are ZP indirects (2 bytes).
             # 65C02 adds:
             # ADC (zp) -> IND (2 bytes)
             # JMP (abs,x) -> INDX (3 bytes)
             
             if mode == 'IND':
                 if inst.mnemonic == 'JMP':
                     size = 3
                 else:
                     # 65C02 'ADC (zp)' etc.
                     size = 2
             elif mode == 'INDX':
                 if inst.mnemonic == 'JMP':
                     # 65C02 JMP (abs,x)
                     size = 3
                 else:
                     size = 2
             else: # INDY
                 size = 2
             operand_val = self.resolve_expr(operand)
             if operand_val is None:
                 if self.pass_num == 2: raise CompilerError(f"Unresolved symbol in {inst.mnemonic}", inst)
                 operand_val = 0
        
        # Emit
        if self.pass_num == 1:
            self.pc += size
        else:
            # Look up opcode
            if inst.mnemonic not in self.opcodes:
                 raise CompilerError(f"Unknown instruction {inst.mnemonic}", inst)
            
            modes = self.opcodes[inst.mnemonic]
            if mode not in modes:
                 # Should have been handled above or is invalid
                 raise CompilerError(f"Mode {mode} not supported for {inst.mnemonic}", inst)
            
            opcode = modes[mode]
            self.emit_byte(opcode)
            
            if size == 2:
                # REL offset is signed, byte() handles 0-255. 
                # Need to convert signed to unsigned byte.
                if mode == 'REL':
                     self.emit_byte(operand_val & 0xFF)
                else:
                     self.emit_byte(operand_val)
            elif size == 3:
                self.emit_word(operand_val)

    def resolve_expr(self, expr):
        if isinstance(expr, int): return expr
        if isinstance(expr, Unresolved):

            if expr.type == 'ADDRESS':
                return self.symbols.get(expr.name)
            if expr.type == 'LOCAL_REL':
                # Parse "1f" or "1b"
                direction = expr.name[-1]
                label_name = expr.name[:-1]
                
                if label_name not in self.local_labels:
                    # In pass 1, might not be seen yet (forward ref), return 0
                    if self.pass_num == 1: return 0
                    return None
                    
                locations = self.local_labels[label_name]
                
                # Use current PC to find closest
                # PC is at start of instruction? Yes, self.pc tracks it.
                # However, during operand resolution, self.pc is at start of this instruction.
                current_pc = self.pc
                
                target = None
                
                if direction == 'f':
                    # Find first location > current_pc
                    # locations should be sorted as we append in order
                    for loc in locations:
                        if loc > current_pc:
                            target = loc
                            break
                    
                    if target is None:
                         # Pass 1: might not be seen yet
                         if self.pass_num == 1: return 0
                         return None
                         
                elif direction == 'b':
                    # Find last location <= current_pc
                    # Actually local label definition is unlikely to be AT current PC 
                    # unless label is defined inside instruction? Impossible.
                    # Usually label is before instruction.
                    # so < current_pc.
                    # "b" searches backwards from current instruction.
                    # so we want max(loc) where loc < current_pc?
                    # Or <= ? If we are at "1: beq 1b". PC is at beq. Label 1 is at beq.
                    # That loops to itself.
                    # So <= is correct.
                    
                    # Iterate backwards
                    for loc in reversed(locations):
                        if loc <= current_pc:
                            target = loc
                            break
                    
                    if target is None:
                         # Pass 1: return 0
                         if self.pass_num == 1: return 0
                         return None
                
                return target

            # Handle LOW/HIGH logic here or during emit?
            # If value is resolved, apply low/high.
            val = self.symbols.get(expr.name)
            if val is None: return None
            if expr.type == 'LOW': return val & 0xFF
            if expr.type == 'HIGH': return (val >> 8) & 0xFF
            return val
        if isinstance(expr, BinaryExpr):
            lhs = self.resolve_expr(expr.left)
            rhs = self.resolve_expr(expr.right)
            if lhs is None or rhs is None: return None
            if expr.op == '+': return lhs + rhs
            if expr.op == '-': return lhs - rhs
        return None

    def emit_byte(self, val):
        if self.pass_num == 2:
            self.bytes.append(val & 0xFF)
        self.pc += 1

    def emit_word(self, val):
        if self.pass_num == 2:
            self.bytes.append(val & 0xFF)
            self.bytes.append((val >> 8) & 0xFF)
        self.pc += 2
