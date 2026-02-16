; minied data structures and Constants
.align $100

cmd_impl:
    .word 0
cmd_table:
    .byte 'A'+$80, 'P'+$80, 'Q'+$80, 'H'+$80, 'E'+$80, 'D'+$80, 'I'+$80, 'F'+$80, 'B'+$80, '?'+$80, 'N'+$80, 'S'+$80, 'T'+$80
.ifdef DEBUG
    .byte '*'+$80
.endif
    .byte 0

cmd_impl_table:
    .word do_append, do_print, do_quit, do_home, do_edit, do_delete, do_insert, do_find, do_buffer_status, do_help, do_new, do_save, do_type
.ifdef DEBUG
    .word do_fill
.endif
    .word 0



msg_help_0:
    .byte "COMMANDS:", $0D
    .byte " A       : APPEND LINES", $0D
    .byte " P [N]   : PRINT LINES", $0D
    .byte " D N     : DELETE LINE N", $0D
    .byte " I N     : INSERT BEFORE LINE N", $0D
    .byte " E N     : EDIT LINE N", $0D
    .byte 0
msg_help_1:
    .byte " F STR   : FIND STRING", $0D
    .byte " B       : BUFFER STATUS", $0D
    .byte " H       : CLEAR SCREEN", $0D
    .byte " ?       : HELP", $0D
    .byte " Q       : QUIT", $0D
    .byte 0
msg_help_2:
    .byte " S FILE  : SAVE BUFFER", $0D
    .byte " T FILE  : TYPE FILE", $0D
    .byte 0

msg_help_3:
.ifdef DEBUG
    .byte $0D, "*** DEBUG COMMANDS:", $0D
    .byte " * N     : FILL N LINES", $0D
.endif
    .byte 0

; VARIABLES
LINE_IDX: .word 0
CURRENT_LINE: .word 0
PRDEC_TMP: .byte 0
PRDEC_FLAG: .byte 0
PRDEC_SAVEX: .byte 0
TARGET_LINE: .word 0

msg_next: .byte "NEXT/CANCEL? ", 0
msg_welcome: .byte "MINIED 1.2", $0d, 0
msg_buffer_full: .byte "ERR: Buffer Full", $0d, 0
msg_too_many_lines: .byte "Err: Too Many Lines", $0d, 0
msg_saved: .byte "SAVED", $0d, 0
msg_dos_error: .byte "DOS ERROR", $0d, 0
msg_no_filename: .byte "MISSING FILENAME", $0d, 0

; DOS 3.3 Definitions
DOS_FM      = $3D6
DOS_OPEN    = 1
DOS_CLOSE   = 2
DOS_READ    = 3
DOS_WRITE   = 4
DOS_DELETE  = 5
DOS_verify  = 8 ; (Not always standard, stick to basics)

; File Manager Parameter Block (Allocated in ZP or main memory)
; We will use a static block in memory.
.align 16
FM_PARM_BLOCK:
FM_OPCODE:      .byte 0     ; +0
FM_SUBCODE:     .byte 0     ; +1
FM_REC_LEN:     .word 0     ; +2
FM_VOL:         .byte 0     ; +4
FM_DRIVE:       .byte 0     ; +5
FM_SLOT:        .byte 0     ; +6
FM_FILETYPE:    .byte 0     ; +7 (Text=0, Bin=4)
FM_NAME_PTR:    .word 0     ; +8
FM_BUFF_PTR:    .word 0     ; +10
FM_LEN:         .word 0     ; +12
FM_AUX:         .word 0     ; +14 (Binary Address usually)

; Filename Buffer
FILENAME_BUFFER: .fill 32, 0
DOS_FILE_BUFFER: .fill 596, 0 ; DOS requires a 595-byte buffer for OPEN
TYPE_CHAR_BUF:   .fill 1, 0



