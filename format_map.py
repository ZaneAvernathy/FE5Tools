#!/usr/bin/python3

import sys
from pathlib import Path
from string import ascii_letters, digits
from itertools import product
import tmx

id_chars = ascii_letters + digits + "_"

missing_map_error = "Error: Unable to open file '{name}'."
duplicate_main_error = "Error: More than one tile layer named 'Main' in '{name}'."
invalid_layer_error = "Error: Invalid layer type for layer '{name}' in '{file}'."
bad_change_error = "Error: Bad tile change in layer '{name}' in '{file}'.\n" \
                   "Tile changes must be contiguous rectangles."

def throw(error: str, **error_info) -> None:
  """Throw an error message and exit."""
  sys.exit(error.format_map(error_info))


def mangle(s: str) -> str:
  """Converts a string into a 64tass-acceptable identifier."""
  return "".join([c for c in s if c in id_chars]).lstrip(digits+"_")


def word(i: int) -> bytes:
  """Shorthand to convert a number into data."""
  return i.to_bytes(2, "little")


def conv(t: tmx.LayerTile) -> int:
  """Converts a Tiled tile into an FE5 metatile index."""
  return ((t.gid - 1) * 8) if (t.gid != 0) else None

def main() -> None:
  """
  Reads FE5 maps made with Tiled.

  Maps should be orthogonal, non-infinite, and have 16x16 pixel tiles.
  They should have a single tileset image that is 512x512 pixels.

  A map must have exactly one tile layer that has the name `Main`.
  This layer must not have any blank tiles.

  Additional tile layers will be treated as tile changes, and should only 
  have tiles covering a rectangular area of the map that they replace
  when triggered.
  """

  infile = Path(sys.argv[1]).resolve()
  if not infile.is_file():
    throw(missing_map_error, name=infile)

  tilemap = tmx.TileMap.load(infile)

  change_count = 0
  change_lines = ["\n"]
  change_def_data, change_tile_data = bytearray(), bytearray()
  change_header_size = 6 * (len(tilemap.layers_list) - 1)

  main_layer, mainfile = False, None
  for layer in tilemap.layers_list:

    name = mangle(layer.name.replace(" ", "_"))

    if name.lower() == "main":

      # More than one main layer is not allowed.

      if main_layer: throw(duplicate_main_error, name=infile)

      # The main layer must be a tile layer.

      if not isinstance(layer, tmx.Layer):
        throw(invalid_layer_error, name=layer.name, file=infile)

      main_layer = True

      main_data = bytearray().join([word(d) for d in [tilemap.width, tilemap.height]])
      main_data += b"".join([word(conv(tile)) for tile in layer.tiles])

    elif isinstance(layer, tmx.Layer):

      # Map change layers

      # We're going to do some checking to make sure that map changes
      # are contiguous and rectangular.

      row_starts = range(0, layer.width * layer.height, layer.width)
      rows = [[conv(tile) for tile in layer.tiles[s:s+layer.width]] for s in row_starts]

      change_tiles = []
      first_row, last_row = None, None
      first_tile, last_tile = None, None
      for y, row in enumerate(rows):
        for x, t in enumerate(row):

          if t is not None:

            change_tiles.append(t)

            first_row = y if not first_row else first_row
            last_row  = y if (not last_row) or (y >= last_row) else first_row

            first_tile = x if not first_tile else first_tile
            last_tile  = x if (not last_tile) or (x >= last_tile) else first_tile

      if (first_tile and first_row):

        width  = (last_tile - first_tile + 1)
        height = (last_row - first_row + 1)

        # Now that we have the parts we need, we can check to make sure
        # the region is rectangular.

        isrect = all([
            rows[y][x] is not None
            for y, x in product(
               range(first_row, last_row+1),
               range(first_tile, last_tile+1),
              )
          ])

        if not isrect:
          throw(bad_change_error, name=layer.name, file=infile)

        header = 2 + len(change_tile_data) + change_header_size
        change_def_data.extend(word(header))
        change_def_data.extend([first_tile, first_row, width, height])

        change_tile_data.extend(b"".join([word(tile) for tile in change_tiles]))

        fname = mangle(infile.stem.split()[0])
        change_lines.extend(f"{fname}Change_{mangle(layer.name)} = {change_count:0d}\n")
        change_count += 1

  mainfile = infile.with_name(infile.stem + "MapMain.bin")
  mainfile.write_bytes(main_data)

  if (change_count > 0):

    c = b"".join([word(change_count - 1), change_def_data, change_tile_data])
    changefile = infile.with_name(infile.stem + "MapChanges.bin")
    changefile.write_bytes(c)

    changetext = infile.with_name(infile.stem + "MapChanges.asm")
    changetext.write_text("".join(change_lines))


if __name__ == '__main__':
  main()
