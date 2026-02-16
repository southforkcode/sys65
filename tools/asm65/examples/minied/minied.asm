; ==============================================================================
; MiniEd - A Simple Line Editor for Apple II
; ==============================================================================
;
; MEMORY LAYOUT & BUFFER STRUCTURE:
; ---------------------------------
; The text buffer is a linear sequence of 0-terminated ASCII strings.
;
; [Start: $3000] -> "Line 1\0" "Line 2\0" ... "Line N\0" [End: TEXT_PTR]
;
; - BUFFER_START ($3000): Fixed start of the buffer.
; - TEXT_PTR ($08/$09): Points to the byte *after* the last 0-terminator.
;                       Free space begins here.
; - LINE_IDX: Contains the current number of lines in the buffer.
; - MAX_BUFFER_SIZE: Hard limit on buffer size ($5000 bytes).
; - MAX_LINES: Hard limit on line count (200).
;
; KEY ROUTINES:
; -------------
; - command_loop: Main input loop. Parses single-character commands.
; - get_line_monitor: Wraps Monitor GETLN to read input into internal buffer.
; - puts / puts_inv: Prints 0-terminated strings (Standard / Inverse).
; - shift_up: Shifts buffer content UP (to higher addr) to create a gap.
; - shift_down:
    ; Shift content DOWN (to lower addresses)
    ; Used by delete operations.
    ; Reads from SHIFT_SRC, Writes to SHIFT_DEST

.org $2000

; Include Apple II definitions
.include "apple2.inc"

; Line Buffer storage
; We will store lines as length-prefixed strings? 
; No, let's just make it simple: 0-terminated strings.
; Buffer starts at $3000

; Zero Page usage for our editor
; Using safe locations $06-$09
PTR_L = $06
PTR_H = $07
TEXT_PTR_L = $08
TEXT_PTR_H = $09
EDIT_PTR_L = $0A
EDIT_PTR_H = $0B
SHIFT_SRC_L = $0C
SHIFT_SRC_H = $0D
SHIFT_DEST_L = $0E
SHIFT_DEST_H = $0F

; Generic Memory Move Variables (Aliased for now, or new)
MEM_SRC_L  = $0C ; Same as SHIFT_SRC
MEM_SRC_H  = $0D
MEM_DEST_L = $0E ; Same as SHIFT_DEST
MEM_DEST_H = $0F
MEM_END_L  = $10 ; New ZP variable for End of Source Block
MEM_END_H  = $11

BUFFER_START = $4000
MAX_BUFFER_SIZE = $4000 ; 16K

.ifdef MEM_LIMIT_ARG
    MEM_LIMIT = MEM_LIMIT_ARG
.else
    MEM_LIMIT = $8000 ; End of valid memory (BUFFER_START + MAX_BUFFER_SIZE)
.endif

.ifdef MAX_LINES_ARG
    MAX_LINES = MAX_LINES_ARG
.else
    MAX_LINES = 1024 ; Increased to 1024
.endif
PROMPT = '>' + $80
CMD_BUFFER = $3F00 ; Command line buffer


start:
    ; Initialize text buffer pointer
    lda #<BUFFER_START
    sta TEXT_PTR_L
    lda #>BUFFER_START
    sta TEXT_PTR_H
    
    lda #0
    sta LINE_IDX
    sta LINE_IDX+1
    sta DIRTY_FLAG

    lda #<msg_welcome
    ldx #>msg_welcome
    jsr puts

command_loop:
    ; Set Prompt for Monitor GETLN
    lda #PROMPT
    sta PROMPT_CHAR
    
    ; Use PTR for command buffer
    lda #<CMD_BUFFER
    sta PTR_L
    lda #>CMD_BUFFER
    sta PTR_H
    
    jsr get_line_monitor
    
    ; Check first char
    ldy #0
    
    ; Match handling for both 'a' and 'A'
    ; Make case insensitive (force upper case)
    
    ; look up command from cmd_table
    ldx #0
1:  lda (PTR_L),y 
    ; Convert to upper case (0x61->0x41, 0xE1->0xC1) - ONLY if 'a'..'z'
    cmp #'a'+$80
    bcc _cl_no_case
    cmp #'z'+$80+1
    bcs _cl_no_case
    and #$DF
_cl_no_case:
    cmp cmd_table,x
    beq 1f
    inx
    lda cmd_table,x
    beq cmd_table_end
    jmp 1b
1:  txa
    asl a
    tax
    lda cmd_impl_table,x
    sta cmd_impl
    inx
    lda cmd_impl_table,x
    sta cmd_impl+1
    jmp (cmd_impl)

cmd_table_end:    
    ; Unknown command (unless empty line)
    ; Check if buffer is empty (first char is 0)
    ldy #0
    lda (PTR_L), y
    beq command_loop ; Just ignore empty line (null char)
    
    ; Unknown command
    jsr PRERR
    jsr BELL
    jsr CROUT
    jmp command_loop

do_quit:
    rts

do_home:
    jsr HOME
    jmp command_loop

do_new:
    ; Check if buffer is dirty
    lda DIRTY_FLAG
    beq _dn_clear   ; If 0, clean. Go straight to clear.

    ; Confirmation
    lda #<msg_confirm_new
    ldx #>msg_confirm_new
    jsr puts
    jsr CROUT
    
    jsr get_line_monitor
    
    ldy #0
    lda (PTR_L), y
    cmp #'Y'+$80
    bne _dn_cancel

_dn_clear:
    ; Reset Buffer
    lda #<BUFFER_START
    sta TEXT_PTR_L
    lda #>BUFFER_START
    sta TEXT_PTR_H
    
    lda #0
    sta LINE_IDX
    sta LINE_IDX+1
    sta DIRTY_FLAG
    
    lda #<msg_cleared
    ldx #>msg_cleared
    jsr puts
    jsr CROUT
    jmp command_loop

_dn_cancel:
    jmp command_loop

do_print:
    ; Parse optional arguments
    ; Y points to command char 'P' in CMD_BUFFER
    jsr parse_arg
    bcc _dp_has_arg ; C=0 -> Has Arg
    beq _dp_no_arg  ; C=1, Z=1 -> No Arg
    ; C=1, Z=0 -> Invalid Arg
    jmp _dp_invalid_arg

_dp_has_arg:
    sta TARGET_LINE
    lda PD_VAL+1
    sta TARGET_LINE+1
    jmp _dp_start
    
_dp_invalid_arg:
    jsr PRERR
    jmp command_loop

_dp_no_arg:
    lda #0
    sta TARGET_LINE
    sta TARGET_LINE+1

_dp_start:
    ; Print lines
    lda #<BUFFER_START
    sta PTR_L
    lda #>BUFFER_START
    sta PTR_H
    
    lda #1
    sta CURRENT_LINE
    lda #0
    sta CURRENT_LINE+1 ; Initialize High byte
    
    ; ldx LINE_IDX -> 16-bit check
    lda LINE_IDX
    ora LINE_IDX+1
    beq print_done
    
print_line_loop:
    ; Check if we should print this line
    lda TARGET_LINE
    ora TARGET_LINE+1
    beq _pl_do_print ; 0 = print all
    
    ; Compare TARGET_LINE vs CURRENT_LINE (16-bit)
    lda TARGET_LINE
    cmp CURRENT_LINE
    bne _pl_check_next
    lda TARGET_LINE+1
    cmp CURRENT_LINE+1
    beq _pl_do_print ; Equal
    
_pl_check_next:
    ; Skip this line
    ldy #0
_pl_skip_scan:
    lda (PTR_L),y
    beq _pl_next_line ; Found null
    iny
    bne _pl_skip_scan
    
_pl_do_print:
    lda CURRENT_LINE
    ldx CURRENT_LINE+1
    jsr PRDEC16
    lda #' '+$80
    jsr COUT
    
    ldy #0
print_char_loop:
    lda (PTR_L), Y
    beq end_of_line
    jsr COUT
    iny
    bne print_char_loop
end_of_line:
    jsr CROUT
    
_pl_next_line:
    ; Advance pointer to next line (Y+1)
    tya
    clc
    adc #1
    adc PTR_L
    sta PTR_L
    lda PTR_H
    adc #0
    sta PTR_H
    
    inc CURRENT_LINE
    bne _pl_chk_bound
    inc CURRENT_LINE+1
    
_pl_chk_bound:
    ; Check if CURRENT_LINE > LINE_IDX
    ; If CURRENT_LINE <= LINE_IDX, continue
    
    ; Compare CURRENT_LINE vs LINE_IDX
    ; Compare CURRENT_LINE vs LINE_IDX
    lda LINE_IDX+1
    cmp CURRENT_LINE+1
    bcc print_done ; LINE_IDX < CURRENT_LINE (High byte)
    bne print_line_loop ; LINE_IDX > CURRENT_LINE (High byte)
    
    lda LINE_IDX
    cmp CURRENT_LINE
    bcc print_done ; LINE_IDX < CURRENT_LINE (Low byte)
    jmp print_line_loop ; Continue
    
