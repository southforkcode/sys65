
import sys
import os
import time
import subprocess

# Add the project root to sys.path to allow importing from tools
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

# Constants
MAX_LINES = 1024
BUFFER_SIZE = 0x4000 # 16KB

def get_virtual_ii_output():
    """Retrieves the current text from the Virtual ][ screen via clipboard."""
    try:
        # Robust Clipboard Capture Strategy
        script = """
        tell application "Virtual ]["
            activate
            tell front machine
                -- 1. Clear Clipboard (to detect failure)
                set the clipboard to "EMPTY_CLIPBOARD"
                delay 0.5
                
                -- 2. Select All and Copy via System Events
                tell application "System Events"
                    tell process "Virtual ]["
                        set frontmost to true
                        try
                            click menu item "Select All" of menu "Edit" of menu bar 1
                            delay 1.0
                            click menu item "Copy" of menu "Edit" of menu bar 1
                            delay 1.0
                        on error
                            -- Fallback to keystrokes if menus fail (rare)
                            keystroke "a" using command down
                            delay 1.0
                            keystroke "c" using command down
                            delay 1.0
                        end try
                    end tell
                end tell
                
                -- 3. Return Clipboard with Error Handling
                try
                    return (the clipboard as text)
                on error
                    return "ERROR_GETTING_TEXT"
                end try
            end tell
        end tell
        """
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"OSASCRIPT ERROR: {result.stderr}")
            return ""
            
        output = result.stdout.strip()
        if output == "EMPTY_CLIPBOARD":
            return ""
            
        return output
    except Exception as e:
        print(f"Error getting output: {e}")
        return ""

def run_test():
    print("Starting MiniEd Append Regression Test...")
    
    # 1. Compile MiniEd
    print("Compiling Minied...")
    subprocess.run([".venv/bin/python", "tools/asm65/asm65.py", "-f", "hex", 
                    "-DDEBUG",
                    "tools/asm65/examples/minied/minied.asm", "minied.hex"], check=True, capture_output=True)
    
    if not os.path.exists("minied.hex"):
        print("Error: minied.hex not found.")
        return ["Compilation Failed"]

    with open("minied.hex", "r") as f:
        hex_lines = f.readlines()

    hex_entry_cmds = ""
    for line in hex_lines:
        line = line.strip()
        if not line: continue
        safe_line = line.replace('"', '\\"')
        hex_entry_cmds += f'keystroke "{safe_line}"\n'
        hex_entry_cmds += 'keystroke return\n'
        hex_entry_cmds += 'delay 0.05\n'
    
    # 2. Upload Sequence
    print("Initiating Upload Sequence...")

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
                error "Could not click Reset menu"
            end try
        end tell
    end tell
    """
    run_applescript(script_reset)
    time.sleep(1.5)

    # B. Enter Monitor
    print("Step B: Entering Monitor...")
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

    # C. Upload Hex
    print("Step C: Uploading Hex...")
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
    time.sleep(2) 

    failures = []

    def send_text(text):
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

    # TEST SCENARIO
    
    # 1. Start clean (N -> Y)
    print("Test 1: Clearing Buffer")
    send_text("N")
    send_return()
    time.sleep(0.5)
    send_text("Y") # Confirm if needed, harmless if not
    send_return()
    time.sleep(0.5)
    
    # 2. Check Status (B)
    print("Test 2: Checking Buffer Status (Empty)")
    send_text("B")
    send_return()
    time.sleep(1.0)
    output = get_virtual_ii_output()
    # Expect: NEW 0/1024L 0/16384B (approx)
    if not "NEW 0/" in output:
         print("FAIL: Buffer not empty or status unexpected")
         print(f"Output: {output}")
         failures.append("Buffer Status Empty Failed")
    else:
         print("PASS: Buffer Empty Confirmed")

    # 3. Append 1 Line
    print("Test 3: Appending Line 1")
    send_text("A")
    send_return()
    time.sleep(0.5)
    send_text("Hello World Line 1")
    send_return()
    send_text(".") # Exit append
    send_return()
    time.sleep(0.5)
    
    # 4. Print Buffer
    print("Test 4: Verifying Line 1")
    send_text("P")
    send_return()
    time.sleep(1.0)
    output = get_virtual_ii_output()
    if "1 Hello World Line 1" in output:
        print("PASS: Line 1 found")
    else:
        print("FAIL: Line 1 not found")
        print(f"Output: {output}")
        failures.append("Line 1 Verification Failed")

    # 5. Append Line 2
    print("Test 5: Appending Line 2")
    send_text("A")
    send_return()
    time.sleep(0.5)
    send_text("This is Line 2")
    send_return()
    send_text(".") # Exit append
    send_return()
    time.sleep(0.5)
    
    # 6. Verify Two Lines
    print("Test 6: Verifying Two Lines")
    send_text("P")
    send_return()
    time.sleep(1.0)
    output = get_virtual_ii_output()
    
    if "1 Hello World Line 1" in output and "2 This is Line 2" in output:
        print("PASS: Both lines found")
    else:
        print("FAIL: Both lines not found")
        print(f"Output: {output}")
        failures.append("Line 2 Verification Failed")

    return failures

if __name__ == "__main__":
    failures = run_test()
    if failures:
        print("FAILURES Found:")
        for f in failures:
            print(f"- {f}")
        sys.exit(1)
    else:
        print("All Tests Passed.")
