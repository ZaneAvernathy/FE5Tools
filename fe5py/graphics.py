
from typing import ByteString, Optional, List, Literal, Sequence
from itertools import product, combinations
from PIL import Image
from copy import copy
from .memory import read_word


__all__ = [
  "Color", "Palette",
  "rect",
  "IndexedTile", "RGBTile",
  "rip_image",
  ]


class Color:
  """A single RGB555 color."""

  def __init__(self, value=0):
    if isinstance(value, int):
      self.color = value & 0x7FFF
    elif isinstance(value, Sequence):
      if len(value) != 3:
        raise ValueError(
          f"Length of {repr(value)} must be 3, got {len(value)}."
          )
      self.r, self.g, self.b = value
    elif isinstance(value, Color):
      self.r, self.g, self.b = value.r, value.g, value.b
    else:
      raise ValueError(f"Cannot make Color from object {repr(value)}")

  @property
  def color(self):
    _c = lambda band, shift: (band >> 3) << shift
    return _c(self.r, 0) | _c(self.g, 5) | _c(self.b, 10)

  @color.setter
  def color(self, value: int):
    _select = lambda s: ((value & (0b11111 << s)) >> s) << 3
    self.r, self.g, self.b = [_select(s) for s in range(0, 15, 5)]

  def __eq__(self, other):
    return (self.r == other.r) & (self.g == other.g) & (self.b == other.b)

  def __hash__(self):
    return hash((self.r, self.b, self.g))

  def __str__(self):
    return str(self.to_rgb())

  def __repr__(self):
    return f"Color({self.to_rgb()})"

  def to_bytes(self):
    """Converts the Color into native data."""
    return int.to_bytes(self.color, 2, "little")

  def to_rgb(self):
    """Converts the Color into an RGB tuple."""
    return (self.r, self.g, self.b)

  def to_hex(self):
    """Converts the Color into a string suitable for HTML."""
    return f"#{self.r:02x}{self.g:02x}{self.b:02x}"

  @classmethod
  def from_bytes(cls, data: ByteString, offset: int=0):
    """Creates a Color from native data."""
    return cls(read_word(data, offset))