print_done:
    jmp command_loop

do_append:
    ; Append lines to TEXT_PTR
append_loop:
    ; Check Max Lines
    lda LINE_IDX+1
    cmp #>MAX_LINES
    bcc 1f ; OK
    bne _da_lines_error_trampoline ; >
    lda LINE_IDX
    cmp #<MAX_LINES
    bcc 1f ; OK
    bcs _da_lines_error_trampoline ; >=
    
1:  ; Check Buffer Space (Simple check: is TEXT_PTR >= MEM_LIMIT?)
    lda TEXT_PTR_H
    cmp #>MEM_LIMIT
    bcc 2f ; OK
    bne _da_full_error_trampoline ; >
    lda TEXT_PTR_L
    cmp #<MEM_LIMIT
    bcs _da_full_error_trampoline ; >=
    
2:  ; Copy TEXT_PTR to PTR for get_line
    lda TEXT_PTR_L
    sta PTR_L
    lda TEXT_PTR_H
    sta PTR_H
    
    ; Use ':' prompt for append mode
    lda #':'+$80
    sta PROMPT_CHAR
    
    jsr get_line_monitor ; Reads into (PTR) via GETLN
    
    ; Check for period on empty line
    ldy #0
    lda (PTR_L), Y
    cmp #'.'+$80
    bne check_len
    
    ; Check if it's just "." (next char is 0)
    iny
    lda (PTR_L), Y
    beq stop_append ; Found "." on its own line
    
check_len:
    ; Find length of line to update TEXT_PTR
    ldy #0
find_null:
    lda (PTR_L), Y
    beq found_null
    iny
    bne find_null
    
found_null:
    ; Update TEXT_PTR = PTR + Y + 1
    tya
    clc
    adc #1
    adc TEXT_PTR_L
    sta TEXT_PTR_L
    lda TEXT_PTR_H
    adc #0
    sta TEXT_PTR_H
    
    inc LINE_IDX
    bne 1f
    inc LINE_IDX+1
1:  lda #1
    sta DIRTY_FLAG
    jmp append_loop

stop_append:
    jmp command_loop

_da_lines_error_trampoline:
    lda #<msg_too_many_lines
    ldx #>msg_too_many_lines
    jsr puts
    jsr CROUT
    jmp command_loop

_da_full_error_trampoline:
    lda #<msg_buffer_full
    ldx #>msg_buffer_full
    jsr puts
    jsr CROUT
    jmp command_loop

; TODO: Refactor argument parsing.
; Many commands (Edit, Delete, Insert) share identical "Parse Number" logic.
; Extract to `parse_arg_or_default`.

do_edit:
    ; 1. Parse argument
    jsr parse_arg
    bcc 1f
    jmp _de_no_arg
1:  lda PD_VAL
    sta TARGET_LINE
    lda PD_VAL+1
    sta TARGET_LINE+1
    
    ; Check if valid (1 <= TARGET <= LINE_IDX)
    lda TARGET_LINE
    ora TARGET_LINE+1
    beq _de_jmp_invalid ; 0 is invalid
    
    ; Compare TARGET_LINE vs LINE_IDX
    lda LINE_IDX+1
    cmp TARGET_LINE+1
    bcc _de_jmp_invalid ; LINE_IDX < TARGET (High)
    bne _de_valid_chk   ; LINE_IDX > TARGET (High) -> Valid
    
    lda LINE_IDX
    cmp TARGET_LINE
    bcc _de_jmp_invalid ; LINE_IDX < TARGET (Low)
    jmp _de_valid_chk

_de_jmp_invalid:
    jmp _de_invalid

_de_valid_chk:
    
    ; 2. Find line address
    lda TARGET_LINE
    jsr find_line_addr
    
    ; Copy PTR to EDIT_PTR
    lda PTR_L
    sta EDIT_PTR_L
    lda PTR_H
    sta EDIT_PTR_H
    
_de_found_line:
    ; 3. Print current line
    lda TARGET_LINE
    ldx TARGET_LINE+1
    jsr PRDEC16
    lda #':'+$80
    jsr COUT
    lda #' '+$80
    jsr COUT
    
    lda EDIT_PTR_L
    ldx EDIT_PTR_H
    jsr puts
    jsr CROUT
    
    ; 4. Prompt for new input
    lda #'?'+$80
    sta PROMPT_CHAR
    
    lda #<CMD_BUFFER
    sta PTR_L
    lda #>CMD_BUFFER
    sta PTR_H
    
    jsr get_line_monitor
    
    ; 5. Check for cancel "."
    ldy #0
    lda (PTR_L), y
    cmp #'.'+$80
    bne _de_process
    iny
    lda (PTR_L), y
    bne _de_process
    jmp _de_cancel
    
_de_process:
    ; 6. Calc Lengths
    ; Get OLD_LEN from EDIT_PTR
    ldy #0
    lda EDIT_PTR_L
    sta PTR_L
    lda EDIT_PTR_H
    sta PTR_H
_de_len_old:
    lda (PTR_L), y
    beq _de_got_old
    iny
    bne _de_len_old
_de_got_old:
    sty OLD_LEN_VAR
    
    ; Get NEW_LEN from CMD_BUFFER
    ldy #0
    lda #<CMD_BUFFER
    sta PTR_L
    lda #>CMD_BUFFER
    sta PTR_H
_de_len_new:
    lda (PTR_L), y
    beq _de_got_new
    iny
    bne _de_len_new
_de_got_new:
    sty NEW_LEN_VAR
    
    ; Compare
    lda NEW_LEN_VAR
    cmp OLD_LEN_VAR
    bne _de_not_equal
    jmp _de_copy ; Equal
_de_not_equal:
    
    bcs _de_expand_trampoline ; NEW >= OLD

    ; SHRINK: NEW < OLD
    ; Move [EDIT_PTR+OLD_LEN+1...TEXT_PTR] to [EDIT_PTR+NEW_LEN+1]
    
    ; Dest
    lda EDIT_PTR_L
    clc
    adc NEW_LEN_VAR
    adc #1
    sta SHIFT_DEST_L
    lda EDIT_PTR_H
    adc #0
    sta SHIFT_DEST_H
    
    ; Src
    lda EDIT_PTR_L
    clc
    adc OLD_LEN_VAR
    adc #1
    sta SHIFT_SRC_L
    lda EDIT_PTR_H
    adc #0
    sta SHIFT_SRC_H
    
    jsr shift_down
    jmp _de_copy

_de_expand_trampoline:
    jmp _de_expand
    
_de_expand:
    ; EXPAND: NEW > OLD
    ; Move [EDIT_PTR+OLD_LEN+1...TEXT_PTR] to [EDIT_PTR+NEW_LEN+1] (Backwards)
    
    ; Dest (Start of new block)
    lda EDIT_PTR_L
    clc
    adc NEW_LEN_VAR
    adc #1
    sta SHIFT_DEST_L
    lda EDIT_PTR_H
    adc #0
    sta SHIFT_DEST_H
    
    ; Src (Start of old block)
    lda EDIT_PTR_L
    clc
    adc OLD_LEN_VAR
    adc #1
    sta SHIFT_SRC_L
    lda EDIT_PTR_H
    adc #0
    sta SHIFT_SRC_H
    
    jsr shift_up
    bcc 1f
    jmp _de_full_error
1:
    
_de_copy:
    ; Copy CMD_BUFFER to EDIT_PTR
    ldy #0
_de_copy_loop:
    lda CMD_BUFFER, y
    sta (EDIT_PTR_L), y
    beq _de_done_copy ; Reached null
    iny
    bne _de_copy_loop
    
_de_done_copy:
    lda #1
    sta DIRTY_FLAG
    jmp command_loop

_de_full_error:
    lda #<msg_buffer_full
    ldx #>msg_buffer_full
    jsr puts
    jsr CROUT
    jmp command_loop
    lda #1
    sta DIRTY_FLAG
    jmp command_loop

_de_cancel:
    jmp command_loop
    
_dd_jmp_no_arg:
    jmp _dd_no_arg

do_delete:
    ; 1. Parse argument
    jsr parse_arg
    bcc 1f
    jmp _dd_no_arg
1:  lda PD_VAL
    sta TARGET_LINE
    lda PD_VAL+1
    sta TARGET_LINE+1
    
    ; Check if valid (1 <= TARGET <= LINE_IDX)
    lda TARGET_LINE
    ora TARGET_LINE+1
    beq _dd_invalid ; 0 is invalid
    
    ; Compare TARGET_LINE vs LINE_IDX
    lda LINE_IDX+1
    cmp TARGET_LINE+1
    bcc _dd_invalid ; LINE_IDX < TARGET (High)
    bne _dd_valid_chk ; LINE_IDX > TARGET (High)
    
    lda LINE_IDX
    cmp TARGET_LINE
    bcc _dd_invalid ; LINE_IDX < TARGET (Low)
    
