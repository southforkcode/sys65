.org $1000
; Test forward references
start:
    .byte $4C       ; JMP opcode
    .word target    ; Forward reference (WORD)
    
    .byte $A9       ; LDA # opcode
    .byte <target   ; Forward reference (LOW)
    
    .byte $A9       ; LDA # opcode
    .byte >target   ; Forward reference (HIGH)
    
target:
    .byte $EA       ; NOP
