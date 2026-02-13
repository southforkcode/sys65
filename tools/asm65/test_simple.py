import subprocess

def run_applescript(script):
    try:
        result = subprocess.run(
            ["osascript", "-e", script], 
            capture_output=True, 
            text=True, 
            check=True
        )
        print(f"DEBUG: stdout: '{result.stdout.strip()}'")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}")
        return None

script = '''
tell application "Virtual ]["
    activate
    tell front machine
        set output to ""
        
        try
            set t1 to screen text
            set output to output & "screen text type: " & (class of t1) & return
        on error e
            set output to output & "screen text failed: " & e & return
        end try

        try
            set t2 to compact screen text
            set output to output & "compact screen text type: " & (class of t2) & return
        on error e
            set output to output & "compact screen text failed: " & e & return
        end try
        
        return output
    end tell
end tell
'''

print("Running simple connection test...")
run_applescript(script)
