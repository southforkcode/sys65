import sys
import os
import time
import subprocess
import subprocess

# Add the project root to sys.path to allow importing from tools
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

# Constants from minied.asm
MAX_LINES = 1024
BUFFER_SIZE = 0x4000 # 16KB

def get_virtual_ii_output():
    """Retrieves the current text from the Virtual ][ screen via clipboard."""
    try:
        # Robust Clipboard Capture Strategy
        # Based on test_minied_buffer_status.py
        script = """
        tell application "Virtual ]["
            activate
            tell front machine
                -- 1. Clear Clipboard (to detect failure)
                set the clipboard to "EMPTY_CLIPBOARD"
                delay 0.5
                
                -- 2. Select All and Copy via System Events
                tell application "System Events"
                    keystroke "a" using command down
                    delay 1.0
                    keystroke "c" using command down
                    delay 2.0
                end tell
                
                -- 3. Return Clipboard with Error Handling
                try
                    return the clipboard
                on error
                    return "EMPTY_CLIPBOARD"
                end try
            end tell
        end tell
        """
        # We use osascript directly to force 'as text' casting which appscript might handle differently
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"OSASCRIPT ERROR: {result.stderr}")
            if "EMPTY_CLIPBOARD" in result.stdout:
                 return "" # Failed to copy
            return ""
            
        output = result.stdout.strip()
        if output == "EMPTY_CLIPBOARD":
            print("OSASCRIPT WARN: Clipboard was not updated (Empty).")
            return ""
            
        return output
    except Exception as e:
        print(f"Error getting output: {e}")
        return ""

def run_test():
    print("Starting MiniEd Constraint Test...")
    
    # 1. Compile MiniEd Test Build (Reduced Limits via -D flags)
    print("Compiling Test Build (Limits: 10 lines, 256 bytes)...")
    subprocess.run([".venv/bin/python", "tools/asm65/asm65.py", "-f", "hex", 
                    "-DMAX_LINES_ARG=10", "-DMEM_LIMIT_ARG=0x4100",
                    "tools/asm65/examples/minied/minied.asm", "minied.hex"], check=True)
    
    # Validates hex file existence
    if not os.path.exists("minied.hex"):
        print("Error: minied.hex not found after compilation.")
        return ["Compilation Failed"]

    with open("minied.hex", "r") as f:
        hex_lines = f.readlines()

    # Construct the hex entry commands
    hex_entry_cmds = ""
    for line in hex_lines:
        line = line.strip()
        if not line: continue
        safe_line = line.replace('"', '\\"')
        hex_entry_cmds += f'keystroke "{safe_line}"\n'
        hex_entry_cmds += 'keystroke return\n'
        hex_entry_cmds += 'delay 0.05\n'
    
    # 2. Upload Sequence following AGENT_INSTRUCTIONS
    print("Initiating Upload Sequence...")

    # Helper for AppleScript Execution
    def run_applescript(script_content):
        result = subprocess.run(['osascript', '-e', script_content], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"AppleScript Error: {result.stderr}")
        return result.stdout

    # A. Reset Machine
    print("Step A: Resetting Machine...")
    script_reset = """
    tell application "System Events"
        tell application process "Virtual ]["
            set frontmost to true
            try
                click menu item "Reset" of menu "Machine" of menu bar 1
            on error
                -- Try typical keystroke fallback if menu not found (Cmd-Ctrl-Reset is hard to script directly reliably)
                -- Just logging warning
                error "Could not click Reset menu"
            end try
        end tell
    end tell
    """
    run_applescript(script_reset)
    time.sleep(1.5) # Wait for Reset cycle

    # B. Enter Monitor
    print("Step B: Entering Monitor (CALL -151)...")
    script_monitor = """
    tell application "System Events"
        tell application process "Virtual ]["
            set frontmost to true
            keystroke "CALL -151"
            keystroke return
        end tell
    end tell
    """
    run_applescript(script_monitor)
    time.sleep(0.5)

    # C. Verify Monitor Prompt '*'
    print("Step C: Verifying Monitor Prompt...")
    monitor_active = False
    for attempt in range(5):
        screen = get_virtual_ii_output()
        # Look for the last line ending in '*' or containing '*'
        if "*" in screen:
            print(f"Confirmed Monitor Prompt '*' (Attempt {attempt+1})")
            monitor_active = True
            break
        print(f"Waiting for prompt... (Attempt {attempt+1})")
        time.sleep(1.0)
    
    if not monitor_active:
        print("WARNING: Could not verify Monitor prompt '*'. Proceeding blindly (CI limitation likely).")

    # D. Upload Hex
    print("Step D: Uploading Hex...")
    # Chunking lines to avoid overwhelming buffer? 
    # Validating format: address: byte byte ... (Produced by asm65.py -f hex)
    
    # We construct one script for the hex dump
    script_upload = f"""
    tell application "System Events"
        tell application process "Virtual ]["
            set frontmost to true
            {hex_entry_cmds}
            delay 1.0
            
            -- Start Program (2000G)
            keystroke "2000G"
            keystroke return
        end tell
    end tell
    """
    run_applescript(script_upload)
    
    print("Upload complete. Program started.")
    time.sleep(2) # Wait for startup

    failures = []

    # Helper to send text via AppleScript
    def send_text(text):
        # Escape quotes for AppleScript
        safe_text = text.replace('"', '\\"').replace('\'', '\\\'')
        script = f"""
        tell application "System Events"
            tell application process "Virtual ]["
                set frontmost to true
                keystroke "{safe_text}"
                delay 0.1
            end tell
        end tell
        """
        subprocess.run(['osascript', '-e', script], check=False)

    def send_return():
        script = """
        tell application "System Events"
            tell application process "Virtual ]["
                set frontmost to true
                keystroke return
                delay 0.1
            end tell
        end tell
        """
        subprocess.run(['osascript', '-e', script], check=False)
        
    def get_output():
        return get_virtual_ii_output()

    # Test 1: Exceed 10 lines
    print("Test 1: Exceeding 10 lines limit...")
    
    # NOTE: Buffer is initially clean (fresh boot), so N command won't prompt.
    # We can just start filling.
    
    # Use Fill Command: * 11
    # This should generate 11 lines. Limit is 10.
    send_text("* 11")
    send_return()

    # Wait for completion/error - increased delay for Applescript
    time.sleep(2.0)
    output = get_output()
    
    if "Error: Too Many Lines" in output:
        print("PASS: Caught Line Limit")
    else:
        print("FAIL: Did not see 'Error: Too Many Lines'")
        print(f"Captured Output: {output!r}")
        failures.append("Line Limit Check Failed")

    # Test 2: Buffer Full
    print("Test 2: Exceeding Buffer Limit...")
    
    # Clear buffer: N -> Y (Buffer is dirty from Test 1, so prompt expected)
    send_text("N")
    send_return()
    time.sleep(0.5)
    send_text("Y")
    send_return()
    time.sleep(0.5)
    
    # Fill Buffer: * 50
    # 50 * 17 = 850 bytes > 256. Limit 256.
    send_text("* 50")
    send_return()
    
    time.sleep(2.0)
    output = get_output()
    
    if "Error: Buffer Full" in output:
        print("PASS: Caught Buffer Full")
    else:
        print("FAIL: Did not see 'Error: Buffer Full'")
        print(f"Captured Output: {output!r}")
        failures.append("Buffer Limit Check Failed")
        
    return failures

if __name__ == "__main__":
    failures = run_test()
    if failures:
        print("FAILURES Found:")
        for f in failures:
            print(f"- {f}")
        sys.exit(1)
    else:
        print("Test Passed (or skipped).")
