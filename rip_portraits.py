#!/usr/bin/python3

import os
import sys
from PIL import Image
from fe5py.graphics import Palette, rip_image, rect
from fe5py.memory import unlorom
from fe5py.decompress import decompress

portraits = {
  0xEADE80: ("Leif", [0x00]),
  0xEAE3B9: ("Finn", [0x01]),
  0xEAE8B7: ("Nanna", [0x02]),
  0xEAEE23: ("Hannibal", [0x03]),
  0xEAF322: ("Julius", [0x04]),
  0xEAF8A6: ("Ishtar", [0x05]),
  0xEAFE34: ("Arion", [0x06]),
  0xEB8318: ("Travant", [0x07]),
  0xEB8851: ("Cairpre", [0x08]),
  0xEB8C84: ("Seliph", [0x09]),
  0xEB91DE: ("LeifAngry", [0x0A]),
  0xEB9717: ("Dermott", [0x0B]),
  0xEB9BD9: ("Daisy", [0x0C]),
  0xEBA119: ("Asaello", [0x0D]),
  0xEBA613: ("Lewyn", [0x0E]),
  0xEBAB36: ("Julia", [0x0F]),
  0xEBB048: ("Lara", [0x10]),
  0xEBB605: ("Miranda", [0x11]),
  0xEBBADC: ("Ronan", [0x12]),
  0xEBBFB5: ("Orsin", [0x13]),
  0xEBC4CE: ("Halvan", [0x14]),
  0xEBC9DC: ("Dagdar", [0x15, 0xEE]),
  0xEBCF30: ("Ralph", [0x16]),
  0xEBD3D2: ("Eyvel", [0x17, 0xED]),
  0xEBD981: ("Marty", [0x18]),
  0xEBDE20: ("Galzus", [0x19, 0xF1]),
  0xEBE3F9: ("Alba", [0x1A]),
  0xEBE928: ("Leonsterite4", [0x1B]),
  0xEBEE1D: ("Selphina", [0x1C]),
  0xEBF2FF: ("Hicks", [0x1D]),
  0xEBF862: ("Dahlson", [0x1E]),
  0xEBFD2F: ("Olwen", [0x1F]),
  0xEC8209: ("Pan", [0x20]),
  0xEC8729: ("Callion", [0x21]),
  0xEC8C0D: ("Mareeta", [0x22]),
  0xEC95D7: ("Asvel", [0x24]),
  0xEC9AB8: ("Matria", [0x25]),
  0xEC9F78: ("Sapphie", [0x26]),
  0xECA4EE: ("Mischa", [0x27]),
  0xECAA94: ("Salem", [0x28]),
  0xECAFB9: ("Schroff", [0x29]),
  0xECB499: ("Fergus", [0x2A]),
  0xECB9C0: ("Brighton", [0x2B]),
  0xECBE8D: ("Sarah", [0x2C, 0xEF]),
  0xECC30D: ("Tanya", [0x2D]),
  0xECC815: ("Trude", [0x2E]),
  0xECCCDA: ("Shanam", [0x2F]),
  0xECD24C: ("Tina", [0x30]),
  0xECD78C: ("Linoan", [0x31]),
  0xECDC66: ("Saias", [0x32]),
  0xECE173: ("Amalda", [0x33]),
  0xECE62B: ("Eda", [0x34]),
  0xECEB79: ("Reinhardt", [0x35]),
  0xECF0A4: ("Gunter", [0x36]),
  0xECF4EA: ("Fred", [0x37]),
  0xECF9CB: ("Kane", [0x38]),
  0xECFE67: ("Robert", [0x39]),
  0xED8356: ("Karin", [0x3A]),
  0xED885F: ("Dean", [0x3B]),
  0xED8DD2: ("Lithis", [0x3C, 0xF0]),
  0xED930E: ("Ced", [0x3D]),
  0xED9854: ("Altena", [0x3E]),
  0xED9D9B: ("Homer", [0x3F]),
  0xEDA2CB: ("Arthur", [0x40]),
  0xEDA84E: ("Jean", [0x41]),
  0xEDAD56: ("Leonsterite1", [0x42]),
  0xEDB266: ("Ilios", [0x43]),
  0xEDB735: ("Leonsterite3", [0x44]),
  0xEDBBDE: ("Xavier", [0x50]),
  0xEDC098: ("Zaumm", [0x51, 0xC0, 0xC1]),
  0xEDC56B: ("Gustav", [0x52]),
  0xEDC9FC: ("Dorias", [0x53]),
  0xEDCEA0: ("Lobos", [0x54, 0xC2, 0xC3]),
  0xEDD314: ("Glade", [0x55]),
  0xEDD7B0: ("Dvorak", [0x56]),
  0xEDDC05: ("Eichmann", [0x57]),
  0xEDE09F: ("Farden", [0x58]),
  0xEDE4DA: ("August", [0x59]),
  0xEDE988: ("Weissman", [0x5A, 0xC9, 0xCA, 0xCB]),
  0xEDED87: ("Leonsterite5", [0x5B, 0xC4, 0xC5, 0xC6]),
  0xEDF246: ("Hortefeux", [0x5C, 0xC7, 0xC8]),
  0xEDF6BA: ("Codha", [0x5D, 0xCC, 0xCD, 0xCE]),
  0xEDFBE9: ("Leonsterite6", [0x5E, 0xCF, 0xD0, 0xD1]),
  0xEE8071: ("Leonsterite7", [0x5F, 0xD2, 0xD3, 0xD4]),
  0xEE84E4: ("Jabal", [0x60]),
  0xEE89F5: ("Zaille", [0x61]),
  0xEE8ED4: ("Kolkho", [0x62]),
  0xEE9378: ("Gomer", [0x63]),
  0xEE9840: ("Bakst", [0x64]),
  0xEE9D0E: ("Shiva", [0x65]),
  0xEEA236: ("Raydrik", [0x66, 0xF2]),
  0xEEA74E: ("Largo", [0x67, 0xD5, 0xD6]),
  0xEEAC11: ("Blume", [0x68]),
  0xEEB0AB: ("Manfroy", [0x69]),
  0xEEB5B3: ("Barath", [0x6A]),
  0xEEBA8A: ("Conomore", [0x6B]),
  0xEEBF63: ("Kempf", [0x6C]),
  0xEEC477: ("Veld", [0x6D]),
  0xEEC97A: ("Shopkeeper", [0x70]),
  0xEECDC7: ("Arena", [0x71]),
  0xEED20C: ("Man1", [0x72, 0xD7, 0xD8, 0xD9, 0xDA]),
  0xEED6A3: ("Man6", [0x73]),
  0xEEDB4B: ("Anna", [0x74]),
  0xEEE104: ("Woman1", [0x75]),
  0xEEE595: ("Man7", [0x76]),
  0xEEE986: ("Woman2", [0x77]),
  0xEEEE9B: ("Girl1", [0x78]),
  0xEEF32A: ("Man8", [0x79]),
  0xEEF712: ("Girl2", [0x7A, 0xE5, 0xE6, 0xE7, 0xE8]),
  0xEEFC0A: ("Boy1", [0x7B]),
  0xEF8019: ("Man9", [0x7C]),
  0xEF8470: ("Woman3", [0x7D]),
  0xEF88E7: ("Girl7", [0x7E]),
  0xEF8D9C: ("Boy2", [0x7F]),
  0xEF91AA: ("Man10", [0x80]),
  0xEF95C0: ("Man11", [0x81]),
  0xEF99BC: ("Man12", [0x82]),
  0xEF9DCD: ("Knight", [0x90, 0x91, 0x92, 0x93]),
  0xEFA1F5: ("BowKnight", [0x90, 0x92, 0x94]),
  0xEFA64C: ("AxeKnight", [0x90, 0xB0]),
  0xEFAA5D: ("MagicKnight", [0x90, 0x95]),
  0xEFAEBF: ("PegasusKnight", [0x93, 0xB4]),
  0xEFB317: ("WyvernKnight", [0x98, 0x99]),
  0xEFB75D: ("Archer", [0x9A, 0x9B, 0xA3, 0xB2]),
  0xEFBB1D: ("Myrmidon", [0x9A, 0x9B, 0x9D, 0x9E]),
  0xEFBF16: ("General", [0x9C, 0x9D]),
  0xEFC3DD: ("Soldier", [0xB2]),
  0xEFC7D1: ("Fighter", [0x9B]),
  0xEFCB8F: ("Armor", [0x9F, 0xA0, 0xA1, 0xA2]),
  0xEFCFD4: ("Brigand", [0x9A, 0xA3, 0xA5, 0xB1]),
  0xEFD3A1: ("MagicSword", [0xA6]),
  0xEFD772: ("Priest", [0xAB, 0xAC, 0xAD]),
  0xEFDC2E: ("Mage", [0xA8, 0xA9, 0xAA, 0xAB, 0xAC, 0xAD]),
  0xEFE053: ("Priestess", [0xAE]),
  0xEFE47D: ("Ballistician", [0xA0, 0xA2, 0xB3, 0xB8]),
  0xEFE801: ("Thief", [0xA6, 0xB6]),
  0xEFEBDE: ("HighPriest", [0xB7]),
  0xEFEF61: ("Dancer", [0xB9]),
  }