class Palette:
  """A group of Colors."""

  def __init__(self, colors=[]):
    self.current = 0
    self.colors = [Color(c) for c in colors]

  def __eq__(self):
    return (self.colors == other.colors)

  def __hash__(self):
    return hash(self.colors)

  def __iter__(self):
    return self

  def __next__(self):
    try:
      result = self.colors[self.current]
    except IndexError:
      self.current = 0
      raise StopIteration
    self.current += 1
    return result

  def __getitem__(self, i: int):
    return self.colors[i]

  def __setitem__(self, i: int, c: Color):
    if not isinstance(c, Color):
      raise ValueError("Palette entries must be Colors.")
    self.colors[i] = c

  def __len__(self):
    return len(self.colors)

  def __str__(self):
    return str(self.colors)

  def __repr__(self):
    colors = ", ".join([repr(c) for c in self.colors])
    return f"Palette(colors=[{colors}])"

  def to_bytes(
      self,
      length: Optional[int] = None,
      fillcolor: Color = Color(),
      ) -> ByteString:
    """Converts the Palette into native data."""
    palette = _fit(self, length, fillcolor)
    return b"".join([color.to_bytes() for color in palette])

  def to_list(
      self,
      length: Optional[int] = None,
      fillcolor: Color = Color(),
      ) -> list:
    """Converts the Palette to a list of RGB tuples."""
    palette = _fit(self, length, fillcolor)
    return [color.to_rgb() for color in palette]

  def to_PIL_list(
      self,
      length: Optional[int] = None,
      fillcolor: Color = Color(),
      ) -> list:
    """Converts the Palette to a flat list for use with indexed PIL images."""
    palette = _fit(self, length, fillcolor)
    return [b for c in palette for b in c.to_rgb()]


  def requantize(self, length: int, fillcolor: Color=Color()) -> tuple:
    """
    Changes the size of a Palette to a certain length and
    returns a new Palette along with a dictionary of {original:new, ...}
    or None if no remapping occurred.
    If the new length is longer than the original palette,
    the new space is filled with a fillcolor.
    If the new length is less than the original palette, the most
    similar colors are averaged until the desired length is achieved.

    The first color (the transparent color) is never requantized.
    """
    if (length == len(self)):
      return (self, None)

    elif (length > len(self)):
      return (
        Palette(self.colors+[fillcolor for c in range(length-len(self))]),
        None,
        )

    elif (length == 1):
      return (Palette(self.colors[0:1]), None)

    colors, remapping = [c.to_rgb() for c in self.colors[1:]], {}
    while len(colors) > (length - 1):
      close1, close2 = _get_closest(colors)
      _avg = lambda c1, c2: (c1 + c2) // 2
      average = tuple([_avg(close1[i], close2[i]) for i in range(3)])

      colors[colors.index(close1)] = average
      colors.remove(close2)

      # Add replacement to remapping.
      remapping[close1] = average
      remapping[close2] = average

    # Flatten remapping such that
    # {original: new1, new1: new2} -> {original: new2}

    flat = {}
    for color in copy(self.colors)[1:]:
      color = color.to_rgb()
      if color in remapping.keys():
        new = remapping[color]
        while new in remapping.keys():
          new = remapping[new]
        flat[color] = new

    return (Palette(self.colors[0:1] + colors), flat)

  @classmethod
  def from_bytes(
      cls,
      data: ByteString,
      count: Optional[int] = None,
      offset: int = 0,
      ):
    """Creates a Palette from native data."""
    if count is None:
      count = len(data) // 2
    c_range = range(offset, offset+(count * 2), 2)
    return cls([Color.from_bytes(data, i)for i in c_range])

  @classmethod
  def from_image(cls, image: Image, maxlength: Optional[int]=None):
    """Creates a Palette from an image."""

    if (image.mode == "P"):
      p = image.getpalette()
      if maxlength is not None:
        p = p[:maxlength*3]
      return Palette([(p[i], p[i+1], p[i+2]) for i in range(0, len(p), 3)])

    elif (image.mode == "RGB"):
      p = []
      for c in image.getdata():
        if c not in p: p.append(c)
      if maxlength is not None:
        p = p[:maxlength]
      return Palette(p)

    else:
      raise ValueError(
        f"Unable to create Palette from image with mode {image.mode}."
        )


def _fit(
    palette: Palette,
    length: Optional[int] = None,
    fillcolor: Color = Color(),
    ) -> List[Color]:
  """Internal helper to pad or truncate Palettes."""
  p = copy(palette.colors)
  if length is None:
    length = len(p)
  if length > len(p):
    p.extend([fillcolor for c in range(length - len(p))])
  return p[:length]


def _get_closest(it: Sequence[tuple]) -> tuple:
  """Internal helper to find the closest two colors in a sequence."""
  c = list(combinations(it, 2))
  _diff = lambda l, r: abs(sum(l) - sum(r))
  closest = (c[0], _diff(c[0][0], c[0][1]))
  for combo in c:
    s = _diff(*combo)
    closest = (combo, s) if (s < closest[1]) else closest
  return closest[0]


def _flatten(it: Sequence[int | tuple | List[int | tuple]]):
  """Internal helper to flatten iterables."""
  isnested = any([isinstance(e, list) for e in it])
  it = [i for e in it for i in e] if isnested else it
  return it


def rect(pos: tuple, size: tuple) -> tuple:
  """Helper to make PIL rects."""
  x, y = pos
  w, h = size
  return (x, y, x+w, y+h)


TILEMODE = Literal[2, 4, 8, "rgb"]


