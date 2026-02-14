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

BUFFER_START = $3000
MAX_LINES = 20
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
    and #$DF ; Convert to upper case (0x61->0x41, 0xE1->0xC1) - effectively clears bit 5
    
    ; look up command from cmd_table
    ldx #0
1:  lda cmd_table,x
    beq cmd_table_end
    cmp (PTR_L),y
    beq 1f
    inx
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
    .byte 'A'+$80, 'P'+$80, 'Q'+$80, 'H'+$80, 0
cmd_impl_table:
    .word do_append, do_print, do_quit, do_home, 0

do_quit:
    rts

do_home:
    jsr HOME
    jmp command_loop

do_print:
    ; Print all lines
    lda #<BUFFER_START
    sta PTR_L
    lda #>BUFFER_START
    sta PTR_H
    
    ldx LINE_IDX
    beq print_done
    
print_line_loop:
    ldy #0
print_char_loop:
    lda (PTR_L), Y
    beq end_of_line
    jsr COUT
    iny
    bne print_char_loop
end_of_line:
    lda #CR
    jsr COUT
    
    ; Advance pointer to next line (Y+1)
    tya
    clc
    adc #1
    adc PTR_L
    sta PTR_L
    lda PTR_H
    adc #0
    sta PTR_H
    
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

msg_welcome:
    .byte "MINIED 1.1", $0d, 0
    
LINE_IDX:
    .byte 0
