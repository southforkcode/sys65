import sys
import os
import argparse

from lib.asm import Assembler

def write_hex_output(asm, output_file):
    with open(output_file, "w") as f:
        # Iterate bytes and print
        # Assumption: asm.bytes corresponds to [asm.origin ... asm.origin + len]
        # We print 16 bytes per line
        start_addr = asm.origin
        data = asm.bytes
        
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            # Format: 'ADDRESS: B1 B2 ...'
            # Address is 16-bit hex
            # Bytes are 2-char hex
            addr = start_addr + i
            hex_bytes = " ".join(f"{b:02X}" for b in chunk)
            f.write(f"{addr:04X}: {hex_bytes}\n")

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="asm65 - 6502 Assembler")
  parser.add_argument("input_files", nargs="+", help="Input assembly files")
  parser.add_argument("output_file", help="Output binary file")
  parser.add_argument("-f", "--format", choices=["bin", "hex"], default="bin", help="Output format (bin is default)")
  parser.add_argument("-D", "--define", action="append", help="Define symbol (e.g. -DDEBUG or -DMAX_LINES=10)")
  
  args = parser.parse_args()

  asm = Assembler()
  
  # Inject definitions
  if args.define:
      for define in args.define:
          parts = define.split('=')
          name = parts[0]
          val = 1
          if len(parts) > 1:
              try:
                  val = int(parts[1], 0) # Handle 0x prefix
              except ValueError:
                  print(f"Invalid value for definition {name}: {parts[1]}")
                  sys.exit(1)
          asm.symbols.set(name, val)

  for input_file in args.input_files:
    if not os.path.exists(input_file):
      print(f"Error: {input_file} does not exist")
      sys.exit(1)

    with open(input_file, "r") as f:
      print(f"Assembling {input_file}")
      asm.assemble_stream(f, input_file)
      asm.parse()

  # dump symbol table to stdout (optional, maybe suppress?)
  # Keeping it as is helpful for debugging
  for name, value in asm.symbols.items():
    print(f"{name}: {value}")

  # dump bytes to stdout
  for i in range(len(asm.bytes)):
    b = asm.bytes[i]
    if i % 16 != 0: print(" ", end="")
    print(f"{b:02x}", end="")
    if i % 16 == 15: print()
  print()

  # Write output
  if args.format == "bin":
      with open(args.output_file, "wb") as f:
          f.write(bytearray(asm.bytes))
      print(f"Written {len(asm.bytes)} bytes to {args.output_file} (binary)")
  elif args.format == "hex":
      write_hex_output(asm, args.output_file)
      print(f"Written {len(asm.bytes)} bytes to {args.output_file} (hex)")

