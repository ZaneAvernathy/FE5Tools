#!/usr/bin/python3

import os
import sys
from PIL import Image
from fe5py.graphics import Color, Palette, rect


sword_template = [
  (( 0,  0), (32, 16), (  0,  0)),
  (( 0, 24), (32, 16), ( 32,  0)),
  ((40,  0), (16, 16), ( 64,  0)),
  ((40, 16), (16, 16), ( 80,  0)),
  ((64,  0), (16, 16), ( 96,  0)),
  ((64, 16), (16, 16), (112,  0)),
  ]


lance_template = [
  (( 0, 24), (16, 16), (  0,  0)),
  ((16, 19), (16,  8), ( 16,  0)),
  ((32, 11), (16,  8), ( 16,  8)),
  ((48,  3), ( 8,  8), ( 32,  0)),
  ((56, 40), (16, 16), ( 40,  0)),
  ((69, 24), ( 8, 16), ( 56,  0)),
  ((77,  8), ( 8, 16), ( 64,  0)),
  ((85,  0), ( 8,  8), ( 32,  8)),
  ((96, 48), (56,  8), ( 72,  8)),
  ]


axe_template = [
  (( 0,  0), (32, 16), (  0,  0)),
  (( 0, 24), (32, 16), ( 32,  0)),
  ((40,  0), (16, 16), ( 64,  0)),
  ((40, 16), (16, 16), ( 80,  0)),
  ((64,  0), (16, 16), ( 96,  0)),
  ((64, 16), (16, 16), (112,  0)),
  ]


bow_template = [
  ((  0,  0), (16, 16), (  0,  0)),
  (( 24,  0), ( 8, 16), ( 16,  0)),
  (( 24, 16), (16, 16), ( 24,  0)),
  (( 48,  0), (16, 16), ( 40,  0)),
  (( 64,  0), ( 8,  8), ( 56,  0)),
  (( 80,  0), (24,  8), ( 80,  0)),
  (( 80, 16), (24,  8), ( 80,  8)),
  ((112,  0), ( 8, 24), (104,  0)),
  ((112, 16), ( 8,  8), (112,  8)),
  ((128,  8), ( 8,  8), ( 56,  8)),
  ((136,  0), (16, 16), ( 64,  0)),
  ]


ballista_template = [
  (( 0,  0), (32, 16), ( 0, 0)),
  ((16, 16), (32, 16), (32, 0)),
  ]


staff_template = [
  (( 0,  0), (16, 16), (64, 0)),
  (( 0, 16), (16, 16), ( 0, 0)),
  (( 0, 32), (16, 16), (16, 0)),
  ((24,  0), (16, 16), (80, 0)),
  ((32, 16), (16, 16), (32, 0)),
  ((32, 32), (16, 16), (48, 0)),
  ]


template_sizes = {
  "sword":    ( 80, 40),
  "lance":    (152, 56),
  "axe":      ( 80, 40),
  "bow":      (152, 32),
  "ballista": ( 48, 32),
  "staff":    ( 48, 48),
  }


templates = {
  "sword":    sword_template,
  "lance":    lance_template,
  "axe":      sword_template,
  "bow":      bow_template,
  "ballista": ballista_template,
  "staff":    staff_template,
  }


palette_zones = {
  "sword":    (  0, 16),
  "lance":    (136,  0),
  "axe":      (  0, 16),
  "bow":      (136, 24),
  "ballista": (  0, 16),
  "staff":    ( 16, 16),
  }


def convert_im(im, palette):
  new = Image.new("P", im.size, palette[0].to_rgb())
  new.putpalette([b for c in palette for b in c.to_rgb()])
  new.putdata([palette.colors.index(Color(c)) for c in im.getdata()])
  return new


def main():

  _, infile = sys.argv

  dirname, fname = os.path.split(infile)
  name, weapontype, _ = fname.split(".")
  weapontype = weapontype.lower()

  try:
    template = templates[weapontype]
  except KeyError:
    sys.exit(f"Unknown weapon type \"{weapontype}\"")

  im = Image.open(infile)

  if im.mode not in ["RGB", "RGBA"]:
    sys.exit("Image must be of type 'RGB'.")

  im = im.convert("RGB")

  # May be naive, but I think that 7 palettes
  # maximum is fine.

  x, y = palette_zones[weapontype]
  bg = Color(im.getpixel((x, y+7)))
  base_palette = Palette(list(im.crop(rect((x, y), (16, 1))).getdata()))

  formatted = Image.new("RGB", (128, 16), base_palette[0].to_rgb())
  for source, size, dest in template:
    formatted.paste(im.crop(rect(source, size)), dest)

  new = convert_im(formatted, base_palette)
  new.save(os.path.join(dirname, name+"FormattedWeapon.png"))

  for i in range(7):
    palette = Palette(list(im.crop(rect((x, y+i), (16, 1))).getdata()))

    # If less than 7 palettes. We check the
    # second color because the first is likely to
    # be the same BG color.
    if palette[1] == bg:
      break

    p_out = palette.to_bytes()
    outname = os.path.join(dirname, name+f"FormattedWeapon{i:02X}.pal")

    with open(outname, "wb") as o:
      o.write(p_out)


if __name__ == '__main__':
  main()
