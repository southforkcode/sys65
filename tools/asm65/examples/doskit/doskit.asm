.include "dos.inc"
PTR = $06

    .org $2000

start:
    jmp main

.align $100
main:
    jsr LOCRPL ; Load RWTS parameter list
    STY PTR
    STA PTR+1
    rts


read_catalog:
    lda #<iocblock
    ldy #>iocblock
    jsr RWTS
    rts

.align 16
iocblock:
table_type:
    .byte 1 ; must be 1
slot_num: 
    .byte 0 ; slot number
drive_num:
    .byte 0 ; drive number
vol_num:
    .byte 0 ; volume number
track_num:
    .byte 0 ; track number
sector_num:
    .byte 0 ; sector number
device_chars:
    .word dev_chars_tbl ; device characteristics table pointer
rw_buffer:
    .word read_buffer ; read/write buffer pointer
    .byte 0 ; not used
byte_count:
    .byte 0 ; 0 = 256 bytes
command_code:
    .byte 0 ; 0 = seek, 1 = read, 2 = write, 4 = format
return_code:
    .byte 0 ; return code



dev_chars_tbl:
    .byte 0 ; must be 0 for DISK II
    .byte 1 ; must be 1 for DISK II
    .word $EFD8 ; must be $EFD8 for DISK II

read_buffer:
    .fill 256, 0
