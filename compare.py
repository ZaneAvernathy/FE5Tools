#!/usr/bin/python3

import sys
from os.path import basename

"""
This script prints differences between
two files in a series of hexdumps.

"""

def format_bin(data):
  return "".join(["{0:02X}{1}".format(b, "\n" if ((i+1) % 16) == 0 else " ") for (i, b) in enumerate(data)])


def diff(fname1, fname2, f1, f2, offset, diffsize):
  yield f"Difference at 0x{offset:06X}"

  yield f"{basename(fname1)}:"
  yield format_bin(f1[offset:offset+diffsize])

  yield ""

  yield f"{basename(fname2)}:"
  yield format_bin(f2[offset:offset+diffsize])

  yield ""


if __name__ == "__main__":

  fname1, fname2 = sys.argv[1], sys.argv[2]

  with open(fname1, "rb") as i:
    f1 = i.read()

  with open(fname2, "rb") as i:
    f2 = i.read()

  s1, s2 = len(f1), len(f2)

  if (s1 != s2):

    print("File lengths do not match:")
    print(f"{basename(fname1)}: 0x{s1:06X}")
    print(f"{basename(fname2)}: 0x{s2:06X}")

  offset = 0
  maxsize = min(s1, s2)

  while (offset+1 < maxsize):

    if (f1[offset] != f2[offset]):

      diffsize = 1
      while (f1[offset+diffsize] != f2[offset+diffsize]):

        diffsize += 1

        if (offset+diffsize >=  maxsize):
          break

      print(*diff(fname1, fname2, f1, f2, offset, diffsize), sep="\n")

      offset += diffsize

    else:

      offset += 1
