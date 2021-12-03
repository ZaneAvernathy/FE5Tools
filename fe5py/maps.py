
import os
from typing import Optional, ByteString
from PIL import Image
from itertools import product
import tmx
from .memory import read_byte, read_word
from .graphics import Color, Palette, IndexedTile, rect


terrain_types = {
  0x00: "Map Edge",
  0x01: "Peak",
  0x02: "Thicket",
  0x03: "Cliff",
  0x04: "Plains",
  0x05: "Forest",
  0x06: "Sea",
  0x07: "River",
  0x08: "Mountain",
  0x09: "Sand ('Sandy Land')",
  0x0A: "Castle",
  0x0B: "Fort",
  0x0C: "House",
  0x0D: "Gate",
  0x0E: "--",
  0x0F: "Wasteland",
  0x10: "Bridge",
  0x11: "Lake",
  0x12: "Village",
  0x13: "Ruins",
  0x14: "Warehouse?",
  0x16: "Supply",
  0x17: "Church",
  0x18: "House",
  0x19: "Road",
  0x1A: "Armory",
  0x1B: "Vendor",
  0x1C: "Arena",
  0x1D: "Floor",
  0x1F: "Throne",
  0x20: "Door",
  0x21: "Chest",
  0x22: "Exit",
  0x23: "Pillar",
  0x24: "Drawbridge",
  0x25: "Secret Shop",
  0x27: "Sand ('Sandy Soil')",
  0x28: "Floor (Magic)",
  0x29: "Floor (Magic)",
  0x2A: "Church",
  0x2B: "Chest",
  }