class TileBase:
  """Base class for Tiles."""

  def __init__(
      self,
      mode: TILEMODE,
      data: Optional[Sequence[int | tuple | Sequence[int | tuple]]] = None,
      ):
    self.current = 0
    self.mode = mode

    if data is None:
      if mode in [2, 4, 8]:
        fill = 0
      elif mode == "rgb":
        fill = (0, 0, 0)
      else:
        raise ValueError(f"Unknown Tile mode {mode}.")
      data = [[fill for x in range(8)] for y in range(8)]

    if len(f := _flatten(data)) != 64:
      raise ValueError(
        f"Cannot create Tile from sequence of {len(f)}/64 elements."
        )
    self.data = f

  @property
  def rows(self):
    return [self.data[i:i+8] for i in range(0, 64, 8)]

  def __eq__(self, other):
    return (self.mode == other.mode) & (self.data == other.data)

  def __hash__(self):
    return hash((self.mode, self.data))

  def __len__(self):
    return 64

  def __iter__(self):
    return self

  def __next__(self):
    try:
      result = self.data[self.current]
    except IndexError:
      self.current = 0
      raise StopIteration
    self.current += 1
    return result

  def __getitem__(self, i):
    return self.data[i]

  def __setitem__(self, i, c):
    self.data[i] = c

  def __str__(self):
    return str(self.data)

  def __repr__(self):
    return f"{self.__class__.__name__}(mode={self.mode}, data={self.data})"