_dd_valid_chk:
    ; 2. Find line address (store in SHIFT_DEST)
    lda TARGET_LINE
    jsr find_line_addr
    
    ; Copy PTR to SHIFT_DEST
    lda PTR_L
    sta SHIFT_DEST_L
    lda PTR_H
    sta SHIFT_DEST_H

_dd_found_line:
    ; SHIFT_DEST points to start of line to delete.
    ; We need to find the start of the next line (SHIFT_SRC).
    
    ; Find end of current line
    ldy #0
_dd_find_end:
    lda (SHIFT_DEST_L), y
    beq _dd_found_end
    iny
    bne _dd_find_end
    
_dd_found_end:
    ; SHIFT_SRC = SHIFT_DEST + Y + 1
    tya
    clc
    adc #1
    adc SHIFT_DEST_L
    sta SHIFT_SRC_L
    lda SHIFT_DEST_H
    adc #0
    sta SHIFT_SRC_H
    
    ; Check if we are deleting the last line
    lda TARGET_LINE
    cmp LINE_IDX
    bne _dd_not_last
    lda TARGET_LINE+1
    cmp LINE_IDX+1
    beq _dd_last_line
    
_dd_not_last:
    ; Not last line, shift everything down
    jsr shift_down
    
    ; dec 16-bit LINE_IDX
    lda LINE_IDX
    bne 1f
    dec LINE_IDX+1
1:  dec LINE_IDX
    
    lda #1
    sta DIRTY_FLAG
    jmp command_loop

_dd_last_line:
    ; Just update TEXT_PTR to SHIFT_DEST
    lda SHIFT_DEST_L
    sta TEXT_PTR_L
    lda SHIFT_DEST_H
    sta TEXT_PTR_H
    
    ; dec 16-bit LINE_IDX
    lda LINE_IDX
    bne 1f
    dec LINE_IDX+1
1:  dec LINE_IDX
    lda #1
    sta DIRTY_FLAG
    jmp command_loop

_dd_invalid:
_dd_no_arg:
    jsr PRERR
    jmp command_loop

do_insert:
    ; 1. Parsing similar to others
    jsr parse_arg
    bcc 1f
    jmp _di_no_arg
1:  sta TARGET_LINE
    jmp _di_check_range

_di_no_arg_trampoline:
    jmp _di_no_arg

_di_check_range:
    
    ; Check range
    lda TARGET_LINE
    bne _di_check_range_valid
    jmp _di_invalid

_di_check_range_valid:
    cmp LINE_IDX
    beq _di_find_start
    bcs _di_invalid_jmp ; > LINE_IDX
    jmp _di_find_start_entry

_di_invalid_jmp:
    jmp _di_invalid

_di_find_start:
_di_find_start_entry:
    ; 2. Find Address of desired line
    lda TARGET_LINE
    jsr find_line_addr
    
    ; Copy PTR to EDIT_PTR
    lda PTR_L
    sta EDIT_PTR_L
    lda PTR_H
    sta EDIT_PTR_H
    
    jmp _di_input_loop
    
_di_input_loop:
    ; Check Max Lines
    lda LINE_IDX+1
    cmp #>MAX_LINES
    bcc 1f ; OK
    bne _di_lines_error_trampoline ; >
    lda LINE_IDX
    cmp #<MAX_LINES
    bcc 1f ; OK
    bcs _di_lines_error_trampoline ; >=
    
1:
    ; Prompt
    lda #':'+$80
    sta PROMPT_CHAR
    
    lda #<CMD_BUFFER
    sta PTR_L
    lda #>CMD_BUFFER
    sta PTR_H
    
    jsr get_line_monitor
    
    ; Check for cancel "."
    ldy #0
    lda (PTR_L), y
    cmp #'.'+$80
    bne _di_do_insert
    iny
    lda (PTR_L), y
    bne _di_do_insert
    jmp command_loop ; Cancelled
    
_di_do_insert:
    ; Calc length of new string
    ldy #0
_di_len:
    lda (PTR_L), y
    beq _di_got_len
    iny
    bne _di_len
_di_got_len:
    ; Y = length. Need Y+1 bytes (null terminator)
    sty NEW_LEN_VAR
    
    ; Setup shift_up
    ; SHIFT_SRC = EDIT_PTR (Start of block to move)
    lda EDIT_PTR_L
    sta SHIFT_SRC_L
    lda EDIT_PTR_H
    sta SHIFT_SRC_H
    
    ; SHIFT_DEST = EDIT_PTR + NEW_LEN + 1
    tya
    clc
    adc #1
    adc EDIT_PTR_L
    sta SHIFT_DEST_L
    lda EDIT_PTR_H
    adc #0
    sta SHIFT_DEST_H
    
    jsr shift_up ; Moves rest of buffer up. Updates TEXT_PTR.
    bcc 1f
    jmp _di_full_error
1:
    
    ; Copy CMD_BUFFER to memory at EDIT_PTR
    ldy #0

_di_copy:
    lda CMD_BUFFER, y
    sta (EDIT_PTR_L), y
    beq _di_done_copy
    iny
    bne _di_copy
    
_di_done_copy:
    ; Update EDIT_PTR to point to start of next line (which is SHIFT_DEST from before)
    ; Since shift_up destroys SHIFT_DEST, recompute:
    lda NEW_LEN_VAR
    clc
    adc #1
    adc EDIT_PTR_L
    sta EDIT_PTR_L
    lda EDIT_PTR_H
    adc #0
    sta EDIT_PTR_H
    
    inc LINE_IDX
    bne 1f
    inc LINE_IDX+1
1:  lda #1
    sta DIRTY_FLAG
    jmp _di_input_loop

_di_lines_error_trampoline:
    jmp _di_lines_error

_di_reloop:
    jmp command_loop

_di_invalid:
_di_no_arg:
    jsr PRERR
    jmp command_loop

_di_full_error:
    lda #<msg_buffer_full
    ldx #>msg_buffer_full
    jsr puts
    jsr CROUT
    jmp _di_reloop

_di_lines_error:
    lda #<msg_too_many_lines
    ldx #>msg_too_many_lines
    jsr puts
    jsr CROUT
    jmp _di_reloop

_de_invalid:
_de_no_arg:
    jsr PRERR
    jmp command_loop

shift_down:
    ; Shift content DOWN (to lower addresses)
    ; Used by delete operations.
    ; Reads from SHIFT_SRC, Writes to SHIFT_DEST
    ; Refactored to use generic memmove.
    
    ; 1. Setup MEM_END = TEXT_PTR
    lda TEXT_PTR_L
    sta MEM_END_L
    lda TEXT_PTR_H
    sta MEM_END_H
    
    ; 2. Calculate New End
    ; New End = MEM_DEST + (MEM_END - MEM_SRC)
    
    lda MEM_END_L
    sec
    sbc SHIFT_SRC_L
    sta SHIFT_DIFF_L
    lda MEM_END_H
    sbc SHIFT_SRC_H
    sta TEMP_PTR_H
    
    ; New End = MEM_DEST + Len
    lda SHIFT_DEST_L
    clc
    adc SHIFT_DIFF_L
    sta TEMP_PTR_L
    lda SHIFT_DEST_H
    adc TEMP_PTR_H
    sta TEMP_PTR_H
    
    ; 3. Call memmove
    ; MEM_SRC = SHIFT_SRC
    ; MEM_DEST = SHIFT_DEST
    ; MEM_END = TEXT_PTR
    ; These are already set up by the calling routine (delete)
    jsr memmove
    
    ; 4. Update TEXT_PTR
    lda TEMP_PTR_L
    sta TEXT_PTR_L
    lda TEMP_PTR_H
    sta TEXT_PTR_H
    
    rts

shift_up:
    ; Expand buffer.
    ; Copy backwards.
    ; 1. Check if we have space
    ; New End = TEXT_PTR + (SHIFT_DEST - SHIFT_SRC)
    ; But wait, SHIFT_DEST - SHIFT_SRC is the *gap size*.
    ; Yes. 
    ; Size of gap = SHIFT_DEST - SHIFT_SRC
    
    ; Calculate Gap Size
    lda SHIFT_DEST_L
    sec
    sbc SHIFT_SRC_L
    sta TEMP_PTR_L ; Gap L
    lda SHIFT_DEST_H
    sbc SHIFT_SRC_H
    sta TEMP_PTR_H ; Gap H
    
    ; Add Gap to TEXT_PTR to get New End
    lda TEXT_PTR_L
    clc
    adc TEMP_PTR_L
    sta TEMP_PTR_L
    lda TEXT_PTR_H
    adc TEMP_PTR_H
    sta TEMP_PTR_H
    
    ; Check against MEM_LIMIT
    lda TEMP_PTR_H
    cmp #>MEM_LIMIT
    bcc 2f ; OK if < High Byte
    bne 1f ; Fail if > High Byte
    ; If equal, check Low Byte
    lda TEMP_PTR_L
    cmp #<MEM_LIMIT
    bcc 2f ; OK if < Low Byte
    
