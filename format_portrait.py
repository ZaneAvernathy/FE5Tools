#!/usr/bin/python3

import sys
import os
from PIL import Image
from fe5py.graphics import Palette, rect

def main():

  # Example: python format_portrait.py PORTRAITS/Alba.png

  # Converts a templated portrait into the layout that FE5 expects.
  # Also processes the portrait's palette(s) into native data.

  # After using this script to format a portrait, you can
  # turn it into native data using a tool like superfamiconv:
  # superfamiconv tiles -i SomeFormattedPortrait.png
  #   -p SomeFormattedPortrait00.pal -d SomeFormattedPortrait.4bpp -B 4 -D -F

  infile = sys.argv[1]
  basename = os.path.splitext(infile)[0]
  outfile = basename + "FormattedPortrait.png"
  pal_name_template = basename + "FormattedPortrait{0:02X}.pal"

  im = Image.open(infile).convert("RGB")

  default_palette = Palette.from_image(im.crop(rect((48, 0), (16, 1))), 16)

  formatted_im = Image.new("RGB", (128, 32))

  upper = im.crop(( 0,  0, 48, 32))
  lower = im.crop(( 0, 32, 80, 64))

  formatted_im.paste(upper, ( 0, 0))
  formatted_im.paste(lower, (48, 0))

  formatted_im.save(outfile)

  bg_color = default_palette[0]

  for pal_index in range(16):
    p = Palette.from_image(im.crop(rect((48, pal_index), (16, 1))), 16)

    if (len(p) == 1) and (p[0] == bg_color):
      break

    with open(pal_name_template.format(pal_index), "wb") as o:
      o.write(p.to_bytes(16))


if __name__ == '__main__':
  main()
