import sys
import os

from lib.asm import Assembler

if __name__ == "__main__":
  # parse command line: 1 or more input files, 1 output file
  args = sys.argv[1:]
  if len(args) < 2:
    print("Usage: asm65 <input>+ <output>")
    sys.exit(1)

  input_files = args[:-1]
  output_file = args[-1]

  asm = Assembler()
  for input_file in input_files:
    if not os.path.exists(input_file):
      print(f"Error: {input_file} does not exist")
      sys.exit(1)

    with open(input_file, "r") as f:
      print(f"Assembling {input_file}")
      asm.assemble_stream(f)
      asm.parse()

  # dump symbol table to stdout
  for name, value in asm.symbols.items():
    print(f"{name}: {value}")

  # dump bytes to stdout
  for i in range(len(asm.bytes)):
    b = asm.bytes[i]
    if i % 16 != 0: print(" ", end="")
    print(f"{b:02x}", end="")
    if i % 16 == 15: print()
  print()

