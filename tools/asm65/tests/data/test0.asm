.org $2000
; byte tests
buffer: .fill 8, $ff
start: .byte $01
string:
.byte "hello world", 0
.byte 01, 02, 03, 077
os_bytes:
.byte %10101010
.byte 0x20, 0b100
table:
.byte >start, <os_bytes

