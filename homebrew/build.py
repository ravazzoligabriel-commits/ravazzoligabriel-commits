"""Build original MIT-licensed GBA Pixel Adventure. No Nintendo logo/BIOS/assets.

The ARM program itself polls real GBA MMIO, waits for VBlank and draws VRAM.
Directional buttons move the red explorer; A/B change its color; Start resets.
The cartridge stores position in SRAM each turn. This is software running on
emulated hardware, not a frontend pretending to emulate a game.
"""
from pathlib import Path
from keystone import Ks, KS_ARCH_ARM, KS_MODE_ARM, KS_MODE_LITTLE_ENDIAN

PROGRAM = r'''
    ldr r0, =0x04000000
    ldr r1, =0x0403
    strh r1, [r0]
    ldr r8, =0x0e000000
    ldrb r1, [r8]
    cmp r1, #42
    moveq r4, #0
    ldrbeq r4, [r8, #1]
    ldrbeq r5, [r8, #2]
    movne r4, #112
    movne r5, #72
    ldr r6, =0x001f
loop:
    ldr r0, =0x04000006
wait_end:
    ldrh r1, [r0]
    cmp r1, #160
    bge wait_end
wait_begin:
    ldrh r1, [r0]
    cmp r1, #160
    blt wait_begin
    ldr r0, =0x04000130
    ldrh r7, [r0]
    tst r7, #16
    addeq r4, r4, #1
    tst r7, #32
    subeq r4, r4, #1
    tst r7, #64
    subeq r5, r5, #1
    tst r7, #128
    addeq r5, r5, #1
    tst r7, #1
    ldreq r6, =0x03ff
    tst r7, #2
    ldreq r6, =0x7c1f
    tst r7, #8
    moveq r4, #112
    moveq r5, #72
    cmp r4, #8
    movlt r4, #8
    cmp r4, #216
    movgt r4, #216
    cmp r5, #8
    movlt r5, #8
    cmp r5, #136
    movgt r5, #136
    mov r0, #42
    strb r0, [r8]
    strb r4, [r8, #1]
    strb r5, [r8, #2]
    ldr r0, =0x06000000
    mov r1, #0
row:
    mov r2, #0
column:
    ldr r3, =0x14a4
    tst r1, #16
    ldreq r3, =0x18c5
    cmp r2, r4
    blt put
    add r9, r4, #16
    cmp r2, r9
    bge put
    cmp r1, r5
    blt put
    add r9, r5, #16
    cmp r1, r9
    movlt r3, r6
put:
    strh r3, [r0], #2
    add r2, r2, #1
    cmp r2, #240
    blt column
    add r1, r1, #1
    cmp r1, #160
    blt row
    b loop
'''

def build(path):
    assembler = Ks(KS_ARCH_ARM, KS_MODE_ARM | KS_MODE_LITTLE_ENDIAN)
    code, _ = assembler.asm(PROGRAM, addr=0x080000c0)
    header = bytearray(192)
    header[:4] = bytes.fromhex('2e0000ea')  # branch to 0x080000c0
    header[0xa0:0xac] = b'PIXELADVANCE'
    header[0xac:0xb0] = b'PXAD'
    header[0xb2] = 0x96
    header[0xbd] = (-sum(header[0xa0:0xbd])-0x19)&255
    data = header + bytes(code) + b'SRAM_V113\0'
    data += bytes(32768-len(data))
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_bytes(data)
    return path

if __name__ == '__main__':
    import sys
    build(sys.argv[1])
