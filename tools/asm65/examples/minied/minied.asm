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

BUFFER_START = $3000
MAX_LINES = 200
PROMPT = '>' + $80
CMD_BUFFER = $2F00 ; Command line buffer


start:
    ; Initialize text buffer pointer
    lda #<BUFFER_START
    sta TEXT_PTR_L
    lda #>BUFFER_START
    sta TEXT_PTR_H
    
    lda #0
    sta LINE_IDX

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
    ; Convert to upper case (0x61->0x41, 0xE1->0xC1) - effectively clears bit 5
    and #$DF
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
    cmp #0 ; End of string?
    beq command_loop ; Just ignore empty line
    
    ; Unknown command
    jsr PRERR
    jsr BELL
    jsr CROUT
    jmp command_loop

cmd_impl:
    .word 0
cmd_table:
    .byte 'A'+$80, 'P'+$80, 'Q'+$80, 'H'+$80, 'E'+$80, 'D'+$80, 'I'+$80, 0
cmd_impl_table:
    .word do_append, do_print, do_quit, do_home, do_edit, do_delete, do_insert, 0

do_quit:
    rts

do_home:
    jsr HOME
    jmp command_loop

do_print:
    ; Parse optional arguments
    ; Y points to command char 'P' in CMD_BUFFER
    iny
    
_dp_skip_space:
    lda (PTR_L), y
    beq _dp_no_arg
    cmp #' '+$80
    bne _dp_check_arg
    iny
    bne _dp_skip_space
    
_dp_check_arg:
    cmp #'0'+$80
    bcc _dp_no_arg ; Not a digit
    cmp #'9'+$80+1
    bcs _dp_no_arg ; Not a digit
    
    ; Parse digit
    jsr PARSE_DECIMAL
    sta TARGET_LINE
    jmp _dp_start
    
_dp_no_arg:
    lda #0
    sta TARGET_LINE

_dp_start:
    ; Print lines
    lda #<BUFFER_START
    sta PTR_L
    lda #>BUFFER_START
    sta PTR_H
    
    lda #1
    sta CURRENT_LINE
    
    ldx LINE_IDX
    beq print_done
    
print_line_loop:
    ; Check if we should print this line
    lda TARGET_LINE
    beq _pl_do_print ; 0 = print all
    cmp CURRENT_LINE
    beq _pl_do_print
    
    ; Skip this line
    ldy #0
_pl_skip_scan:
    lda (PTR_L),y
    beq _pl_next_line ; Found null
    iny
    bne _pl_skip_scan
    
_pl_do_print:
    lda CURRENT_LINE
    jsr PRDEC
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
    dex
    bne print_line_loop
    
print_done:
    jmp command_loop

do_append:
    ; Append lines to TEXT_PTR
append_loop:
    ; Copy TEXT_PTR to PTR for get_line
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
    jmp append_loop

stop_append:
    jmp command_loop

do_edit:
    ; 1. Parse argument
    iny
_de_skip_space:
    lda (PTR_L), y
    beq _de_jmp_no_arg
    cmp #' '+$80
    bne _de_check_arg
    iny
    bne _de_skip_space

_de_jmp_no_arg:
    jmp _de_no_arg
    
_de_check_arg:
    cmp #'0'+$80
    bcc _de_jmp_no_arg
    cmp #'9'+$80+1
    bcs _de_jmp_no_arg
    
    jsr PARSE_DECIMAL
    sta TARGET_LINE
    
    ; Check if valid (1 <= TARGET <= LINE_IDX)
    lda TARGET_LINE
    beq _de_jmp_invalid
    cmp LINE_IDX
    beq _de_valid_chk
    bcs _de_jmp_invalid ; TARGET > LINE_IDX
    jmp _de_valid_chk

_de_jmp_invalid:
    jmp _de_invalid

_de_valid_chk:
    
    ; 2. Find line address
    lda #<BUFFER_START
    sta EDIT_PTR_L
    lda #>BUFFER_START
    sta EDIT_PTR_H
    
    ldx TARGET_LINE
    dex
    beq _de_found_line
    
_de_find_loop:
    ldy #0
_de_scan_line:
    lda (EDIT_PTR_L), y
    beq _de_next_line
    iny
    bne _de_scan_line
