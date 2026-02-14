import subprocess
import time
import os
import sys

# Configuration
HEX_FILE = "/tmp/minied.hex"
ASM_FILE = "examples/minied/minied.asm"
ASM_TOOL = "asm65.py"

def run_applescript(script):
    """Executes an AppleScript and returns the output."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script], 
            capture_output=True, 
            text=True, 
            check=True
        )
        print(f"DEBUG: osascript stdout: '{result.stdout}'")
        print(f"DEBUG: osascript stderr: '{result.stderr}'")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"AppleScript Error: {e.stderr}")
        return None

def compile_asm():
    """Compiles the assembly file to hex."""
    print(f"Compiling {ASM_FILE}...")
    try:
        subprocess.run(
            ["python3", ASM_TOOL, "-f", "hex", ASM_FILE, HEX_FILE],
            check=True,
            capture_output=True 
        )
        print("Compilation successful.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Compilation failed: {e.stderr}")
        return False

def generate_test_script(hex_lines):
    """Generates the AppleScript to drive Virtual ][."""
    
    # Construct the hex entry commands
    # To avoid overwhelming the emulator buffer, we can do it line by line
    hex_entry_cmds = ""
    for line in hex_lines:
        line = line.strip()
        if not line: continue
        # Escape quotes if necessary
        safe_line = line.replace('"', '\\"')
        hex_entry_cmds += f'type text "{safe_line}" & return\n'
        hex_entry_cmds += 'delay 0.2\n' # Small delay

    script = f'''
    tell application "Virtual ]["
        activate
        tell front machine
            -- Reset to get to known state
            reset
            delay 2.0
            
            -- Enter Monitor
            type text "CALL -151" & return
            delay 0.5
            
            -- Enter Hex Data
            {hex_entry_cmds}
            
            -- Run Program
            type text "2000G" & return
            delay 1.0
            
            -- 1. Add some lines
            type text "A" & return
            delay 0.5
            type text "Line 1 Original" & return
            delay 0.2
            type text "Line 2 To Keep" & return
            delay 0.2
            type text "." & return
            delay 0.5
            
            -- 2. Print initial
            type text "P" & return
            delay 1.0
            
            -- 3. Edit Line 1 (Replace)
            type text "E 1" & return
            delay 1.0
            type text "Line 1 Edited" & return
            delay 0.5
            
            -- 4. Print again
            type text "P" & return
            delay 1.0

            -- 5. Edit Line 2 (Cancel)
            type text "E 2" & return
            delay 1.0
            type text "." & return
            delay 0.5

            -- 6. Print final
            type text "P" & return
            delay 1.0
            
            return "Test sequence completed."
        end tell
    end tell
    '''
    return script

def main():
    print("Beginning automated test sequence.")
    if not compile_asm():
        print("Test failed at compilation step.")
        sys.exit(1)
        
    if not os.path.exists(HEX_FILE):
        print(f"Error: {HEX_FILE} not found.")
        sys.exit(1)
        
    with open(HEX_FILE, 'r') as f:
        hex_lines = f.readlines()
        
    print(f"Loaded {len(hex_lines)} lines of hex data.")
    print("Running automated test via Virtual ][...")
    script = generate_test_script(hex_lines)
    
    output = run_applescript(script)
    
    if output:
        print("\n--- Virtual ][ Screen Output (Clipboard) ---")
        print(output)
        print("--------------------------------------------")
        
        # Simple analysis
        success = False
        if "C1" in output or "41" in output: # 'A' is $41, with high bit $C1
             print("SUCCESS: Found 'A' char code in output!")
             success = True
        elif "A" in output and "?" in output:
             print("PARTIAL: Saw 'A' input attempt, but maybe code mismatch.")
        else:
             print("FAILURE: Did not detect expected patterns.")
             
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        print("Failed to get output from Virtual ][.")
        sys.exit(1)

if __name__ == "__main__":
    main()