1:  ; Error: Buffer Full
    sec ; Set Carry = Error
    rts
    
2:  ; OK to proceed
    
    ; 1. Setup MEM_END = TEXT_PTR
    lda TEXT_PTR_L
    sta MEM_END_L
    lda TEXT_PTR_H
    sta MEM_END_H
    
    ; 2. Calculate New End (Return value logic moved here)
    ; New End = MEM_DEST + (MEM_END - MEM_SRC)
    ; We need this to update TEXT_PTR after the move.
    
    lda MEM_END_L
    sec
    sbc MEM_SRC_L
    sta SHIFT_DIFF_L ; Save Len L for calculation
    lda MEM_END_H
    sbc MEM_SRC_H
    sta TEMP_PTR_H ; Save Len H for calculation (reuse TEMP_PTR_H)
    
    ; New End = MEM_DEST + Len
    lda MEM_DEST_L
    clc
    adc SHIFT_DIFF_L
    sta TEMP_PTR_L
    lda MEM_DEST_H
    adc TEMP_PTR_H
    sta TEMP_PTR_H
    
    ; 3. Call memmove (MEM_SRC, MEM_DEST matched by aliases)
    jsr memmove
    
    ; 4. Update Global TEXT_PTR
    lda TEMP_PTR_L
    sta TEXT_PTR_L
    lda TEMP_PTR_H
    sta TEXT_PTR_H
    
    rts

; Input routine using Monitor GETLN
; Reads line into Monitor buffer ($0200) then copies to (PTR_L)
; Null-terminates with 0.
get_line_monitor:
    jsr GETLN      ; Monitor routine: Prints prompt, gets line to $0200
                   ; Returns X = length (index of CR)
    
    ; Copy from $0200 to (PTR)
    ldy #0
copy_loop:
    lda $0200, Y   ; Get char from input buffer
    cmp #CR        ; Check for CR (end of line)
    beq copy_done
    sta (PTR_L), Y ; Store in our buffer
    iny
    bne copy_loop  ; Limit to 256 chars (unlikely with GETLN)
    
copy_done:
    lda #0         ; Null terminate string
    sta (PTR_L), Y
    rts

puts:
    sta PTR_L
    stx PTR_H
    ldy #0
puts_loop:
    lda (PTR_L),y
    beq puts_done
    ora #$80
    jsr COUT
    iny
    bne puts_loop
puts_done:
    rts

; Print string in A (Low), X (High) using Inverse Video
; Preserves A and X when calling SETINV, but destroys them after puts returns.
puts_inv:
    pha             ; Save A (PTR_L)
    txa
    pha             ; Save X (PTR_H)
    
    jsr SETINV      ; Set Inverse Video Flag ($3F)
    
    pla
    tax             ; Restore X
    pla             ; Restore A
    
    jsr puts        ; Print the string
    
    jsr SETNORM     ; Restore Normal Video Flag ($FF)
    rts

; Print A as decimal number (0-255) to COUT
PRDEC:
    stx PRDEC_SAVEX
    sta PRDEC_TMP
    
    lda #0
    sta PRDEC_FLAG
    
    ldx #0      ; Hundreds count
    lda PRDEC_TMP
_prdec_100_loop:
    cmp #100
    bcc _prdec_100_done
    sbc #100
    inx
    bne _prdec_100_loop
_prdec_100_done:
    sta PRDEC_TMP ; Save remainder
    cpx #0
    beq _prdec_chk10
    ; Print hundreds
    txa
    ora #$B0
    jsr COUT
    inc PRDEC_FLAG
    
_prdec_chk10:
    ldx #0
    lda PRDEC_TMP
_prdec_10_loop:
    cmp #10
    bcc _prdec_10_done
    sbc #10
    inx
    bne _prdec_10_loop
_prdec_10_done:
    sta PRDEC_TMP ; Remainder is ones
    cpx #0
    bne _prdec_do_10
    lda PRDEC_FLAG
    beq _prdec_do_ones ; Skip 0 tens if no hundreds
_prdec_do_10:
    txa
    ora #$B0
    jsr COUT
    
_prdec_do_ones:
    lda PRDEC_TMP
    ora #$B0
    jsr COUT
    
    ldx PRDEC_SAVEX
    rts

; Parse decimal number starting at (PTR_L), Y
; Returns value in PD_VAL (16-bit). Updates Y.
; A is clobbered.
PARSE_DECIMAL:
    lda #0
    sta PD_VAL
    sta PD_VAL+1
_pd_loop:
    lda (PTR_L),y
    cmp #'0'+$80
    bcs 1f
    jmp _pd_done
1:  cmp #'9'+$80+1
    bcc 2f
    jmp _pd_done
2:
    
    ; Convert to int
    and #$0F
    pha ; Push digit
    
    ; Val = Val * 10
    ; Val = (Val * 2) * 5? No, Val*10 = Val*8 + Val*2
    
    ; PD_TEMP = Val * 2
    lda PD_VAL
    asl a
    sta PD_TEMP
    lda PD_VAL+1
    rol a
    sta PD_TEMP+1 ; PD_TEMP = Val * 2
    
    ; Val = Val * 4 (Accumulator has Val*2)
    asl PD_TEMP
    rol PD_TEMP+1
    
    ; Val = Val * 8
    asl PD_TEMP
    rol PD_TEMP+1 ; PD_TEMP = Val * 8
    
    ; Val = (Val * 8) + (Val * 2)
    ; We need Val*2 again. Let's restart logic to be clearer.
    ; Val * 10 = (Val << 3) + (Val << 1)
    
    ; Shift Left 1 (Val * 2)
    lda PD_VAL
    asl a
    sta PD_TEMP   ; PD_TEMP = Val * 2
    lda PD_VAL+1
    rol a
    sta PD_TEMP+1
    
    ; Shift Left 2 more times (Val * 8)
    asl a         ; Val * 4
    rol PD_TEMP+1 ; Incorrect usage of rol? No, A has High byte
    ; Let's operate on memory for simplicity or registers.
    
    ; PD_VAL * 2 -> stored in PD_TEMP
    lda PD_VAL
    asl a
    sta PD_TEMP
    lda PD_VAL+1
    rol a
    sta PD_TEMP+1
    
    ; PD_VAL * 4
    lda PD_TEMP
    asl a
    sta PD_TEMP2
    lda PD_TEMP+1
    rol a
    sta PD_TEMP2+1
    
    ; PD_VAL * 8
    lda PD_TEMP2
    asl a
    sta PD_TEMP2
    lda PD_TEMP2+1
    rol a
    sta PD_TEMP2+1
    
    ; Val * 10 = (Val * 8) + (Val * 2)
    lda PD_TEMP2   ; Val * 8
    clc
    adc PD_TEMP    ; Val * 2
    sta PD_VAL
    lda PD_TEMP2+1
    adc PD_TEMP+1
    sta PD_VAL+1
    
    pla ; Pop digit
    clc
    adc PD_VAL
    sta PD_VAL
    lda PD_VAL+1
    adc #0
    sta PD_VAL+1
    
    iny
    beq 1f
    jmp _pd_loop
1:
_pd_done:
    lda PD_VAL ; Return Low byte in A for compatibility (if needed, but consumers should check PD_VAL)
    rts

; Skip spaces in buffer pointed to by PTR
; Inputs: PTR, Y
; Outputs: Y points to first non-space or null
;          A contains that char
;          Z flag set if null (end of line)
skip_spaces:
    lda (PTR_L), y
    beq _ss_done
    cmp #' '+$80
    bne _ss_done
    iny
    bne skip_spaces
_ss_done:
    rts

; Parse optional decimal argument
; Inputs: PTR = Command Buffer
;         Y = Current Index (pointing to command char)
; Outputs: A = Parsed Value
;          Y = Updated Index
;          C = Clear if valid argument found
;          C = Set if no argument found or invalid
parse_arg:
    iny ; Skip command char or previous char
    jsr skip_spaces
    
    ; Check if we have a char
    cmp #0
    beq _pa_return_no_arg ; Z=1
    
    ; Check if digit
    cmp #'0'+$80
    bcc _pa_return_invalid ; Z=0
    cmp #'9'+$80+1
    bcs _pa_return_invalid ; Z=0
    
    jsr PARSE_DECIMAL
    clc ; Success (C=0)
    rts

_pa_return_no_arg:
    sec ; C=1
    lda #0 ; Z=1
    rts

_pa_return_invalid:
    sec ; C=1
    lda #$FF ; Z=0
    rts

; Old labels for compatibility if any (unlikely used directly)
_pa_no_arg:
    sec
    rts

