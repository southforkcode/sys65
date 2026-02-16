---
name: apple2
description: Use this skill when working with Apple II assembly language programming.
---

## When to use this skill

- Use this when developing Apple II assembly language programs. This includes writing new programs, modifying existing programs, and debugging existing programs.

## How to use it

- When you make a code change, you either must have a unit test that you can run or you must add one.
- If you need to execute 6502 code, you should use an integration test that integrates with Virtual ][ using applescript. See below
- Please make sure you can verify your code changes using unit tests or through integration tests.
- Remember YOU MUST RUN THE TESTS YOURSELF

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

### DOS 3.3
- [Beneath DOS Technical Documentation](https://asciiexpress.net/files/docs/Beneath%20Apple%20DOS%20OCR.pdf)

**Safe Locations (Generally):**
- $06-$09 (Often free, used by some BASICs but usually safe for simple machine language programs)
- $EB-$EF (Monitor scratchpad)
- $FA-$FF (Monitor scratchpad)

## Integration Testing with "Virtual ]["
- recompile the code before trying to upload it
- When writing and executing integration tests, use Virtual ][ to load and run the assembly code. See https://www.virtualii.com/VirtualIIHelp/virtual_II_help.html
- When pushing code for integration testing, you have to first rest the machine, then call -151 to enter the monitor, then load the program using the format "<address in hex>: <8 hex bytes>". For example, "0800: 48 65 6c 6c 6f 20 20 20".
- Make sure you are in the monitor before loading the program. You know you are in the monitor by seeing the prompt "*".
- Any temporary files created during integration testing should be placed in the `scratch` directory.

## Project Structure Rules

- All test files must be located in the `tests` subfolder of each project, organized by type (e.g., unit, integration). Do not create tests in the root project directory.