class MapTileset:

  """An FE5 tileset for use with Tiled maps."""

  def __init__(
      self,
      name: str = "",
      tiles: Optional[list] = None,
      config: Optional[list] = None,
      terrains: Optional[list] = None,
      palette: Optional[list] = None,
      ):

    self.name = name
    self.tiles = tiles if tiles else []
    self.config = config if config else []
    self.terrains = terrains if terrains else []
    self.palette = palette if palette else []

  @staticmethod
  def from_tmxfile(filename):
    """Creates a MapTileset from a formatted TMX file."""

    name = os.path.splitext(os.path.basename(filename))[0]

    tmxfile = tmx.TileMap.load(filename)

    if (l := len(tmxfile.tilesets)) != 8:
      raise ValueError(
        f"Unexpected number of palette images: expected 8, got {l:d}."
        )

    palette = []
    for palette_tiles in tmxfile.tilesets:

      p_im = Image.open(palette_tiles.image.source)

      if p_im.mode != "P":
        raise ValueError(
          f"Palette image {palette_tiles.image.source} must be an indexed image."
          )

      pal = Palette.from_image(p_im, 16)
      palette.append(pal)

    # We use image 3 because 0-2 are unused.
    t_im = Image.open(tmxfile.tilesets[3].image.source)

    tiles = []
    for (y, x) in product(range(0, 320, 8), range(0, 128, 8)):
      tiles.append(IndexedTile.from_image(4, t_im, pos=(x, y)))

    config, terrains = [], []
    for layer in tmxfile.layers:

      if isinstance(layer, tmx.Layer):
        config = layer.tiles

      elif isinstance(layer, tmx.ObjectGroup):
        terrains = layer.objects

    return MapTileset(name, tiles, config, terrains, palette)

  @staticmethod
  def from_bytes(
      name: str,
      tiledata: ByteString,
      configdata: ByteString,
      palettedata: ByteString,
      ):
    """Creates a MapTileset from native data."""

    tiles = [
      IndexedTile.from_bytes(4, tiledata, offset)
      for offset in range(0, (16 * 40) * 32, 32)
      ]

    tilemap = [[tmx.LayerTile(0) for x in range(64)] for y in range(64)]

    terrains = []
    for (entry, (y, x)) in enumerate(product(range(32), repeat=2)):
      offset = entry * 8
      metatile = [
        read_word(configdata, i)
        for i in range(offset, offset + 8, 2)
        ]

      for (tile, (m_x, m_y)) in zip(metatile, product(range(2), repeat=2)):
        # Each palette image has 640 tiles, Tiled treats
        # tile indices from later images as coming after
        # the previous image's.
        t_index = (tile & 0x3FF) - 0x80
        t_pal = (tile >> 10) & 0x7

        index = 1 + (640 * t_pal) + t_index

        xflip = True if ((tile & 0x4000) != 0) else False
        yflip = True if ((tile & 0x8000) != 0) else False

        t_x, t_y = (x * 2) + m_x, (y * 2) + m_y

        tilemap[t_y][t_x] = tmx.LayerTile(index, xflip, yflip)

      # While we're looping like this, snag the metatile's terrain data

      offset = entry + 0x2000
      terrain = read_byte(configdata, offset)
      tagname = terrain_types.get(terrain, "")

      tag = f"0x{terrain:02X} {tagname}" if tagname else f"0x{terrain:02X}"
      terrains.append(tmx.Object("", tag, x * 16, y * 16, 16, 16,))

    palette = [
      Palette.from_bytes(palettedata, 16, offset)
      for offset in range(0, 32 * 8, 32)
      ]

    config = [t for r in tilemap for t in r]

    return MapTileset(name, tiles, config, terrains, palette)

  @staticmethod
  def update_images(name: str, index: Optional[int]=None):
    """
    Updates all tile images in a .tmx MapTileset. The optional parameter
    `index` specifies which image has been updated last. If not specified,
    uses the last-modified time for each file to determine the most recent.
    """

    ts = tmx.TileMap.load(name)
    images = [im.image.source for im in ts.tilesets]

    if index is None:

      times = [os.stat(f).st_mtime for f in images]
      index = times.index(max(times))

    tilesimage = Image.open(images[index])

    for image in images:
      im = Image.open(image)
      im.putdata(tilesimage.getdata())
      im.save(image)

    ts = MapTileset.from_tmxfile(name)
    dirname, basename = os.path.split(name)
    basename = os.path.splitext(basename)[0]
    im = ts.to_image()
    im.save(os.path.join(dirname, basename+".png"))

  @staticmethod
  def create(name: str, index: Optional[int]=None):
    """
    Creates a new .tmx MapTileset. If `index` is specified, initialize
    using a tiles image with that index.
    """

    dirname, basename = os.path.split(name)
    basename = os.path.splitext(basename)[0]

    tiles = [IndexedTile(4) for i in range(640)]
    palette = [Palette([Color() for c in range(16)]) for p in range(8)]

    if index is not None:

      tiles_im = Image.open(os.path.join(dirname, basename+f"_{index:d}.png"))
      tiles_palette = Palette.from_image(tiles_im, 16)

      tiles = []
      for (y, x) in product(range(0, 320, 8), range(0, 128, 8)):
        tiles.append(IndexedTile.from_image(4, tiles_im, tiles_palette, (x, y)))

      palette[index] = tiles_palette

    config = [tmx.LayerTile(1) for x in range(64) for y in range(64)]

    terrains = []
    for (y, x) in product(range(32), repeat=2):

      terrain = 0x00
      tagname = terrain_types.get(terrain, "")

      tag = f"0x{terrain:02X} {tagname}" if tagname else f"0x{terrain:02X}"
      terrains.append(tmx.Object("", tag, x * 16, y * 16, 16, 16))

    ts = MapTileset(basename, tiles, config, terrains, palette)
    ts.to_tmx(os.path.join(dirname, basename+".tmx"))

  def to_image(self) -> Image:
    """Returns the MapTileset as an image usable as a Tiled tileset."""

    im = Image.new("RGB", (512, 512))

    for (i, (y, x)) in enumerate(product(range(0, 512, 8), repeat=2)):
      tile = self.config[i]
      pal, index = divmod((tile.gid - 1), 640)
      t = self.tiles[index]
      t_im = t.to_image(self.palette[pal], "RGB", tile.hflip, tile.vflip)
      im.paste(t_im, (x, y))

    return im

  def to_tmx(self, name: str):
    """Saves the MapTileset as a .tmx file."""

    dirname, basename = os.path.split(name)
    basename = os.path.splitext(basename)[0]

    os.makedirs(dirname, exist_ok=True)

    tilesets = []
    for (pal_index, palette) in enumerate(self.palette):
      im = Image.new("P", (128, 320))
      im.putpalette(palette.to_PIL_list())

      for (i, (y, x)) in enumerate(product(range(0, 320, 8), range(0, 128, 8))):
        t = self.tiles[i]
        t_im = t.to_image(palette, "P")
        im.paste(t_im, (x, y))

      im_name = f"{basename}_{pal_index:01d}.png"
      im_name_full = os.path.join(dirname, im_name)

      im.save(im_name_full)

      ts_im = tmx.Image(source=im_name_full, width=128, height=320)

      ts = tmx.Tileset(
        1 + (640 * pal_index),
        im_name,
        8, 8,
        tilecount = 640,
        columns = 16,
        image = ts_im,
        )

      ts.animation = None
      tilesets.append(ts)

    mapfile = tmx.TileMap()

    mapfile.tilesets = tilesets
    mapfile.width, mapfile.height = (64, 64)
    mapfile.tilewidth, mapfile.tileheight = (8, 8)

    mapfile.layers = [
      tmx.Layer("Main", tiles=self.config, width=64, height=64),
      tmx.ObjectGroup("Terrains", objects=self.terrains),
      ]

    mapfile.save(
      os.path.join(dirname, basename+".tmx"),
      data_encoding = "csv",
      data_compression = False,
      )

    im = self.to_image()
    im.save(os.path.join(dirname, basename+".png"))

  def to_bytes(self, name: str):
    """Saves the MapTileset as native data."""

    dirname, basename = os.path.split(name)
    basename = os.path.splitext(basename)[0]

    os.makedirs(dirname, exist_ok=True)

    config, terrains = bytearray(), bytearray()

    for (meta_y, meta_x) in product(range(32), repeat=2):
      for (sub_x, sub_y) in product(range(2), repeat=2):
        e_x, e_y = (meta_x * 2) + sub_x, (meta_y * 2) + sub_y
        entry = self.config[(e_y * 64) + e_x]

        pal, index = divmod(entry.gid - 1, 640)
        index += 0x80
        index |= (pal << 10)
        index |= (entry.hflip << 14)
        index |= (entry.vflip << 15)

        config.extend(int.to_bytes(index, 2, "little"))

      # To get the terrain type, parse the terrain object's
      # text to get an int.

      entry = self.terrains[(meta_y * 32) + meta_x].type
      entry = entry.lstrip().split()[0]

      if entry.startswith("0x"):
        val = int(entry, 16)

      else:
        val = int(entry)

      terrains.extend(int.to_bytes(val, 1, "little"))

    config += terrains

    tiles = b"".join([tile.to_bytes() for tile in self.tiles])

    palette = b"".join([pal.to_bytes(16) for pal in self.palette])

    with open(os.path.join(dirname, basename+"Config.bin"), "wb") as o:
      o.write(config)

    with open(os.path.join(dirname, basename+"Tiles.bin"), "wb") as o:
      o.write(tiles)

    with open(os.path.join(dirname, basename+"Palette.bin"), "wb") as o:
      o.write(palette)

    im = self.to_image()
    im.save(os.path.join(dirname, basename+".png"))




