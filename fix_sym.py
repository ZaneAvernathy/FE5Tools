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

    with open(symfile, "w", encoding="UTF-8") as o:
        o.writelines(sorted(fixed))