do_find:
    iny
    jsr skip_spaces
    bne _df_got_arg ; Z=0 means A!=0 (found arg)
    ; Z=1 means null (no arg)
    jsr PRERR
    jmp command_loop

_df_chk_space:

_df_got_arg:
    ldx #0
_df_copy_pat:
    lda (PTR_L), y
    beq _df_end_pat
    sta $2E00, x
    iny
    inx
    bne _df_copy_pat
_df_end_pat:
    lda #0
    sta $2E00, x
    cpx #0
    bne _df_init
    jsr PRERR
    jmp command_loop

_df_init:

    lda #<BUFFER_START
    sta FIND_PTR_CURR
    lda #>BUFFER_START
    sta FIND_PTR_CURR+1
    
    lda #1
    sta FIND_LINE_NUM
    lda #0
    sta FIND_LINE_NUM+1
    
    lda #0
    sta FIND_PTR_PREV1
    sta FIND_PTR_PREV1+1
    sta FIND_PTR_PREV2
    sta FIND_PTR_PREV2+1
    
_df_loop:
    ; Check if FIND_LINE_NUM <= LINE_IDX
    lda LINE_IDX+1
    cmp FIND_LINE_NUM+1
    bcc _df_end_loop ; LINE_IDX < FIND (High) -> Stop
    bne _df_check    ; LINE_IDX > FIND (High) -> Create
    
    lda LINE_IDX
    cmp FIND_LINE_NUM
    bcc _df_end_loop ; LINE_IDX < FIND (Low) -> Stop
    jmp _df_check
    
_df_end_loop:
    jmp command_loop
    
_df_check:
    lda FIND_PTR_CURR
    sta PTR_L
    lda FIND_PTR_CURR+1
    sta PTR_H
    
    lda #<$2E00
    sta EDIT_PTR_L
    lda #>$2E00
    sta EDIT_PTR_H
    
    jsr glob_match
    bcc _df_next
    
    jsr print_context
    
    lda #'N'+$80
    sta PROMPT_CHAR
    
    lda #<msg_next
    ldx #>msg_next
    jsr puts
    
    lda #<CMD_BUFFER
    sta PTR_L
    lda #>CMD_BUFFER
    sta PTR_H
    jsr get_line_monitor
    
    ldy #0
    lda (PTR_L), y
    cmp #'C'+$80
    beq _df_finish_jmp
    cmp #'c'+$80
    beq _df_finish_jmp
    cmp #'.'+$80
    beq _df_finish_jmp
    
_df_next:
    lda FIND_PTR_PREV1
    sta FIND_PTR_PREV2
    lda FIND_PTR_PREV1+1
    sta FIND_PTR_PREV2+1
    
    lda FIND_PTR_CURR
    sta FIND_PTR_PREV1
    lda FIND_PTR_CURR+1
    sta FIND_PTR_PREV1+1
    
    ldy #0
    lda FIND_PTR_CURR
    sta PTR_L
    lda FIND_PTR_CURR+1
    sta PTR_H
    
_df_scan_null:
    lda (PTR_L), y
    beq _df_found_null
    iny
    bne _df_scan_null
    
_df_found_null:
    tya
    clc
    adc #1
    adc PTR_L
    sta FIND_PTR_CURR
    lda PTR_H
    adc #0
    sta FIND_PTR_CURR+1
    
    inc FIND_LINE_NUM
    bne 1f
    inc FIND_LINE_NUM+1
1:  jmp _df_loop

_df_finish_jmp:
    jmp command_loop

_df_no_arg:
    jsr PRERR
    jmp command_loop

glob_match:
    ldy #0
    lda (EDIT_PTR_L), y
    bne _gm_check_stars
    lda (PTR_L), y
    beq _gm_match_ok
    clc
    rts
_gm_match_ok:
    sec
    rts

_gm_check_stars:
    cmp #'*'+$80
    beq _gm_is_star
    jmp _gm_check_q
    
_gm_is_star:
    
    iny
    lda (EDIT_PTR_L), y
    bne _gm_star_recurse
    sec
    rts

_gm_star_recurse:
    lda PTR_L
    pha
    lda PTR_H
    pha
    lda EDIT_PTR_L
    pha
    lda EDIT_PTR_H
    pha
    
    inc EDIT_PTR_L
    bne 1f
    inc EDIT_PTR_H
1:

_gm_star_loop:
    jsr glob_match
    bcs _gm_star_found
    
    ldy #0
    lda (PTR_L), y
    beq _gm_star_fail
    
    inc PTR_L
    bne 1f
    inc PTR_H
1:
    jmp _gm_star_loop

_gm_star_found:
    pla
    sta EDIT_PTR_H
    pla
    sta EDIT_PTR_L
    pla
    sta PTR_H
    pla
    sta PTR_L
    sec
    rts

_gm_star_fail:
    pla
    sta EDIT_PTR_H
    pla
    sta EDIT_PTR_L
    pla
    sta PTR_H
    pla
    sta PTR_L
    clc
    rts

_gm_check_q:
    cmp #'?'+$80
    beq _gm_char_match
    
    cmp (PTR_L), y
    bne _gm_fail
    
_gm_char_match:
    lda (PTR_L), y
    beq _gm_fail
    
    inc PTR_L
    bne 1f
    inc PTR_H
1:
    inc EDIT_PTR_L
    bne 1f
    inc EDIT_PTR_H
1:
    jmp glob_match

_gm_fail:
    clc
    rts

print_context:
    lda #'-'+$80
    jsr COUT
    jsr COUT
    jsr CROUT

    lda FIND_PTR_PREV2+1
    beq _pc_prev1
    
    lda FIND_PTR_PREV2
    sta PTR_L
    lda FIND_PTR_PREV2+1
    sta PTR_H
    
    ; Calc FIND_LINE_NUM - 2
    lda FIND_LINE_NUM
    sec
    sbc #2
    ldx FIND_LINE_NUM+1
    bcs 1f
    dex
1:  jsr print_line_at_ptr
    
_pc_prev1:
    lda FIND_PTR_PREV1+1
    beq _pc_curr
    
    lda FIND_PTR_PREV1
    sta PTR_L
    lda FIND_PTR_PREV1+1
    sta PTR_H
    
    ; Calc FIND_LINE_NUM - 1
    lda FIND_LINE_NUM
    sec
    sbc #1
    ldx FIND_LINE_NUM+1
    bcs 1f
    dex
1:  jsr print_line_at_ptr

_pc_curr:
    lda FIND_PTR_CURR
    sta PTR_L
    sta TEMP_PTR_L
    lda FIND_PTR_CURR+1
    sta PTR_H
    sta TEMP_PTR_H

    lda FIND_LINE_NUM
    ldx FIND_LINE_NUM+1
    jsr print_line_at_ptr
    
    lda FIND_LINE_NUM
    jsr print_line_highlighted
    

    
    jsr _pc_advance_temp
    beq _pc_done
    
    lda TEMP_PTR_L
    sta PTR_L
    lda TEMP_PTR_H
    sta PTR_H
    lda FIND_LINE_NUM
    clc
    adc #1
    cmp LINE_IDX
    beq _pc_print_next1
    bcs _pc_done
_pc_print_next1:
    jsr print_line_at_ptr
    
    jsr _pc_advance_temp
    beq _pc_done
    
    lda TEMP_PTR_L
    sta PTR_L
    lda TEMP_PTR_H
    sta PTR_H
    lda FIND_LINE_NUM
    clc
    adc #2
    cmp LINE_IDX
    beq _pc_print_next2
    bcs _pc_done
_pc_print_next2:
    jsr print_line_at_ptr

_pc_done:
    rts

_pc_advance_temp:
    lda TEMP_PTR_L
    sta EDIT_PTR_L
    lda TEMP_PTR_H
    sta EDIT_PTR_H
    
    ldy #0
_pc_scan:
    lda (EDIT_PTR_L), y
    beq _pc_found
    iny
    bne _pc_scan
_pc_found:
    tya
    clc
    adc #1
    adc TEMP_PTR_L
    sta TEMP_PTR_L
    lda TEMP_PTR_H
    adc #0
    sta TEMP_PTR_H
    
    lda TEMP_PTR_L
    cmp TEXT_PTR_L
    bne 1f
    lda TEMP_PTR_H
    cmp TEXT_PTR_H
    beq _pc_at_end
1:  lda #1
    rts
_pc_at_end:
    lda #0
    rts

print_line_at_ptr:
    ; Print Line Number (A, X) - but wait, where is the line number coming from?
    ; It seems FIND_LINE_NUM is passed implicitly or loaded?
    ; Original code: lda FIND_LINE_NUM; jsr print_line_at_ptr? No.
    ; print_context calls it.
    ; Wait, print_context:
    ; lda FIND_LINE_NUM
    ; sec
    ; sbc #2
    ; jsr print_line_at_ptr
    
    ; So print_line_at_ptr expects Line Number in A?
    ; If 16-bit, it needs A and X.
    
    ; let's update print_line_at_ptr to assume A(Low), X(High)
    jsr PRDEC16
    lda #':'+$80
    jsr COUT
    lda #' '+$80
    jsr COUT
    
    ldy #0
