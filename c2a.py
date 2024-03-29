#!/usr/bin/python3
import sys
from os.path import basename, splitext
import csv


def add_def(definition, value):
    definitions.append(f'{definition.ljust(reserved, " ")} = {value}\n')


if __name__ == "__main__":

    (inname, outname), indent = sys.argv[1:3], 2

    if len(sys.argv) == 4:
        try:
            indent = int(sys.argv[3])
        except:
            print(f'Invalid spacing "{sys.argv[3]}", ignoring')

    tablename = splitext(basename(inname))[0].strip()

    with open(inname, "r", encoding="UTF-8") as c:
        sheet = csv.reader(c)
        row1 = next(sheet)
        rows = [row for row in sheet]

    parts = row1[0].split()

    if (len(parts) == 3):
        (command, start, step) = parts
    elif (len(parts) == 2):
        (command, start) = parts
        step = 1
    elif (len(parts) == 1):
        command = parts[0]
        start, step = 0, 1
    else:
        raise ValueError(f"Unable to parse first cell: {row1[0]}.")

    fields = row1[1:]
    start = int(start)
    step = int(step)

    fieldwidth = max(len(f) for f in fields)
    namewidth = max(len(row[0]) for row in rows)
    reserved = indent + namewidth + fieldwidth

    definitions, table = [], []

    for index, [name, *items] in enumerate(rows):

        add_def(name, start + (index * step))
        for i, item in enumerate(items):
            field = (" " * indent) + name + fields[i]
            add_def(field, item)

        definitions.append("\n")

        args = ", ".join([name + field for field in fields])
        table.append(f"{name}{tablename}Entry {command} {args}\n")

    with open(outname, "w", encoding="UTF-8") as o:
        o.writelines(definitions)
        o.writelines(table)
