#!/usr/bin/python3


import argparse
from fe5py.maps import MapTileset


def main():

  parser = argparse.ArgumentParser(
    description = "Creates, updates, or exports tilesets as Tiled .tmx files.",
    )
  parser.add_argument(
    "mode",
    choices = ["create", "update", "export"],
    )
  parser.add_argument(
    "filepath",
    help = "path to a .tmx file",
    )
  parser.add_argument(
    "index",
    help = "optional tiles image index",
    nargs = "?",
    default = None,
    )

  args = parser.parse_args()

  if (i := args.index) is not None:
    args.index = int(i, 16 if i.startswith("0x") else 10)

  match args.mode:
    case "create":
      MapTileset.create(args.filepath, args.index)

    case "update":
      MapTileset.update_images(args.filepath, args.index)

    case "export":
      ts = MapTileset.from_tmxfile(args.filepath)
      ts.to_bytes(args.filepath)


if __name__ == '__main__':
  main()
