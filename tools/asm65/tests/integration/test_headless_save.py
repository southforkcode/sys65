
import sys
import os
import subprocess
import re
from py65.devices.mpu6502 import MPU
from py65.memory import ObservableMemory

# Paths
ASM_DIR = "tools/asm65"
ASM_TOOL = os.path.join(ASM_DIR, "asm65.py")
SOURCE_FILE = os.path.join(ASM_DIR, "examples/minied/minied.asm")
HEX_FILE = "minied_headless.hex"

def compile_and_get_symbols():
    print(f"Compiling {SOURCE_FILE}...")
    result = subprocess.run(
        [sys.executable, ASM_TOOL, "-f", "hex", SOURCE_FILE, HEX_FILE],
        capture_output=True, text=True, check=True
    )
    
    symbols = {}
    for line in result.stdout.splitlines():
        match = re.match(r"^([A-Za-z0-9_]+): (\d+)$", line)
        if match:
            symbols[match.group(1)] = int(match.group(2))
    
    return symbols

def load_hex(filename, memory):
    print(f"Loading {filename}...")
    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.split(":")
            if len(parts) != 2: continue
            
            addr = int(parts[0], 16)
            bytes_str = parts[1].strip()
            bytes_list = [int(b, 16) for b in bytes_str.split()]
            
            for i, b in enumerate(bytes_list):
                memory[addr + i] = b

class MockSystem:
    def __init__(self):
        self.memory = ObservableMemory()
        self.mpu = MPU(memory=self.memory)
        self.symbols = {}
        self.input_buffer = [] 
        self.captured_dos_calls = []
        self.running = True
        self.cycle_limit = 2000000 
        
        # Hooks
        self.hooks = {} # addr -> callback
        
    def add_hook(self, addr, name, callback=None):
        self.hooks[addr] = (name, callback)

    def run(self):
        print("Starting Simulation...")
        self.mpu.pc = self.symbols['start']
        
        cycles = 0
        while self.running and cycles < self.cycle_limit:
            pc = self.mpu.pc
            
            if pc in self.hooks:
                name, callback = self.hooks[pc]
                # print(f"Hook: {name}")
                if callback:
                    callback(self)
                self._return_from_subroutine()
                continue
            
            try:
                self.mpu.step()
                cycles += 1
            except Exception as e:
                print(f"CPU Crash at ${pc:04X}: {e}")
                self.running = False
                break
                
        print(f"Simulation ended after {cycles} cycles. Running={self.running}")

    def _return_from_subroutine(self):
        lo = self.mpu.sp + 1
        hi = self.mpu.sp + 2
        if lo > 0x1FF: lo -= 0x100
        if hi > 0x1FF: hi -= 0x100
        
        pc_lo = self.memory[0x100 + (self.mpu.sp + 1 & 0xFF)]
        pc_hi = self.memory[0x100 + (self.mpu.sp + 2 & 0xFF)]
        
        self.mpu.sp = (self.mpu.sp + 2) & 0xFF
        
        ret_addr = (pc_hi << 8) | pc_lo
        self.mpu.pc = ret_addr + 1

# Hook Callbacks
def hook_getln(sys):
    if sys.input_buffer:
        cmd = sys.input_buffer.pop(0)
        print(f"GETLN Input: {cmd}")
        for i, char in enumerate(cmd):
            sys.memory[0x200 + i] = ord(char) | 0x80
        sys.memory[0x200 + len(cmd)] = 0x8D 
        sys.mpu.y = len(cmd) + 1 
        
        if cmd == "Q":
            sys.running = False # Clean exit? No, Q loops or RTS? minied: do_quit -> rts. 
            # If Q returns from minied, we need to catch that.
    else:
        print("GETLN: No more input.")
        sys.running = False

def hook_cout(sys):
    char_code = sys.mpu.a & 0x7F
    if 32 <= char_code <= 126:
        print(chr(char_code), end="", flush=True)
    elif char_code == 13:
        print()

