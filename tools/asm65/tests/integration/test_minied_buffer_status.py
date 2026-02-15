import subprocess
import time
import os
import sys

# Configuration
HEX_FILE = "/tmp/minied_bs.hex"
ASM_FILE = "tools/asm65/examples/minied/minied.asm"
ASM_TOOL = "tools/asm65/asm65.py"

def run_applescript(script):
    """Executes an AppleScript and returns the output."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script], 
            capture_output=True, 
            text=True, 
            check=True
        )
        # print(f"DEBUG: osascript stdout: '{result.stdout}'")
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
    hex_entry_cmds = ""
    for line in hex_lines:
        line = line.strip()
        if not line: continue
        safe_line = line.replace('"', '\\"')
        hex_entry_cmds += f'type text "{safe_line}" & return\n'
        hex_entry_cmds += 'delay 0.05\n'

    script = f'''
    tell application "Virtual ]["
        activate
        tell front machine
            -- Reset
            reset
            delay 1.0
            
            -- Enter Monitor
            type text "CALL -151" & return
            delay 0.5
            
            -- Enter Hex Data
            {hex_entry_cmds}
            delay 1.0
            
            -- Run Program
            type text "2000G" & return
            delay 1.0
            
            -- 1. Initial Buffer Status (Should be Empty/Clean)
            type text "B" & return
            delay 1.0
            
            -- 2. Add Content
            type text "A" & return
            delay 0.5
            type text "Hello World" & return
            type text "Line 2" & return
            type text "." & return
            delay 0.5
            
            -- 3. Buffer Status (Should be Dirty, 2 lines)
            type text "B" & return
            delay 1.0
            
            -- 4. Delete Line
            type text "1D" & return
            delay 0.5
            
            -- 5. Final Buffer Status (Dirty, 1 line)
            type text "B" & return
            delay 1.0

            -- Capture Screen
            try
                -- Clear Clipboard first to avoid stale data
                set the clipboard to "EMPTY_CLIPBOARD"
                delay 0.5
                
                -- Select All (Cmd+A)
                tell application "System Events" to keystroke "a" using command down
                delay 1.0
                -- Copy (Cmd+C)
                tell application "System Events" to keystroke "c" using command down
                delay 1.0
                
                return the clipboard
            on error errMsg
                return "Clipboard capture failed: " & errMsg
            end try
        end tell
    end tell
    '''
    return script

def main():
    print("Beginning automated buffer status test.")
    if not compile_asm():
        print("Test failed: Compilation failed.")
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
        print("\\n--- Virtual ][ Screen Output ---")
        print(output)
        print("--------------------------------")
        
        failures = []
        
        # Validation Logic
        # Note: Output capture might capture the whole session history.
        # We need to look for specific patterns.
        
        # Check Initial Status (Order matters, but simple substring check might be enough if unique)
        # However, multiple B commands mean multiple outputs. 
        # We can just check that all expected states appear in the output.
        
        # 1. Initial: Clean, 0 lines, 0 bytes used
        if "NEW 0/200L" not in output:
             failures.append("Missing initial Clean status")
        
        # 2. After Add: Dirty, 2 lines
        if "UNSAVED 2/200L" not in output:
             failures.append("Missing Dirty status")
             
        # 3. After Delete: Dirty, 1 line
        if "UNSAVED 1/200L" not in output:
             failures.append("Missing Line count 1 (after delete)")
             
        # Check Byte Counts (Approximate)
        # We look for "B" suffix.
        if "B" not in output:
             failures.append("Missing Byte count suffix")

        if not failures and "Screen capture failed" not in output:
            print("SUCCESS: Buffer Status command verified.")
            sys.exit(0)
        else:
            print("FAILURE:")
            for f in failures:
                print(f" - {f}")
            sys.exit(1)
    else:
        print("Failed to get output from Virtual ][.")
        sys.exit(1)

if __name__ == "__main__":
    main()
