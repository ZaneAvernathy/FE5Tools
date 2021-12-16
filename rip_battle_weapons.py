#!/usr/bin/python3

import os
import sys
from PIL import Image
from fe5py.memory import read_byte, read_word, read_long, unlorom
from fe5py.graphics import Color, Palette, rip_image, rect
from fe5py.decompress import decompress

item_base_table = 0x0494ED
image_pointer_table = 0x049403
image_palettes = 0x203090


COLOR_0 = Color((255, 0, 255))
TEMPLATE_BG = Color((104, 219, 121))


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


weapons = {
  0x01: ("IronSword", "sword"),
  0x02: ("SteelSword", "sword"),
  0x03: ("SilverSword", "sword"),
  0x04: ("SlimSword", "sword"),
  0x05: ("IronBlade", "sword"),
  0x06: ("KillingEdge", "sword"),
  0x07: ("PoisonSword", "sword"),
  0x08: ("BerserkSword", "sword"),
  0x09: ("SleepSword", "sword"),
  0x0A: ("BeoBlade", "sword"),
  0x0B: ("BlessedSword", "sword"),
  0x0C: ("LoptyrsBlade", "sword"),
  0x0D: ("BragisBlade", "sword"),
  0x0E: ("LightBrand", "sword"),
  0x0F: ("BraveSword", "sword"),
  0x10: ("SwordOfKings", "sword"),
  0x11: ("EarthSword", "sword"),
  0x12: ("WindSword", "sword"),
  0x13: ("FireBrand", "sword"),
  0x14: ("VoltEdge", "sword"),
  0x15: ("ParagonSword", "sword"),
  0x16: ("Armorslayer", "sword"),
  0x17: ("Rapier", "sword"),
  0x18: ("Shortsword", "sword"),
  0x19: ("Longsword", "sword"),
  0x1A: ("Greatsword", "sword"),
  0x1B: ("MasterSword", "sword"),
  0x1C: ("DarkEdge", "sword"),
  0x1D: ("MareetasBlade", "sword"),
  0x1E: ("BrokenSword", "sword"),
  0x1F: ("IronLance", "lance"),
  0x20: ("SteelLance", "lance"),
  0x21: ("SilverLance", "lance"),
  0x22: ("SlimLance", "lance"),
  0x23: ("PoisonSpear", "lance"),
  0x24: ("Wyrmlance", "lance"),
  0x25: ("DarkLance", "lance"),
  0x26: ("BraveLance", "lance"),
  0x27: ("ShortLance", "lance"),
  0x28: ("LongLance", "lance"),
  0x29: ("Greatlance", "lance"),
  0x2A: ("Javelin", "lance"),
  0x2B: ("MasterLance", "lance"),
  0x2C: ("Horseslayer", "lance"),
  0x2D: ("KillerLance", "lance"),
  0x2E: ("GaeBolg", "lance"),
  0x2F: ("Gungnir", "lance"),
  0x30: ("BrokenLance", "lance"),
  0x31: ("IronAxe", "axe"),
  0x32: ("PoisonAxe", "axe"),
  0x33: ("SteelAxe", "axe"),
  0x34: ("SilverAxe", "axe"),
  0x35: ("HandAxe", "axe"),
  0x36: ("Hammer", "axe"),
  0x37: ("KillerAxe", "axe"),
  0x38: ("Pugi", "axe"),
  0x39: ("BraveAxe", "axe"),
  0x3A: ("DevilAxe", "axe"),
  0x3B: ("BattleAxe", "axe"),
  0x3C: ("Halberd", "axe"),
  0x3D: ("MasterAxe", "axe"),
  0x3E: ("BrokenAxe", "axe"),
  0x3F: ("IronBow", "bow"),
  0x40: ("SteelBow", "bow"),
  0x41: ("SilverBow", "bow"),
  0x42: ("PoisonBow", "bow"),
  0x43: ("KillerBow", "bow"),
  0x44: ("BraveBow", "bow"),
  0x45: ("Shortbow", "bow"),
  0x46: ("Longbow", "bow"),
  0x47: ("Greatbow", "bow"),
  0x48: ("MasterBow", "bow"),
  0x49: ("Ballista", "ballista"),
  0x4A: ("IronBallista", "ballista"),
  0x4B: ("KillerBallista", "ballista"),
  0x4C: ("PoisonBallista", "ballista"),
  0x4D: ("BrokenBow", "bow"),
  0x68: ("Heal", "staff"),
  0x69: ("Mend", "staff"),
  0x6A: ("Recover", "staff"),
  0x6B: ("Physic", "staff"),
  0x6C: ("Fortify", "staff"),
  0x6D: ("Rescue", "staff"),
  0x6E: ("Warp", "staff"),
  0x6F: ("Restore", "staff"),
  0x70: ("SilenceStaff", "staff"),
  0x71: ("Sleep", "staff"),
  0x72: ("TorchStaff", "staff"),
  0x73: ("Return", "staff"),
  0x74: ("Hammerne", "staff"),
  0x75: ("ThiefStaff", "staff"),
  0x76: ("Watch", "staff"),
  0x77: ("Berserk", "staff"),
  0x78: ("Unlock", "staff"),
  0x79: ("Ward", "staff"),
  0x7A: ("Rewarp", "staff"),
  0x7B: ("Kia", "staff"),
  0x7C: ("DrainedStaff", "staff"),
  }


