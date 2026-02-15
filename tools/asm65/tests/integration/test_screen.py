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
        try
            set lines_list to (get screen text)
            
            -- Coerce to string
            set oldDelims to AppleScript'"'"'s text item delimiters
            set AppleScript'"'"'s text item delimiters to return
            set txt to lines_list as string
            set AppleScript'"'"'s text item delimiters to oldDelims
            
            return txt
        on error e
            return "Error: " & e
        end try
    end tell
end tell
'''
# Fixing syntax error in previous attempt which looked identical? 
# Maybe issue is with Python f-string or escaping? Let's use simple string concat.
script = """
tell application "Virtual ]["
    activate
    tell front machine
        try
            set p to (get screen picture)
            return "Got screen picture (class: " & (class of p) & ")"
        on error e
            return "Error: " & e
        end try
    end tell
end tell
"""

print("Running screen text test...")
run_applescript(script)
