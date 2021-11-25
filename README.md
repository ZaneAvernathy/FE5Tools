
# FE5 Tools

This is a collection of tools intended to be used for working with Fire Emblem: Thracia 776.

### Requirements

All of these tools require [**a recent version of python 3**](https://www.python.org/). Some of these tools output files for use with [**the 64tass assembler**](https://sourceforge.net/projects/tass64/).

---

### fe5py - Common python code

`fe5py` is a set of code that ends up being common between various python scripts that I write.

---

### c2a - CSV to ASM converter

Usage: `python c2a.py csvfile outfile [indent]`
Example: `python c2a.py Examples/c2aExample.csv Examples/c2aExample.csv.asm 2`

`c2a` converts a formatted CSV table into something insertable using `64tass`. Each row in the table is turned into a set of definitions and a command (usually a struct, macro, or other assembler directive). Each entry is also given a definition for its index in the table.

The upper-leftmost cell in the table contains the command that will be used for each entry along with an index that the first entry will be considered to have started at, separated by a space.

The top row of the table contains names for each field that will be filled in the command. The leftmost column contains the names for each entry. The names are used for the indexes of each entry, and are also combined with the field names for each definition.

The optional indent option when running the script from the command line controls how many spaces each definition is indented by. The default indentation is two spaces, and this option does not have any effect on the data being assembled.

See the included table and output file for an example of how everything looks.

---

### checksum - SNES checksum fixer

Usage: `python checksum.py ROMfile`
Example: `python checksum.py FE5.sfc`

`checksum` calculates the new checksum and complement for the given ROM image. If the new checksum does not match the checksum in the ROM header, writes the new checksum and complement, and prints both.

---

### fix_sym - 64tass VICE symbol fixer

Usage: `python fix_sym.py symfile`
Example: `python fix_sym.py FE5.cpu.sym`

Fixes 64tass' symbol output for use with bsnes-plus.

---

### scan_includes - 64tass dependency scanner

Usage: `python scan_includes.py file [file ...]`
Example: `python scan_includes.py Examples/scan_includesExample.asm`

Scans a file and prints out the filenames of any files included by that file. Also scans any files found, continuing this pattern until no more included files are found.

The primary use of this script is to generate a list of dependencies for use with a Makefile.

---

### compare - binary difference printer

Usage: `python compare.py file1 file2`
Example: `python compare.py Examples/compareExample1.bin Examples/compareExample2.bin`

Given two files, prints differences between them as a series of bytes.

---

### rip_portraits - vanilla portrait ripper

Usage: `python rip_portraits.py ROM_name destination_dir`
Example: `python rip_portraits.py FE5.sfc PORTRAITS`

This script rips FE5's portraits into nice .pngs and puts them in `destination_dir`.