_pl_loop:
    lda (PTR_L),y
    beq _pl_done
    jsr COUT
    iny
    bne _pl_loop
_pl_done:
    jsr CROUT
    rts

print_line_highlighted:
    jsr PRDEC
    lda #':'+$80
    jsr COUT
    lda #' '+$80
    jsr COUT
    
    ldy #0
_plh_loop:
    lda (PTR_L),y
    beq _plh_done
    
    ; Convert to Inverse
    ; Clear bit 7 (Normal -> 0xxxxxxx)
    ; Clear bit 6 (Normal -> 00xxxxxx)
    ; Standard Inverse is $00-$3F
    cmp #'a'+$80
    bcc _plh_inv
    cmp #'z'+$80+1
    bcs _plh_inv
    and #$DF ; Convert low to up
_plh_inv:
    and #$3F
    jsr COUT
    iny
    bne _plh_loop
_plh_done:
    jsr CROUT
    rts

do_help:
    lda #<msg_help_0
    ldx #>msg_help_0
    jsr puts
    lda #<msg_help_1
    ldx #>msg_help_1
    jsr puts
    lda #<msg_help_2
    ldx #>msg_help_2
    jsr puts
    lda #<msg_help_3
    ldx #>msg_help_3
    jsr puts
    jmp command_loop

do_buffer_status:
    ; 1. Print Dirty Status
    lda DIRTY_FLAG
    beq _dbs_clean
    lda #<msg_dirty
    ldx #>msg_dirty
    jmp _dbs_print_dirty
_dbs_clean:
    lda #<msg_clean
    ldx #>msg_clean
_dbs_print_dirty:
    jsr puts_inv
    
    ; 2. Print Lines
    lda LINE_IDX
    ldx LINE_IDX+1
    jsr PRDEC16
    lda #<msg_slash
    ldx #>msg_slash
    jsr puts
    lda #<MAX_LINES
    ldx #>MAX_LINES
    jsr PRDEC16
    
    lda #<msg_lines_suffix
    ldx #>msg_lines_suffix
    jsr puts
    
    ; 3. Print Bytes
    ; Calc Bytes Used (TEXT_PTR - BUFFER_START)
    lda TEXT_PTR_L
    sec
    sbc #<BUFFER_START
    sta BS_USED_L
    lda TEXT_PTR_H
    sbc #>BUFFER_START
    sta BS_USED_H
    
    lda BS_USED_L
    ldx BS_USED_H
    jsr PRDEC16
    
    lda #<msg_slash
    ldx #>msg_slash
    jsr puts
    
    lda #<MAX_BUFFER_SIZE
    ldx #>MAX_BUFFER_SIZE
    jsr PRDEC16
    
    lda #<msg_bytes_suffix
    ldx #>msg_bytes_suffix
    jsr puts
    
    jsr CROUT
    
    jmp command_loop

msg_next:
    .byte "NEXT/CANCEL? ", 0

msg_welcome:
    .byte "MINIED 1.1", $0d, 0

msg_buffer_full:
    .byte "Error: Buffer Full", $0d, 0
msg_too_many_lines:
    .byte "Error: Too Many Lines", $0d, 0
    


; Print 16-bit number in X (High), A (Low)
PRDEC16:
    sta PRDEC16_VAL_L
    stx PRDEC16_VAL_H
    
    ; Simple repeated subtraction for 10000, 1000, 100, 10
    ; Or just a basic conversion loop.
    ; Since we don't have a divide, subtraction is easiest.
    
    lda #0
    sta PRDEC_FLAG ; Use to suppress leading zeros
    
    ; 10000s
    ldy #0
_pd16_10000:
    lda PRDEC16_VAL_L
    sec
    sbc #<10000
    tax
    lda PRDEC16_VAL_H
    sbc #>10000
    bcc _pd16_10000_done
    sta PRDEC16_VAL_H
    stx PRDEC16_VAL_L
    iny
    jmp _pd16_10000
_pd16_10000_done:
    tya
    beq _pd16_chk_1000
    ora #$B0
    jsr COUT
    inc PRDEC_FLAG
    
_pd16_chk_1000:
    ; 1000s
    ldy #0
_pd16_1000:
    lda PRDEC16_VAL_L
    sec
    sbc #<1000
    tax
    lda PRDEC16_VAL_H
    sbc #>1000
    bcc _pd16_1000_done
    sta PRDEC16_VAL_H
    stx PRDEC16_VAL_L
    iny
    jmp _pd16_1000
_pd16_1000_done:
    tya
    bne _pd16_print_1000
    lda PRDEC_FLAG
    beq _pd16_chk_100
_pd16_print_1000:
    tya
    ora #$B0
    jsr COUT
    inc PRDEC_FLAG

_pd16_chk_100:
    ; 100s
    ldy #0
_pd16_100:
    lda PRDEC16_VAL_L
    sec
    sbc #100
    tax
    lda PRDEC16_VAL_H
    sbc #0
    bcc _pd16_100_done
    sta PRDEC16_VAL_H
    stx PRDEC16_VAL_L
    iny
    jmp _pd16_100
_pd16_100_done:
    tya
    bne _pd16_print_100
    lda PRDEC_FLAG
    beq _pd16_chk_10
_pd16_print_100:
    tya
    ora #$B0
    jsr COUT
    inc PRDEC_FLAG

_pd16_chk_10:
    ; 10s
    ldy #0
_pd16_10:
    lda PRDEC16_VAL_L
    sec
    sbc #10
    tax
    lda PRDEC16_VAL_H
    sbc #0 ; High byte of 10 is 0
    bcc _pd16_10_done
    sta PRDEC16_VAL_H
    stx PRDEC16_VAL_L
    iny
    jmp _pd16_10
_pd16_10_done:
    tya
    bne _pd16_print_10
    lda PRDEC_FLAG
    beq _pd16_chk_1
_pd16_print_10:
    tya
    ora #$B0
    jsr COUT

_pd16_chk_1:
    ; Ones
    lda PRDEC16_VAL_L
    ora #$B0
    jsr COUT
    
    rts

PD_VAL: .word 0
PD_TEMP: .word 0
PD_TEMP2: .word 0
    
OLD_LEN_VAR: .byte 0
NEW_LEN_VAR: .byte 0
SHIFT_BLOCK_START_L: .byte 0
SHIFT_BLOCK_START_H: .byte 0
TEMP_PTR_L: .byte 0
TEMP_PTR_H: .byte 0
SHIFT_DIFF_L: .byte 0
FIND_PTR_CURR: .word 0
FIND_PTR_PREV1: .word 0
FIND_PTR_PREV2: .word 0
FIND_LINE_NUM: .word 0 ; 16-bit
DIRTY_FLAG: .byte 0
BS_USED_L: .byte 0
BS_USED_H: .byte 0
BS_REM_L:  .byte 0
BS_REM_H:  .byte 0
PRDEC16_VAL_L: .byte 0
PRDEC16_VAL_H: .byte 0

msg_dirty: .byte "UNSAVED ", 0
msg_clean: .byte "NEW ", 0
msg_confirm_new: .byte "CLEAR BUFFER (Y/N)?", 0
msg_cleared: .byte "BUFFER CLEARED", 0
msg_slash: .byte "/", 0
msg_lines_suffix: .byte "L ", 0
msg_bytes_suffix: .byte "B", 0

.ifdef DEBUG
msg_lorem: .byte "LOREM IPSUM LINE", 0
msg_fill_done: .byte "FILL DONE", 0
.endif

; Find Address of Line A (1-based)
; Inputs: A = Line Number
.ifdef DEBUG
do_fill:
    ; Fill buffer with N lines of dummy text.
    ; Syntax: * N
    
    jsr parse_arg
    bcc _dfill_has_arg
    ; If no arg, default to 10
    lda #10
    sta PD_VAL
    lda #0
    sta PD_VAL+1
    
_dfill_has_arg:
    ; PD_VAL has count.
    ; Store in TARGET_LINE as loop counter
    lda PD_VAL
    sta TARGET_LINE
    lda PD_VAL+1
    sta TARGET_LINE+1
    
_dfill_loop:
    ; Check if counter is 0
    lda TARGET_LINE
    ora TARGET_LINE+1
    beq _dfill_done
    
    ; 1. Check Max Lines
    lda LINE_IDX+1
    cmp #>MAX_LINES
    bcc 1f
    bne _dfill_err_lines
    lda LINE_IDX
    cmp #<MAX_LINES
    bcc 1f
    bcs _dfill_err_lines
