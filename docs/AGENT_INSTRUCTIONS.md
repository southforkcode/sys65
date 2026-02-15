# Agent Instructions

## Reference Documentation

When working with Apple II assembly, avoid using Zero Page locations that are used by the Monitor, DOS, or BASIC.

### Safe Locations (Generally):
- $06-$09 (Often free, used by some BASICs but usually safe for simple machine language programs)
- $EB-$EF (Monitor scratchpad)
- $FA-$FF (Monitor scratchpad)

### Apple II Memory Locations / Zero Page / Routines / IO
- [Apple II Zero Page Usage](https://www.kreativekorp.com/miscpages/a2info/zeropage.shtml)
- [Apple II Memory Areas](https://www.kreativekorp.com/miscpages/a2info/memorymap.shtml)
- [Apple II Monitor Routines](https://www.kreativekorp.com/miscpages/a2info/monitors.shtml)
- [Apple II Screen Holes](https://www.kreativekorp.com/miscpages/a2info/screenholes.shtml)
- [Apple II Memory Mapped I/O](https://www.kreativekorp.com/miscpages/a2info/iomemory.shtml)

**Safe Locations (Generally):**
- $06-$09 (Often free, used by some BASICs but usually safe for simple machine language programs)
- $EB-$EF (Monitor scratchpad)
- $FA-$FF (Monitor scratchpad)

## Virtual ][
- When writing and executing integration tests, use Virtual ][ to load and run the assembly code. See https://www.virtualii.com/VirtualIIHelp/virtual_II_help.html

## Project Structure Rules

- All test files must be located in the `tests` subfolder of each project, organized by type (e.g., unit, integration). Do not create tests in the root project directory.