class IndexedTile(TileBase):
  """
  A native indexed tile. Pixel data is stored as palette indices.
  Possible bit depths: 2, 4, 8.
  """

  def __init__(
      self,
      mode: TILEMODE,
      data: Optional[Sequence[int | Sequence[int]]] = None,
      ):
    if mode not in [2, 4, 8]:
      raise ValueError(
        f"IndexedTile mode must be one of [2, 4, 8], not {mode}."
        )
    if (data is not None):
      f = _flatten(data)
      if not all([isinstance(c, int) for c in f]):
        raise ValueError("Pixel indices must be ints.")
      if (max(_flatten(data)) >= (m := (2 ** mode))):
        raise ValueError(f"Pixel indices must be 0-{m-1} for {mode}bpp Tiles.")
    super().__init__(mode, data)

  def __setitem__(self, i, c):
    if not isinstance(c, int):
      raise ValueError(f"Pixels must be ints for IndexedTiles, got {c}.")
    elif (c >= (m := (2 ** self.mode))):
      raise ValueError(
        f"Pixel indices must be 0-{m-1} for {self.mode}bpp Tiles, got {c}"
        )
    super().__setitem__(i, c)

  def convert(self, mode: TILEMODE, palette: Optional[Palette]=None):
    """
    Converts the Tile to the specified mode and returns the converted Tile.
    Returns a copy of itself if the requested mode matches the current one.
    """
    if self.mode == mode:
      return copy(self)

    # For indexed modes, don't do any processing.
    # If the conversion is a reduction in bit depth, this will fail if
    # the palette indices of the original tile are too large.
    elif mode in [2, 4, 8]:
      return IndexedTile(mode, copy(self.data))

    elif mode == "rgb":

      if palette is None:
        raise ValueError("Converting to an RGB Tile requires a palette.")

      return RGBTile([palette[c].to_rgb() for c in self])

    else:
      raise ValueError(f"Unknown mode {mode}.")

  def requantize(
      self,
      newmode: TILEMODE,
      oldpalette: Palette,
      newpalette: Palette,
      remapping: dict,
      ):
    """
    Swaps color values according to a dict {original: new}
    and returns a new tile.
    """
    pixels = copy(self.data)
    for (i, c) in enumerate(pixels):
      color = oldpalette[c].to_rgb()
      if color in remapping.keys():
        newcolor = remapping[color]
        newindex = list(newpalette).index(Color(newcolor))
        pixels[i] = newindex
      else:
        newindex = list(newpalette).index(Color(color))
        pixels[i] = newindex
    t = IndexedTile(self.mode, pixels)
    return t.convert(newmode, newpalette)

  def to_bytes(self):
    """Converts the Tile into native data."""
    bpp, rows = self.mode, self.rows

    # Representing bitplanes as strings of 0s and 1s
    # because it's easy to convert them into ints.
    planes = [""] * bpp
    for row in rows:
      for pixel in row:
        for plane in range(bpp):
          planes[plane] += str((pixel >> plane) & 0b1)

    # Flatten bits into bytes
    # plane0 [0, 1, 0, 1, 0, 1, 0, 1, ...] -> 55 ...
    # plane1 [0, 0, 1, 1, 0, 0, 1, 1, ...] -> 33 ...
    # ...
    for (p, plane) in enumerate(planes):
      planes[p] = [
        int(plane[i:i+8], 2).to_bytes(1, "little") for i in range(0, 64, 8)
        ]

    # Merge the planes into bytes.
    # 55 ... -> 55 33
    # 33 ... -^
    d = bytearray()
    for p in range(0, bpp, 2):
      for i in range(8):
        d += planes[p][i] + planes[p+1][i]

    return d

  def to_image(
      self,
      palette: Palette,
      mode: str="P",
      xflip: bool=False,
      yflip: bool=False,
      ) -> Image:
    """Creates a PIL image from a Tile. Available modes are 'P' or 'RGB'."""
    rows = self.rows
    if xflip:
      for row in rows: row.reverse()
    if yflip:
      rows.reverse()
    if (mode == "RGB"):
      data = [palette[c].to_rgb() for c in _flatten(rows)]
    else:
      data = _flatten(rows)
    im = Image.new(mode, (8, 8))
    im.putdata(data)
    if (mode == "P"):
      im.putpalette(palette.to_PIL_list())
    return im

  @classmethod
  def from_bytes(cls, mode: TILEMODE, data: ByteString, offset: int=0):
    """Creates a tile from native data."""

    if (l := len(data[offset:])) < (r := (mode * 8)):
      raise ValueError(f"Not enough data to build {mode}bpp tile: {l}/{r}.")

    # Each bitplane is 8 bytes,
    # plane bytes are interwoven into 16-byte groups:

    # p0 p1 p0 p1 p0 p1 p0 p1 p0 p1 p0 p1 p0 p1 p0 p1 | 2bpp \      \
    # p2 p3 p2 p3 p2 p3 p2 p3 p2 p3 p2 p3 p2 p3 p2 p3 |      / 4bpp  \
    # p4 p5 p4 p5 p4 p5 p4 p5 p4 p5 p4 p5 p4 p5 p4 p5 |              /
    # p6 p7 p6 p7 p6 p7 p6 p7 p6 p7 p6 p7 p6 p7 p6 p7 |             / 8bpp

    # Each byte contains a single bit from each of the
    # row's pixels, with the MSB belonging to the leftmost
    # pixel, LSB to the rightmost.

    indexes = [[0 for x in range(8)] for y in range(8)]
    for plane in range(mode):
      # Get every other byte.
      p_start = ((plane // 2) * 16) + offset
      plane_bytes = data[p_start + (plane % 2):p_start + 16:2]
      for (y, x) in product(range(8), range(8)):
        # 7 - x to fetch the MSB first.
        # Add a bit every time we go through the plane.
        bit = (plane_bytes[y] >> (7 - x)) & 0b1
        indexes[y][x] += (bit << plane)

    return cls(mode, indexes)

  @classmethod
  def from_image(
      cls,
      mode: TILEMODE,
      image: Image,
      palette: Optional[Palette] = None,
      pos: tuple = (0, 0),
      ):
    """Creates a tile from a PIL image."""

    crop = image.crop(rect(pos, (8, 8)))

    if (image.mode == "RGB"):
      if palette is None:
        raise ValueError(
          "A palette is required to make an IndexedTile from an RGB image."
          )
      data = [list(palette).index(Color(c)) for c in list(crop.getdata())]

    elif (image.mode == "P"):
      data = list(crop.getdata())

    else:
      raise ValueError(f"Image must be mode 'P' or 'RGB', got {image.mode}.")

    return cls(mode, data)


class RGBTile(TileBase):
  """
  An RGB tile. Pixel indices are stored as RGB tuples.
  """

  def __init__(
      self,
      data: Optional[Sequence[tuple | Sequence[tuple]]] = None,
      ):
    if (data is not None):
      f = _flatten(data)
      if not all([isinstance(c, tuple) for c in f]):
        raise ValueError("Pixel values must be tuples.")
    super().__init__("rgb", data)

  def __setitem__(self, i, c):
    # Allow pixels to be assigned Colors,
    # silently convert them into RGB tuples.
    if isinstance(c, Color):
      c = c.to_rgb()
    elif not isinstance(c, tuple):
      raise ValueError(f"Pixels must be RGB tuples for RGBTiles, got {c}.")
    super().__setitem__(i, c)

  def convert(self, mode: TILEMODE, palette: Optional[Palette]=None):
    """
    Converts the Tile to the specified mode and returns the converted Tile.
    Returns itself if the requested mode matches the current one.
    """
    if self.mode == mode:
      return copy(self)

    elif mode in [2, 4, 8]:

      if palette is None:
        raise ValueError("Converting to an indexed Tile requires a palette.")

      return IndexedTile(mode, [list(palette).index(Color(c)) for c in self])

    else:
      raise ValueError(f"Unknown mode {mode}.")

  def requantize(self, newmode: TILEMODE, newpalette: Palette, remapping: dict):
    """
    Swaps color values according to a dict {original: new}
    and returns a new tile.
    """
    pixels = copy(self.data)
    for (i, color) in enumerate(pixels):
      if color in remapping.keys():
        newcolor = remapping[color]
        pixels[i] = newcolor
    t = IndexedTile(self.mode, pixels)
    return t.convert(newmode, newpalette)

  def to_image(self, xflip: bool=False, yflip: bool=False) -> Image:
    """Creates an RGB PIL image from a Tile."""
    rows = self.rows
    if xflip:
      for row in rows: row.reverse()
    if yflip:
      rows.reverse()
    im = Image.new("RGB", (8, 8))
    im.putdata(_flatten(rows))
    return im

  @classmethod
  def from_bytes(
      cls,
      mode: TILEMODE,
      data: ByteString,
      palette: Palette,
      offset: int = 0,
      ):
    """
    Creates a tile from native data.
    The requested mode determines the size of the native data.
    """
    t = IndexedTile.from_bytes(mode, data, offset)
    return cls([palette[c].to_rgb() for c in t])

  @classmethod
  def from_image(
      cls,
      image: Image,
      palette: Optional[Palette] = None,
      pos: tuple = (0, 0),
      ):
    """Creates a tile from a PIL image."""

    crop = image.crop(rect(pos, (8, 8)))

    if (image.mode == "P"):
      if palette is None:
        raise ValueError(
          "A palette is required to make an RGBTile from an indexed image."
          )
      data = [palette[c].to_rgb() for c in list(crop.getdata())]

    elif (image.mode == "RGB"):
      data = list(crop.getdata())

    else:
      raise ValueError(f"Image must be mode 'P' or 'RGB', got {image.mode}.")

    return cls(data)


def rip_image(
    data: ByteString,
    size: tuple,
    palette: Palette,
    offset: int = 0,
    mode: TILEMODE = 4,
    indexed_output = True,
    ):
  """Rips an image from binary data."""

  if mode == "rgb":
    raise ValueError("Mode must be one of [2, 4, 8].")

  im_mode = "P" if indexed_output else "RGB"
  im = Image.new(im_mode, size)

  if im_mode == "P":
    im.putpalette(palette.to_PIL_list())

  w, h = size
  for (i, (y, x)) in enumerate(product(range(0, h, 8), range(0, w, 8))):
    pos = offset + (i * (mode * 8))
    t = IndexedTile.from_bytes(mode, data, pos)
    if not indexed_output:
      t = t.convert("rgb", palette)
      im.paste(t.to_image(), (x, y))
    else:
      im.paste(t.to_image(palette, im_mode), (x, y))

  return im