raw_template = [
  (( 0, 0), (48, 32)),
  ((48, 0), (80, 32)),
  ]


formatted_template = [
  ((0,  0), (48, 32)),
  ((0, 32), (80, 32)),
  ]


def rip_palette(index, ROM):
  offset = 0x354000 + (index * 0x20)
  return Palette.from_bytes(ROM, 16, offset)



def main():

  _, ROMfile, destdir = sys.argv

  with open(ROMfile, "rb") as i:
    ROM = i.read()

  os.makedirs(destdir, exist_ok=True)

  for (graphics_pointer, (name, palette_indices)) in portraits.items():

    palettes = [rip_palette(p, ROM) for p in palette_indices]

    raw, _ = decompress(ROM, unlorom(graphics_pointer), bytearray())
    raw_im = rip_image(raw, (128, 32), palettes[0], indexed_output=False)

    formatted_im = Image.new("RGB", (80, 64), palettes[0][0].to_rgb())

    for (r_pos, r_size), (f_pos, f_size) in zip(raw_template, formatted_template):
      formatted_im.paste(raw_im.crop(rect(r_pos, r_size)), rect(f_pos, f_size))

    for (p_index, palette) in enumerate(palettes):
      p_im = Image.new("RGB", (16, 1))
      p_im.putdata(palette.to_list())

      formatted_im.paste(p_im, (48, p_index))

    formatted_im.save(os.path.join(destdir, name+".png"))


if __name__ == '__main__':
  main()