1:
    ; 2. Check Buffer Space
    ; Assume dummy line length = ~16 bytes.
    ; Check if TEXT_PTR + 17 < MEM_LIMIT
    lda TEXT_PTR_L
    clc
    adc #17
    sta EDIT_PTR_L ; Use EDIT_PTR as temp
    lda TEXT_PTR_H
    adc #0
    sta EDIT_PTR_H
    
    lda EDIT_PTR_H
    cmp #>MEM_LIMIT
    bcc 2f
    bne _dfill_err_buf
    lda EDIT_PTR_L
    cmp #<MEM_LIMIT
    bcs _dfill_err_buf
2:
    
    ; 3. Append Line
    ; Copy "LOREM IPSUM LINE" + null
    ldy #0
    ldx #0
_dfill_copy:
    lda msg_lorem,x
    beq _dfill_term
    sta (TEXT_PTR_L),y
    inx
    iny
    bne _dfill_copy
_dfill_term:
    ; Null terminate
    lda #0
    sta (TEXT_PTR_L),y
    
    ; Update TEXT_PTR
    tya
    clc
    adc #1
    adc TEXT_PTR_L
    sta TEXT_PTR_L
    lda TEXT_PTR_H
    adc #0
    sta TEXT_PTR_H
    
    ; Update Counters
    inc LINE_IDX
    bne 3f
    inc LINE_IDX+1
3:
    ; Decrement Loop Counter (TARGET_LINE)
    lda TARGET_LINE
    bne 4f
    dec TARGET_LINE+1
4:  dec TARGET_LINE
    
    jmp _dfill_loop

_dfill_done:
    lda #1
    sta DIRTY_FLAG
    lda #<msg_fill_done
    ldx #>msg_fill_done
    jsr puts
    jsr CROUT
    jmp command_loop

_dfill_err_lines:
    jsr PRERR
    lda #<msg_too_many_lines
    ldx #>msg_too_many_lines
    jsr puts
    jsr CROUT
    jmp command_loop

_dfill_err_buf:
    jsr PRERR
    lda #<msg_buffer_full
    ldx #>msg_buffer_full
    jsr puts
    jsr CROUT
    jmp command_loop

.endif

; Outputs: PTR = Address of start of line
; Destroys: A, X, Y
find_line_addr:
    pha ; Save target line
    
    lda #<BUFFER_START
    sta PTR_L
    lda #>BUFFER_START
    sta PTR_H
    
    pla
    tax
    dex         ; 0-indexed for loop (Line 1 = 0 offsets)
    beq _fla_done
    
_fla_loop:
    ldy #0
_fla_scan:
    lda (PTR_L), y
    beq _fla_next
    iny
    bne _fla_scan
_fla_next:
    ; Point to next line (PTR + Y + 1)
    tya
    clc
    adc #1
    adc PTR_L
    sta PTR_L
    lda PTR_H
    adc #0
    sta PTR_H
    
    dex
    bne _fla_loop
    
_fla_done:
    rts

; ==============================================================================
; Generic Memory Move
; Moves block [MEM_SRC, MEM_END) to MEM_DEST.
; Handles overlap correctly (copy forward or backward).
; Inputs: MEM_SRC, MEM_END, MEM_DEST (ZP Pointers)
; Outputs: None (Memory moved)
; Destroys: A, X, Y, MEM_SRC, MEM_DEST, MEM_END
; ==============================================================================
memmove:
    ; Compare Dest vs Src
    lda MEM_DEST_H
    cmp MEM_SRC_H
    bne _mm_check_dir
    lda MEM_DEST_L
    cmp MEM_SRC_L
    bne _mm_check_dir
    rts ; Dest == Src, nothing to do

_mm_check_dir:
    ; If Dest < Src, Copy Forward
    ; If Dest > Src, Copy Backward
    
    lda MEM_DEST_H
    cmp MEM_SRC_H
    bcc _mm_copy_fwd
    bne _mm_copy_bwd ; Dest > Src
    
    ; High bytes equal, check low
    lda MEM_DEST_L
    cmp MEM_SRC_L
    bcc _mm_copy_fwd
    
_mm_copy_bwd:
    ; --------------------------------------------------------------------------
    ; BACKWARD COPY (Dest > Src)
    ; Start at End-1, Copy to (Dest + Len) - 1
    ; Actually, simpler:
    ; Read from MEM_END-1 down to MEM_SRC
    ; Write to (MEM_DEST + Len) - 1 down to MEM_DEST
    
    ; Just use pointers and predecrement.
    ; But we need to know where to start writing.
    ; WriteEnd = MEM_DEST + (MEM_END - MEM_SRC)
    
    ; Calc Length into X/Y (Low/High)
    lda MEM_END_L
    sec
    sbc MEM_SRC_L
    tax ; Len Low
    lda MEM_END_H
    sbc MEM_SRC_H
    tay ; Len High
    
    ; Add Len to MEM_DEST to get MEM_DEST_END
    txa
    clc
    adc MEM_DEST_L
    sta MEM_DEST_L
    tya
    adc MEM_DEST_H
    sta MEM_DEST_H
    
    ; Now MEM_DEST points to End of Dest Block (Exclusive)
    ; MEM_END points to End of Source Block (Exclusive)
    
_mm_bwd_loop:
    ; Check if done: MEM_END == MEM_SRC ?
    lda MEM_END_L
    cmp MEM_SRC_L
    bne _mm_bwd_do
    lda MEM_END_H
    cmp MEM_SRC_H
    beq _mm_done
    
_mm_bwd_do:
    ; Pre-decrement Pointers
    lda MEM_END_L
    bne 1f
    dec MEM_END_H
1:  dec MEM_END_L
    
    lda MEM_DEST_L
    bne 1f
    dec MEM_DEST_H
1:  dec MEM_DEST_L
    
    ; Copy Byte
    ldy #0
    lda (MEM_END_L), y
    sta (MEM_DEST_L), y
    jmp _mm_bwd_loop

_mm_copy_fwd:
    ; --------------------------------------------------------------------------
    ; FORWARD COPY (Dest < Src)
    ; Start at MEM_SRC, Copy to MEM_DEST, until MEM_SRC == MEM_END
    
_mm_fwd_loop:
    ; Check if done
    lda MEM_SRC_L
    cmp MEM_END_L
    bne _mm_fwd_do
    lda MEM_SRC_H
    cmp MEM_END_H
    beq _mm_done
    
_mm_fwd_do:
    ldy #0
    lda (MEM_SRC_L), y
    sta (MEM_DEST_L), y
    
    ; Increment Pointers
    inc MEM_SRC_L
    bne 1f
    inc MEM_SRC_H
1:
    inc MEM_DEST_L
    bne 1f
    inc MEM_DEST_H
1:
    jmp _mm_fwd_loop

_mm_done:
    rts

; ==============================================================================
; SAVE ROUTINE
; ==============================================================================
do_save:
    ; 1. Parse Filename
    ; Skip command 'S'
    iny
    jsr skip_spaces
    bne _ds_got_char
    
    ; No filename
    lda #<msg_no_filename
    ldx #>msg_no_filename
    jsr puts
    jmp command_loop
    
_ds_got_char:
    ; Copy filename to FILENAME_BUFFER
    ldx #0
_ds_fname_loop:
    lda (PTR_L), y
    beq _ds_check_end_fname ; Null
    cmp #','+$80 ; Check for separator (Drive/Slot)
    beq _ds_check_opt
    cmp #' '+$80 ; Check for space (end of filename?)
    beq _ds_check_end_fname
    
    sta FILENAME_BUFFER, x
    iny
    inx
    cpx #30
    bcc _ds_fname_loop
    ; Truncate if too long (or error)
    
_ds_check_end_fname:
_ds_check_opt:
    ; Terminate Filename (high bit set or not? DOS usually expects high bit set chars, 
    ; but FM calls often take normal strings if length is managed? No, DOS 3.3 is high-bit ASCII.)
    ; We already use high-bit ASCII in minied.
    ; NOTE: DOS 3.3 FM might require the filename to be in a specific format or 
    ; the Name Pointer to point to a string.
    ; Standard DOS 3.3: High Definition ASCII.
    
    ; Ensure filename is clean (no trailing nulls inside buffer if we reuse it).
    ; Fill rest with 0? No, just remember length or ensure terminator?
    ; The FM parameter block takes a pointer. Does it expect a length byte or null?
    ; It expects a pointer to the string. The string usually needs to be valid.
    ; DOS 3.3 File Manager uses the length of the name found? 
    ; Actually, it parses until it hits a non-valid char or max length?
    ; Let's assume standard string conventions.
    
    lda #0
    sta FILENAME_BUFFER, x ; Null terminate for our own sanity
    
    ; Save Y for parsing options
    sty SHIFT_DIFF_L 
    
    ; Set Defaults for DOS
    lda #6
    sta FM_SLOT
    lda #1
    sta FM_DRIVE
    lda #0
    sta FM_VOL
    
    ; Parse Options
    ldy SHIFT_DIFF_L
    lda (PTR_L), y
    cmp #','+$80
    bne _ds_do_save_op ; No options
    
    ; Parse Options loop