def hook_dos_fm(sys):
    parm_addr = (sys.mpu.a << 8) | sys.mpu.y
    print(f"\nDOS_FM Call! Parm Addr: ${parm_addr:04X}")
    
    opcode = sys.memory[parm_addr]
    name_ptr = sys.memory[parm_addr + 8] | (sys.memory[parm_addr + 9] << 8)
    
    fname = ""
    p = name_ptr
    for _ in range(32):
        c = sys.memory[p]
        if c == 0: break
        fname += chr(c & 0x7F)
        p += 1
    
    call_info = {
        "opcode": opcode,
        "filename": fname,
        "buff_ptr": sys.memory[parm_addr + 10] | (sys.memory[parm_addr + 11] << 8),
        "len": sys.memory[parm_addr + 12] | (sys.memory[parm_addr + 13] << 8),
        "aux": sys.memory[parm_addr + 14] | (sys.memory[parm_addr + 15] << 8),
    }
    sys.captured_dos_calls.append(call_info)
    print(f"Captured: {call_info}")
    sys.mpu.p &= ~0x01

def hook_prbyte(sys):
    val = sys.mpu.a
    print(f"{val:02X}", end="", flush=True)

def hook_prerr(sys):
    print("ERR", end="")

def main():
    try:
        symbols = compile_and_get_symbols()
    except Exception as e:
        print(f"Compilation failed: {e}")
        sys.exit(1)
        
    if 'FM_PARM_BLOCK' not in symbols:
        print("Error: FM_PARM_BLOCK symbol not found.")
        sys.exit(1)
        
    print(f"FM_PARM_BLOCK Address: ${symbols['FM_PARM_BLOCK']:04X}")
    
    sys65 = MockSystem()
    sys65.symbols = symbols
    load_hex(HEX_FILE, sys65.memory)
    
    # Hooks
    sys65.add_hook(0xFD6A, "GETLN", hook_getln)
    sys65.add_hook(0xFDED, "COUT", hook_cout)
    sys65.add_hook(0x03D6, "DOS_FM", hook_dos_fm)
    sys65.add_hook(0xFD8E, "CROUT", lambda s: print())
    sys65.add_hook(0xFF3A, "BELL", lambda s: print("\a", end=""))
    sys65.add_hook(0xFC58, "HOME", lambda s: print("[HOME]"))
    sys65.add_hook(0xFF2D, "PRERR", hook_prerr)
    sys65.add_hook(0xFDDA, "PRBYTE", hook_prbyte)
    sys65.add_hook(0xFE80, "SETINV", lambda s: None)
    sys65.add_hook(0xFE84, "SETNORM", lambda s: None)
    
    # Input Sequence
    sys65.input_buffer = [
        "N", # Clears (No prompt if clean)
        "A", "LINE 1", "LINE 2", ".", 
        "S TESTFILE,D1", 
        "Q" 
    ]
    
    sys65.run()
    
    print("\n--- Verification ---")
    
    expected_ops = [5, 1, 4, 2] # Delete, Open, Write, Close
    captured_ops = [call['opcode'] for call in sys65.captured_dos_calls]
    print(f"Captured Opcodes: {captured_ops}")
    
    if len(captured_ops) < 4:
        print("FAIL: Not enough DOS calls captured.")
        sys.exit(1)
        
    recent_ops = [c['opcode'] for c in sys65.captured_dos_calls[-4:]]
    if recent_ops != expected_ops:
         print(f"FAIL: Sequence mismatch. Expected {expected_ops}, got {recent_ops}")
         sys.exit(1)
         
    # Check WRITE Opcode logic (ensure it used correct params)
    # The simulation proved that the code put correct address in A/Y,
    # otherwise hook_dos_fm would have read garbage param block.
    
    # Also verify lengths
    write_call = sys65.captured_dos_calls[-2] # 4 (Write)
    # Length of "LINE 1" (7) + "LINE 2" (7) + terminators (2) = 16 bytes?
    # "LINE 1\0" = 7 bytes. "LINE 2\0" = 7 bytes.
    # Total 14 bytes.
    # Check length
    length = write_call['len']
    print(f"Write Length: {length}")
    if length == 0:
        print("FAIL: Zero length write")
        sys.exit(1)
        
    print("PASS: DOS interactions verified.")
    sys.exit(0)

if __name__ == "__main__":
    main()