_de_next_line:
    tya
    clc
    adc #1
    adc EDIT_PTR_L
    sta EDIT_PTR_L
    lda EDIT_PTR_H
    adc #0
    sta EDIT_PTR_H
    dex
    bne _de_find_loop
    
_de_found_line:
    ; 3. Print current line
    lda TARGET_LINE
    jsr PRDEC
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
    jmp command_loop

_de_cancel:
    jmp command_loop

do_delete:
    ; 1. Parse argument
    iny
_dd_skip_space:
    lda (PTR_L), y
    beq _dd_no_arg
    cmp #' '+$80
    bne _dd_check_arg
    iny
    bne _dd_skip_space

_dd_check_arg:
    cmp #'0'+$80
    bcc _dd_no_arg
    cmp #'9'+$80+1
    bcs _dd_no_arg
    
    jsr PARSE_DECIMAL
    sta TARGET_LINE
    
    ; Check if valid (1 <= TARGET <= LINE_IDX)
    lda TARGET_LINE
    beq _dd_invalid
    cmp LINE_IDX
    beq _dd_valid_chk
    bcs _dd_invalid ; TARGET > LINE_IDX

_dd_valid_chk:
    ; 2. Find line address (store in SHIFT_DEST)
    lda #<BUFFER_START
    sta SHIFT_DEST_L
    lda #>BUFFER_START
    sta SHIFT_DEST_H
    
    ldx TARGET_LINE
    dex
    beq _dd_found_line
    
_dd_find_loop:
    ldy #0
_dd_scan_line:
    lda (SHIFT_DEST_L), y
    beq _dd_next_line
    iny
    bne _dd_scan_line
_dd_next_line:
    tya
    clc
    adc #1
    adc SHIFT_DEST_L
    sta SHIFT_DEST_L
    lda SHIFT_DEST_H
    adc #0
    sta SHIFT_DEST_H
    dex
    bne _dd_find_loop

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
    beq _dd_last_line
    
    ; Not last line, shift everything down
    jsr shift_down
    dec LINE_IDX
    jmp command_loop

_dd_last_line:
    ; Just update TEXT_PTR to SHIFT_DEST
    lda SHIFT_DEST_L
    sta TEXT_PTR_L
    lda SHIFT_DEST_H
    sta TEXT_PTR_H
    dec LINE_IDX
    jmp command_loop

_dd_invalid:
_dd_no_arg:
    jsr PRERR
    jmp command_loop

do_insert:
    ; 1. Parsing similar to others
    iny
_di_skip_space:
    lda (PTR_L), y
    bne _di_check_arg_trampoline
    jmp _di_no_arg

_di_check_arg_trampoline:
    cmp #' '+$80
    bne _di_check_arg
    iny
    bne _di_skip_space
    
_di_check_arg:
    cmp #'0'+$80
    bcc _di_no_arg_trampoline
    cmp #'9'+$80+1
    bcs _di_no_arg_trampoline
    
    jsr PARSE_DECIMAL
    sta TARGET_LINE
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
    lda #<BUFFER_START
    sta EDIT_PTR_L ; Using EDIT_PTR to hold insertion point
    lda #>BUFFER_START
    sta EDIT_PTR_H
    
    ldx TARGET_LINE
    dex
    bne _di_start_loop
    jmp _di_input_loop

_di_start_loop:
    jmp _di_find_loop_entry

_di_find_loop_entry: ; Used as label
_di_find_loop:
    ldy #0
_di_scan:
    lda (EDIT_PTR_L), y
    beq _di_next
    iny
    bne _di_scan
_di_next:
    tya
    clc
    adc #1
    adc EDIT_PTR_L
    sta EDIT_PTR_L
    lda EDIT_PTR_H
    adc #0
    sta EDIT_PTR_H
    dex
    bne _di_find_loop_trampoline_2
    jmp _di_input_loop

_di_find_loop_trampoline_2:
    jmp _di_find_loop_entry
    
_di_input_loop:
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
    
    jmp _di_reloop

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
    jmp _di_input_loop

_di_reloop:
    jmp command_loop

_di_invalid:
_di_no_arg:
    jsr PRERR
    jmp command_loop

_de_invalid:
_de_no_arg:
    jsr PRERR
    jmp command_loop

shift_down:
    ; Copy from SRC to DEST until SRC == TEXT_PTR
    ; Forward copy