_ds_opt_loop:
    iny
    lda (PTR_L), y
    cmp #'D'+$80
    beq _ds_opt_drive
    cmp #'S'+$80
    beq _ds_opt_slot
    cmp #'V'+$80
    beq _ds_opt_vol
    bne _ds_do_save_op ; Unknown or End
    
_ds_opt_drive:
    iny
    lda (PTR_L), y
    and #$0F
    sta FM_DRIVE
    jmp _ds_next_opt
_ds_opt_slot:
    iny
    lda (PTR_L), y
    and #$0F
    sta FM_SLOT
    jmp _ds_next_opt
_ds_opt_vol:
    iny
    jsr PARSE_DECIMAL ; Updates Y, returns in PD_VAL
    lda PD_VAL
    sta FM_VOL
    jmp _ds_next_opt
    
_ds_next_opt:
    ; Check for comma or end
    lda (PTR_L), y
    cmp #','+$80
    beq _ds_opt_loop
    
_ds_do_save_op:
    
    ; Setup Parameter Block Common Fields
    lda #<FILENAME_BUFFER
    sta FM_NAME_PTR
    lda #>FILENAME_BUFFER
    sta FM_NAME_PTR+1
    
    lda #0 ; Text File
    sta FM_FILETYPE
    
    ; --------------------------------------------------------------------------
    ; 1. DELETE FILE (Best practice to ensure clean write)
    ; --------------------------------------------------------------------------
    lda #DOS_DELETE
    sta FM_OPCODE
    jsr call_dos
    ; Ignore error (File might not exist)
    
    ; --------------------------------------------------------------------------
    ; 2. OPEN FILE
    ; --------------------------------------------------------------------------
    lda #DOS_OPEN
    sta FM_OPCODE
    
    ; Set Buffer for DOS (Buffer required for OPEN)
    lda #<DOS_FILE_BUFFER
    sta FM_BUFF_PTR
    lda #>DOS_FILE_BUFFER
    sta FM_BUFF_PTR+1
    
    jsr call_dos
    bcc _ds_open_ok
    jmp _ds_error
    
_ds_open_ok:
    ; --------------------------------------------------------------------------
    ; 3. WRITE FILE
    ; --------------------------------------------------------------------------
    lda #DOS_WRITE
    sta FM_OPCODE
    
    ; Data Buffer to Write = BUFFER_START
    lda #<BUFFER_START
    sta FM_BUFF_PTR
    lda #>BUFFER_START
    sta FM_BUFF_PTR+1
    
    ; Length = TEXT_PTR - BUFFER_START
    lda TEXT_PTR_L
    sec
    sbc #<BUFFER_START
    sta FM_LEN
    lda TEXT_PTR_H
    sbc #>BUFFER_START
    sta FM_LEN+1
    
    ; FILE TYPE = Text
    lda #0
    sta FM_FILETYPE
    
    jsr call_dos
    bcc _ds_write_ok
    jmp _ds_error_close
    
_ds_write_ok:
    
    ; --------------------------------------------------------------------------
    ; 4. CLOSE FILE
    ; --------------------------------------------------------------------------
    lda #DOS_CLOSE
    sta FM_OPCODE
    ; FM_NAME_PTR still valid
    jsr call_dos
    
    ; Success - Clear Dirty Flag
    lda #0
    sta DIRTY_FLAG
    
    lda #<msg_saved
    ldx #>msg_saved
    jsr puts
    jmp command_loop

_ds_error_close:
    ; Try to close file even on error
    pha ; Save Error Code
    lda #DOS_CLOSE
    sta FM_OPCODE
    jsr call_dos
    pla ; Restore Error Code
    ; Fall through to error
    
_ds_error:
    lda #<msg_dos_error
    ldx #>msg_dos_error
    jsr puts
    jsr PRBYTE ; Print Accumulator (Error Code)
    jsr CROUT
    jmp command_loop

call_dos:
    lda #>FM_PARM_BLOCK
    ldy #<FM_PARM_BLOCK
    jsr DOS_FM
    rts

; ==============================================================================
; TYPE ROUTINE
; ==============================================================================
do_type:
    ; 1. Parse Filename (Copy-paste logic from do_save for now to avoid refactoring risk)
    ; Skip command 'T'
    iny
    jsr skip_spaces
    bne _dt_got_char
    
    ; No filename
    lda #<msg_no_filename
    ldx #>msg_no_filename
    jsr puts
    jmp command_loop
    
_dt_got_char:
    ; Copy filename to FILENAME_BUFFER
    ldx #0
_dt_fname_loop:
    lda (PTR_L), y
    beq _dt_check_end_fname ; Null
    cmp #','+$80 ; Check for separator (Drive/Slot)
    beq _dt_check_opt
    cmp #' '+$80 ; Check for space (end of filename?)
    beq _dt_check_end_fname
    
    sta FILENAME_BUFFER, x
    iny
    inx
    cpx #30
    bcc _dt_fname_loop
    
_dt_check_end_fname:
_dt_check_opt:
    lda #0
    sta FILENAME_BUFFER, x 
    
    ; Save Y 
    sty SHIFT_DIFF_L 
    
    ; Set Defaults
    lda #6
    sta FM_SLOT
    lda #1
    sta FM_DRIVE
    lda #0
    sta FM_VOL
    
    ; Parse Options
    ldy SHIFT_DIFF_L
    lda (PTR_L), y
    cmp #','+$80
    bne _dt_do_type_op ; No options
    
    ; Parse Options loop
_dt_opt_loop:
    iny
    lda (PTR_L), y
    cmp #'D'+$80
    beq _dt_opt_drive
    cmp #'S'+$80
    beq _dt_opt_slot
    cmp #'V'+$80
    beq _dt_opt_vol
    bne _dt_do_type_op 
    
_dt_opt_drive:
    iny
    lda (PTR_L), y
    and #$0F
    sta FM_DRIVE
    jmp _dt_next_opt
_dt_opt_slot:
    iny
    lda (PTR_L), y
    and #$0F
    sta FM_SLOT
    jmp _dt_next_opt
_dt_opt_vol:
    iny
    jsr PARSE_DECIMAL 
    lda PD_VAL
    sta FM_VOL
    jmp _dt_next_opt
    
_dt_next_opt:
    lda (PTR_L), y
    cmp #','+$80
    beq _dt_opt_loop
    
_dt_do_type_op:
    
    ; Setup Parameter Block
    lda #<FILENAME_BUFFER
    sta FM_NAME_PTR
    lda #>FILENAME_BUFFER
    sta FM_NAME_PTR+1
    
    lda #0 ; Text File
    sta FM_FILETYPE
    
    ; --------------------------------------------------------------------------
    ; 1. OPEN FILE
    ; --------------------------------------------------------------------------
    lda #DOS_OPEN
    sta FM_OPCODE
    
    lda #<DOS_FILE_BUFFER
    sta FM_BUFF_PTR
    lda #>DOS_FILE_BUFFER
    sta FM_BUFF_PTR+1
    
    jsr call_dos
    bcc _dt_open_ok
    jmp _ds_error ; Reuse error handler
    
_dt_open_ok:
    
    ; --------------------------------------------------------------------------
    ; 2. READ LOOP
    ; --------------------------------------------------------------------------
_dt_read_loop:
    lda #DOS_READ
    sta FM_OPCODE
    
    ; Read 1 byte to TEMP_PTR_L (reuse ZP)
    ; Actually, let's read to a dedicated byte or just reuse a safe ZP?
    ; We can read directly to memory? 
    ; Let's use TEMP_PTR_L ($??) - Check usage.
    ; TEMP_PTR_L is likely mapped to ZP.
    ; Let's use PD_TEMP or similar safe scratch.
    ; Or just a byte in BSS.
    
    lda #<TYPE_CHAR_BUF
    sta FM_BUFF_PTR
    lda #>TYPE_CHAR_BUF
    sta FM_BUFF_PTR+1
    
    lda #1
    sta FM_LEN
    lda #0
    sta FM_LEN+1
    
    jsr call_dos
    bcs _dt_read_fail ; Error or EOF
    
    ; Print Char
    lda TYPE_CHAR_BUF
    ora #$80 ; Ensure Normal Video (if standard ASCII)
    jsr COUT
    
    jmp _dt_read_loop
    
_dt_read_fail:
    ; Check error code. 
    ; If EOF (End of Data), usually specific code.
    ; DOS 3.3 End of Data = 5.
    cmp #5
    beq _dt_eof
    
    ; Real error
    jmp _ds_error_close
    
_dt_eof:
    ; --------------------------------------------------------------------------
    ; 3. CLOSE FILE
    ; --------------------------------------------------------------------------
    lda #DOS_CLOSE
    sta FM_OPCODE
    jsr call_dos
    
    jsr CROUT
    jmp command_loop


.inc "data.inc"
