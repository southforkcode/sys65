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
        -- We will try to get "screen text" in various ways
        
        try
            set my_text to screen text
            return "Got screen text directly (class: " & (class of my_text) & ")"
        on error e
            -- continue
        end try
        
        try
           set my_text_2 to (get screen text)
           return "Class: " & (class of my_text_2) & " | Content: " & my_text_2
        on error e
           return "Error getting screen text: " & e
        end try
        
    end tell
end tell
'''

print("Running diagnostic...")
run_applescript(script)
