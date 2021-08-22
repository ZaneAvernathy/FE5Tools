#!/usr/bin/python3

import sys

if __name__ == "__main__":

    ROMfile = sys.argv[1]

    with open(ROMfile, "rb") as i:
        ROM = bytearray(i.read())

    oldsum = int.from_bytes(ROM[0x7FDE:0x7FE0], "little")

    checksum = sum(ROM) & 0xFFFF
    complement = (checksum ^ 0xFFFF) & 0xFFFF

    if checksum != oldsum:
        ROM[0x7FDC:0x7FDE] = complement.to_bytes(2, "little")
        ROM[0x7FDE:0x7FE0] = checksum.to_bytes(2, "little")

        with open(ROMfile, "wb") as o:
            o.write(ROM)

        print(f"New checksums for ROM {ROMfile}:")
        print(f"Checksum:   0x{checksum:04X}")
        print(f"Complement: 0x{complement:04X}")
