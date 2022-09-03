#!/usr/bin/python3

import sys

"""
This is a simple script to fix
64tass' VICE symbol output to be
usable with bsnes-plus.

It has three goals:
Ensure addresses are 6 characters long
remove periods at the start of label names
change the scope character from colon to period
"""

if __name__ == "__main__":

    symfile = sys.argv[1]

    with open(symfile, "r", encoding="UTF-8") as i:
        lines = i.readlines()

    fixed = []

    for line in lines:
        _, address, label = line.split()
        label = label.lstrip(".").replace(":", ".")
        fixed.append(f"al {int(address, 16):06X} {label}\n")

    def keyfunc(string):
        """
        Turn a VICE symbol line into a sorting key value.

        This aims to help when sorting lines with the same
        address, like a table and its first entry, along with
        the first part of the first entry. We want to ensure
        that the order is table->entry->entry field.
        """
        _, address, symbol = string.split()
        address = int("0x" + address, 16)
        nesting_level = symbol.count(".")
        return (address, nesting_level, len(symbol))

    with open(symfile, "w", encoding="UTF-8") as o:
        o.writelines(sorted(fixed, key=keyfunc))
