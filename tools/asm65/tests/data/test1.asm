; A simple test program
.org $1000
COUT = $FDF0

start:
  lda #<message
  ldx #>message
  jsr prints
  rts

prints:
  sta $04
  stx $05
  ldy #0
prints_:
  lda ($04),y
  beq prints_end
  jsr COUT
  iny
  bne prints_
prints_end:
  rts

message:
  .byte "Hello, World!", 0
