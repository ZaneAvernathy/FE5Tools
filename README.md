
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

### format_portrait - turn templated portraits into raw format

Usage: `python format_portrait.py portrait.png`
Example: `python format_portrait.py Examples/Soldier.png`

Given a templated portrait, outputs an image in the format that FE5 expects. Also outputs all palettes.

The templated format is an 80x64 RGB .png image. The main portrait takes up the left side. The portrait's talking frames are at (48, 32) for the openmost frame and (48, 48) for the partially-open frame. All of the portrait's palettes are at (48, 0+), with each new palette a pixel below the last. See the example `Examples/Soldier.png`.

---

### rip_portraits - vanilla portrait ripper

Usage: `python rip_portraits.py ROM_name destination_dir`
Example: `python rip_portraits.py FE5.sfc PORTRAITS`

This script rips FE5's portraits into nice .pngs and puts them in `destination_dir`.

---

### fe5tileset - tileset updating/creating utility

Usage: `python fe5tileset.py (update|create|export) filepath [index]`
Example: `python fe5tileset.py create Examples/Tileset/Example.tmx 5`

This script creates and updates tilesets for use with [**the Tiled map editor**](https://www.mapeditor.org/). It stores the tilesets as Tiled .tmx files alongside 8 tile graphics images and an export tileset image, which will be used as the tileset image for editing maps.

Each tile graphics image contains the same tiles as the others, just using a different palette. They are labeled 0-7 and the tileset's exported palette will be in this order. Each image is a 128px by 320px indexed 16-color .png. The first color in each palette is considered to be the transparent color, although there is never any layering.

For a tileset `folder/foo.tmx`, the tiles images are named `folder/foo_0.png`, `folder/foo_1.png`, etc. Specifying an `index` for `update` or `create` will use the corresponding image, i.e. `python fe5tileset.py update folder/foo.tmx 4` will use `folder/foo_4.png`.

The tilesets themselves are 64x64 graphics tiles that get assembled into a 32x32 metatile image suitable for mapping. Each tileset uses Tiled's object layer to specify the terrain type for its metatiles, where the object's `type` field determines the type. This field has the format `0xNN whatever` where `0xNN` is a hexadecimal byte with the terrain type and `whatever` is an optional terrain name, which is included in generated tilesets for convenience. The name isn't assembled into anything.

You can check [**here**](https://github.com/ZaneAvernathy/VoltEdge/blob/master/VOLTEDGE/Terrain.h) for a list of terrain types.