def main():

  _, ROMfile, outdir = sys.argv

  with open(ROMfile, "rb") as i:
    ROM = i.read()

  os.makedirs(outdir, exist_ok=True)

  # Fetch all of the weapons that share graphics.

  shared = {}
  for index, (name, template_name) in weapons.items():

    entry_offset = item_base_table + (2 * index)
    gfx, pal = read_byte(ROM, entry_offset), read_byte(ROM, entry_offset + 1)

    if not gfx in shared.keys():
      shared[gfx] = (name, template_name, [], [])

    _, _, shared_palettes, shared_palette_names = shared[gfx]

    if pal not in shared_palettes:
      shared_palettes.append(pal)

    shared_palette_names.append(name)

  out_txt = []

  for index, shared_info in shared.items():

    name, template_name, shared_palettes, shared_palette_names = shared_info

    gfx_offset = unlorom(read_long(ROM, image_pointer_table + (index * 3)))
    pal_offset = image_palettes + (shared_palettes[0] * 0x1E)

    palette = Palette.from_bytes(ROM, 15, pal_offset)
    palette.colors.insert(0, COLOR_0)

    raw, _ = decompress(ROM, gfx_offset)
    raw_im = rip_image(raw, (128, 16), palette, indexed_output=False)

    out_im = Image.new("RGB", template_sizes[template_name], TEMPLATE_BG.to_rgb())

    template = templates[template_name]
    for dest, size, source in template:
      out_im.paste(raw_im.crop(rect(source, size)), dest)

    x, y = palette_zones[template_name]
    for index, pal_index in enumerate(shared_palettes):
      pal_offset = image_palettes + (pal_index * 0x1E)

      palette = Palette.from_bytes(ROM, 15, pal_offset)
      palette.colors.insert(0, COLOR_0)

      pal_im = Image.new("RGB", (16, 1))
      pal_im.putdata(palette.to_list())

      out_im.paste(pal_im, (x, y+index))

    out_im.save(os.path.join(outdir, f"{name}.{template_name}.png"))

    # Output some nice info about shared graphics/palettes.

    out_txt.append(name)
    for shared_name in shared_palette_names:
      out_txt.append("  "+shared_name)

    out_txt.append("")

  out_txt_name = os.path.join(outdir, "Palettes.txt")
  with open(out_txt_name, "w") as o:
    o.write("\n".join(out_txt))


if __name__ == '__main__':
  main()
