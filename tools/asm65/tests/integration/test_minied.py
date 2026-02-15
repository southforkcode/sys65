import subprocess
import time
import os
import sys

# Configuration
HEX_FILE = "/tmp/minied.hex"
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
            
            -- Setup Content for Find Test
            type text "A" & return
            delay 0.5
            type text "Context Before 1" & return
            type text "Context Before 2" & return
            type text "The Target Line" & return
            type text "Context After 1" & return
            type text "Context After 2" & return
            type text "Another Target Line" & return
            type text "." & return
            delay 0.5
            
            -- Test Find
            type text "F *Target*" & return
            delay 2.0
            
            -- Find Next
            type text "N" & return
            delay 2.0
            
            -- Quit
            type text "." & return
            delay 1.0
            
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
    print("Beginning automated test sequence.")
    if not compile_asm():
        print("Test failed at compilation step.")
        # Continue execution to allow debugging of python script even if compile fails (handled by called process error usually)
        # But here we exit
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
        # Output might be messy, print it all
        print(output)
        print("--------------------------------")
        
        # Validation Logic
        failures = []
        
        if "The Target Line" not in output:
            failures.append("Missed first match of 'The Target Line'")
            
        if "Another Target Line" not in output:
            failures.append("Missed second match 'Another Target Line'")
            
        if "Context Before 2" not in output:
            failures.append("Missing context (before)")
            
        if "Context After 1" not in output:
            failures.append("Missing context (after)")
            
        if "NEXT/CANCEL?" not in output:
            failures.append("Missing Prompt")

        if not failures and "Screen capture failed" not in output:
            print("SUCCESS: Find command worked as expected with Context and Next.")
            sys.exit(0)
        else:
            print("FAILURE:")
            for f in failures:
                print(f" - {f}")
            if "Screen capture failed" in output:
                print(" - Could not capture screen text from Virtual ][")
            
            print("\n------------------------------")
            print("DEBUG: Full Screen Text START:")
            print(output)
            print("DEBUG: Full Screen Text END")
            print("------------------------------")
            sys.exit(1)
    else:
        print("Failed to get output from Virtual ][.")
        sys.exit(1)

if __name__ == "__main__":
    main()