_sd_loop:
    lda SHIFT_SRC_L
    cmp TEXT_PTR_L
    bne _sd_copy
    lda SHIFT_SRC_H
    cmp TEXT_PTR_H
    beq _sd_finish
_sd_copy:
    ldy #0
    lda (SHIFT_SRC_L), y
    sta (SHIFT_DEST_L), y
    
    ; Increment 16-bit pointers for next iteration
    inc SHIFT_SRC_L
    bne 1f
    inc SHIFT_SRC_H
1:  inc SHIFT_DEST_L
    bne 1f
    inc SHIFT_DEST_H
1:  jmp _sd_loop
    
_sd_finish:
    ; Update TEXT_PTR = DEST
    lda SHIFT_DEST_L
    sta TEXT_PTR_L
    lda SHIFT_DEST_H
    sta TEXT_PTR_H
    rts

shift_up:
    ; Expand buffer.
    ; Copy backwards.
    ; First, calculate how much we are shifting by and set pointers
    
    ; Calc Diff
    lda SHIFT_DEST_L
    sec
    sbc SHIFT_SRC_L
    sta SHIFT_DIFF_L
    
    ; DEST_PTR (Use TEMP variable for write pointer) = TEXT_PTR + Diff
    lda TEXT_PTR_L
    clc
    adc SHIFT_DIFF_L
    sta TEMP_PTR_L
    lda TEXT_PTR_H
    adc #0 ; Carry prop
    sta TEMP_PTR_H
    
    ; Save New End of Buffer position
    lda TEMP_PTR_L
    sta SHIFT_DEST_L
    lda TEMP_PTR_H
    sta SHIFT_DEST_H 
    
    ; shift_up now needs to read from TEXT_PTR (going backwards) 
    ; and write to SHIFT_DEST (going backwards)
    ; until TEXT_PTR reaches SHIFT_SRC.
    
_su_loop:
    ; Check if Read Pointer (TEXT_PTR) == SHIFT_SRC
    lda TEXT_PTR_L
    cmp SHIFT_SRC_L
    bne _su_do
    lda TEXT_PTR_H
    cmp SHIFT_SRC_H
    beq _su_finish
    
_su_do:
    ; Pre-decrement Pointers
    
    ; Dec Write Pointer (SHIFT_DEST)
    lda SHIFT_DEST_L
    bne 1f
    dec SHIFT_DEST_H
1:  dec SHIFT_DEST_L
    
    ; Dec Read Pointer (TEXT_PTR)
    ; TEXT_PTR is being used as READ_PTR here
    lda TEXT_PTR_L
    bne 1f
    dec TEXT_PTR_H
1:  dec TEXT_PTR_L
    
    ; Copy
    ldy #0
    lda (TEXT_PTR_L), y ; Read
    sta (SHIFT_DEST_L), y ; Write
    
    jmp _su_loop
    
_su_finish:
    ; Update global TEXT_PTR to New End
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
; Returns value in A. Updates Y.
PARSE_DECIMAL:
    lda #0
    sta PD_VAL
_pd_loop:
    lda (PTR_L),y
    cmp #'0'+$80
    bcc _pd_done
    cmp #'9'+$80+1
    bcs _pd_done
    
    ; Convert to int
    and #$0F
    pha ; Push digit
    
    ; Val = Val * 10
    lda PD_VAL
    asl a
    sta PD_TEMP
    asl a
    asl a
    clc
    adc PD_TEMP
    sta PD_VAL
    
    pla ; Pop digit
    clc
    adc PD_VAL
    sta PD_VAL
    
    iny
    bne _pd_loop
_pd_done:
    lda PD_VAL
    rts

msg_welcome:
    .byte "MINIED 1.1", $0d, 0
    
LINE_IDX:
    .byte 0

CURRENT_LINE: .byte 0
PRDEC_TMP: .byte 0
PRDEC_FLAG: .byte 0
PRDEC_SAVEX: .byte 0
TARGET_LINE: .byte 0
PD_VAL: .byte 0
PD_TEMP: .byte 0
    
OLD_LEN_VAR: .byte 0
NEW_LEN_VAR: .byte 0
SHIFT_BLOCK_START_L: .byte 0
SHIFT_BLOCK_START_H: .byte 0
TEMP_PTR_L: .byte 0
TEMP_PTR_H: .byte 0
SHIFT_DIFF_L: .byte 0
