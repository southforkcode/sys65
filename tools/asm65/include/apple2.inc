; apple2.inc
; Apple II Constants and Routines

; Keyboard Routine (Read Key - Wait for keypress)
; Returns ASCII code in Accumulator with high bit set.
GETCH = $FD0C

; Character Out Routine (Print character in A)
; Prints character in Accumulator to current cursor position.
; Should have high bit set for normal video.
COUT = $FDED

; ASCII Codes (with high bit set for Apple II normal video)
CR = $8D    ; Carriage Return
BS = $88    ; Backspace (CTRL-H)
ESC = $9B   ; Escape

; Monitor Routines
PRBYTE = $FDDA ; Print byte in A as hex

; --- Common Zero Page Locations ---
; (Refer to Apple II Zero Page Usage documentation)

; Text Window (Define the active screen area)
WNDLFT = $20 ; Left margin (0..39)
WNDWDTH = $21 ; Window width (1..40)
WNDTOP = $22 ; Top margin (0..23)
WNDBTM = $23 ; Bottom margin (0..24)

; Cursor Position
CH = $24 ; Cursor Horizontal (0..39)
CV = $25 ; Cursor Vertical (0..23)

; Text Screen Line Base Address (Pointer to start of current line)
BASL = $28 ; Base address low byte
BASH = $29 ; Base address high byte

; Prompt Character
PROMPT_CHAR = $33

; Monitor Scratchpad / Registers (Useful for passing args to monitor routines)
A1L = $3C ; Monitor Argument 1 Low
A1H = $3D ; Monitor Argument 1 High
A2L = $3E ; Monitor Argument 2 Low
A2H = $3F ; Monitor Argument 2 High
A4L = $42 ; Monitor Argument 4 Low
A4H = $43 ; Monitor Argument 4 High

; Random Number (Updated by Monitor KEYIN routine)
RNDL = $4E ; Random number low byte
RNDH = $4F ; Random number high byte

; --- Monitor ROM Routines (Reference: Apple II Monitors Peeled) ---

; -- Screen Output --
; COUT is already defined ($FDED)
COUT1   = $FDF0 ; Output char to screen at current cursor position
COUTZ   = $FDF6 ; Output char to screen (handles control codes, but no INVFLG)
CROUT   = $FD8E ; Generate a Carriage Return
PRERR   = $FF2D ; Prints "ERR" and rings the bell
BELL    = $FF3A ; Ring the system bell
VTAB    = $FC22 ; Set vertical cursor position (CV) to line in Accumulator
VTABZ   = $FC24 ; Set BASL,H from A-reg (line) and WNDLFT (ignore CV)
TABV    = $FB5B ; Set vertical position (like VTAB)
CLREOL  = $FC9C ; Clear from cursor to end of line
CLREOP  = $FC42 ; Clear from cursor to end of page (window)
HOME    = $FC58 ; Clear window and put cursor at top left
SCROLL  = $FC70 ; Scroll the window up one line

; -- Keyboard Input --
; GETCH/RDKEY is already defined ($FD0C)
RDCHAR  = $FD35 ; Get next char (handles ESC codes)
GETLN   = $FD6A ; Print prompt, get line of input (into buffer at $0200)
GETLNZ  = $FD67 ; Output CR, then GETLN
NOTCR   = $FD3D ; Echo input char with inverse video, handle backspace/cancel
CANCEL  = $FD62 ; Handle 'Cancel' (Ctrl-X) - prints backslash and resets line

; -- Graphics / Text Modes --
SETTXT  = $FB39 ; Set Text Mode (Reset window to full screen)
SETGR   = $FB40 ; Set Graphics Mode (Mixed)
SETWND  = $FB4B ; Set window top (WNDTOP) from A-reg
SETINV  = $FE80 ; Set Inverse Video (white on black, INVFLG=$3F)
SETNORM = $FE84 ; Set Normal Video (white on black, INVFLG=$FF)

; -- Miscellaneous --
SAVE    = $FF4A ; Save registers (A,X,Y,P,S) to $45-$49
RESTORE = $FF3F ; Restore registers from $45-$49
MON     = $FF65 ; Enter Monitor (Beep and wait for command)
MONZ    = $FF69 ; Enter Monitor (No beep)
RESET   = $FF59 ; Monitor Reset Handler (Warm Start)

; -- Hardware I/O Locations --
KBD     = $C000 ; Keyboard Data (High bit set if key pressed)
KBDSTRB = $C010 ; Keyboard Strobe (Clear high bit)
SPKR    = $C030 ; Toggle Speaker (Read to toggle)
TXTSET  = $C051 ; Switch to Text Mode
TXTCLR  = $C050 ; Switch to Graphics Mode
MIXSET  = $C053 ; Mix Text and Graphics
MIXCLR  = $C052 ; Full Screen Graphics
HIRES   = $C057 ; Hi-Res Graphics
LORES   = $C056 ; Lo-Res Graphics
