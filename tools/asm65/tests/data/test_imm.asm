.org $1000
; Immediate mode tests
LDA #$01
LDX #$02
LDY #$03
ADC #$04
AND #$05
EOR #$06
ORA #$07
SBC #$08
CMP #$09
CPX #$0A
CPY #$0B
; Check one non-immediate to see fallback
LDA $1234
