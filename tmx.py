# Simple TMX library
# Copyright (c) 2014-2016 Julie Marchant <onpon4@riseup.net>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This library reads and writes the Tiled TMX format in a simple way.
This is useful for map editors or generic level editors, and it's also
useful for using a map editor or generic level editor like Tiled to edit
your game's levels.

To load a TMX file, use :meth:`tmx.TileMap.load`.  You can then read the
attributes of the returned :class:`tmx.TileMap` object, modify the
attributes to your liking, and save your changes with
:meth:`tmx.TileMap.save`.  That's it!  Simple, isn't it?

At the request of the developer of Tiled, this documentation does not
explain in detail what each attribute means. For that, please see the
TMX format specification, found here:

http://doc.mapeditor.org/en/latest/reference/tmx-map-format/
"""

from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals


__version__ = "1.10a0"


import os
import xml.etree.ElementTree as ET
import base64
import gzip
import zlib
import warnings
import pathlib

import six


__all__ = ["TileMap", "Color", "Image", "Text", "ImageLayer", "Layer",
           "LayerTile", "Object", "ObjectGroup", "GroupLayer", "Property",
           "TerrainType", "Tile", "Tileset", "Frame", "data_decode",
           "data_encode"]


class TileMap(object):

    """
    This class loads, stores, and saves TMX files.

    .. attribute:: version

       The TMX format version.

    .. attribute:: orientation

       Map orientation.  Can be "orthogonal", "isometric", "staggered",
       or "hexagonal".

    .. attribute:: renderorder

       The order in which tiles are rendered.  Can be ``"right-down"``,
       ``"right-up"``, ``"left-down"``, or ``"left-up"``.  Default is
       ``"right-down"``.

    .. attribute:: width

       The width of the map in tiles.

    .. attribute:: height

       The height of the map in tiles.

    .. attribute:: tilewidth

       The width of a tile.

    .. attribute:: tileheight

       The height of a tile.

    .. attribute:: staggeraxis

       Determines which axis is staggered.  Can be "x" or "y".  Set to
       :const:`None` to not set it.  Only meaningful for staggered and
       hexagonal maps.

    .. attribute:: staggerindex

       Determines what indexes along the staggered axis are shifted.
       Can be "even" or "odd".  Set to :const:`None` to not set it.
       Only meaningful for staggered and hexagonal maps.

    .. attribute:: hexsidelength

       Side length of the hexagon in hexagonal tiles.  Set to
       :const:`None` to not set it.  Only meaningful for hexagonal maps.

    .. attribute:: backgroundcolor

       A :class:`Color` object indicating the background color of the
       map, or :const:`None` if no background color is defined.

    .. attribute:: nextobjectid

       The next available ID for new objects.  Set to :const:`None` to
       not set it.

    .. attribute:: properties

       A list of :class:`Property` objects indicating the map's
       properties.

    .. attribute:: tilesets

       A list of :class:`Tileset` objects indicating the map's tilesets.

    .. attribute:: layers

       A list of :class:`Layer`, :class:`ObjectGroup`,
       :class:`GroupLayer`, and :class:`ImageLayer` objects indicating
       the map's tile layers, object groups, group layers, and image
       layers, respectively.  Those that appear in this list first are
       rendered first (i.e. furthest in the back).

    .. attribute:: layers_list

       :attr:`layers`, but with all :class:`GroupLayer` objects
       replaced recursively with their respective layer lists.  Use this
       to ignore the layer hierarchy and treat it as a simple list of
       layers instead.

       (Read-only)
    """

    @property
    def layers_list(self):
        def expand_layers(layers):
            new_layers = []
            for layer in layers:
                if isinstance(layer, GroupLayer):
                    new_layers.extend(expand_layers(layer.layers))
                else:
                    new_layers.append(layer)
            return new_layers

        return expand_layers(self.layers)

    def __init__(self):
        self.version = "1.0"
        self.orientation = "orthogonal"
        self.renderorder = "right-down"
        self.width = 0
        self.height = 0
        self.tilewidth = 32
        self.tileheight = 32
        self.staggeraxis = None
        self.staggerindex = None
        self.hexsidelength = None
        self.backgroundcolor = None
        self.nextobjectid = None
        self.properties = []
        self.tilesets = []
        self.layers = []

    @classmethod
    def load(cls, fname):
        """
        Load the TMX file with the indicated name and return a
        :class:`TileMap` object representing it.
        """
        self = cls()

        tree = ET.parse(fname)
        root = tree.getroot()
        fd = os.path.dirname(fname)
        self.version = root.attrib.get("version", self.version)
        self.orientation = root.attrib.get("orientation", self.orientation)
        self.renderorder = root.attrib.get("renderorder", self.renderorder)
        self.width = int(root.attrib.get("width", self.width))
        self.height = int(root.attrib.get("height", self.height))
        self.tilewidth = int(root.attrib.get("tilewidth", self.tilewidth))
        self.tileheight = int(root.attrib.get("tileheight", self.tileheight))
        self.staggeraxis = root.attrib.get("staggeraxis", self.staggeraxis)
        self.staggerindex = root.attrib.get("staggerindex", self.staggerindex)
        self.hexsidelength = root.attrib.get("hexsidelength",
                                             self.hexsidelength)
        if self.hexsidelength is not None:
            self.hexsidelength = int(self.hexsidelength)
        self.backgroundcolor = root.attrib.get("backgroundcolor")
        if self.backgroundcolor:
            self.backgroundcolor = Color(self.backgroundcolor)
        self.nextobjectid = root.attrib.get("nextobjectid", self.nextobjectid)
        if self.nextobjectid is not None:
            self.nextobjectid = int(self.nextobjectid)

        def get_properties(properties_root, fd=fd):
            properties = []
            for prop in properties_root.findall("property"):
                name = prop.attrib.get("name")
                value = prop.attrib.get("value")
                if not value:
                    value = prop.text
                type_ = prop.attrib.get("type", "string")
                if type_ == "bool":
                    value = (value.lower() == "true")
                elif type_ == "int":
                    value = int(value)
                elif type_ == "float":
                    value = float(value)
                elif type_ == "file":
                    value = pathlib.PurePath(os.path.join(fd, value))
                elif type_ == "color":
                    value = Color(value)
                properties.append(Property(name, value))
            return properties

        def get_image(image_root, fd=fd):
            format_ = image_root.attrib.get("format")
            source = image_root.attrib.get("source")
            if source is not None:
                source = os.path.join(fd, source)
            trans = image_root.attrib.get("trans")
            width = image_root.attrib.get("width")
            height = image_root.attrib.get("height")
            data = None

            for child in image_root:
                if child.tag == "data":
                    data = child.text.strip()

            return Image(format_, source, trans, width, height, data)

        def get_animation(animation_root):
            animation = []

            for child in animation_root.findall("frame"):
                tid = child.attrib.get("tileid")
                if tid is not None:
                    tid = int(tid)
                else:
                    tid = 0
                duration = child.attrib.get("duration")
                if duration is not None:
                    duration = int(duration)
                else:
                    duration = 0

                animation.append(Frame(tid, duration))

            return animation

        def get_layer(layer_root):
            name = layer_root.attrib.get("name", "")
            opacity = float(layer_root.attrib.get("opacity", 1))
            visible = bool(int(layer_root.attrib.get("visible", True)))
            offsetx = int(layer_root.attrib.get("offsetx", 0))
            offsety = int(layer_root.attrib.get("offsety", 0))
            height = int(layer_root.attrib.get("height", 0))
            width = int(layer_root.attrib.get("width", 0))
            properties = []
            tiles = []

            for child in layer_root:
                if child.tag == "properties":
                    properties.extend(get_properties(child))
                elif child.tag == "data":
                    encoding = child.attrib.get("encoding")
                    compression = child.attrib.get("compression")
                    if encoding:
                        tile_n = data_decode(child.text, encoding,
                                             compression)
                    else:
                        tile_n = [int(tile.attrib.get("gid", 0))
                                  for tile in child.findall("tile")]

                    for n in tile_n:
                        gid = (n - (n & 2 ** 31) - (n & 2 ** 30) -
                               (n & 2 ** 29))
                        hflip = bool(n & 2 ** 31)
                        vflip = bool(n & 2 ** 30)
                        dflip = bool(n & 2 ** 29)
                        tiles.append(LayerTile(gid, hflip, vflip, dflip))

            return Layer(name, opacity, visible, offsetx, offsety, properties,
                         tiles, width, height)

        def get_objectgroup(layer_root):
            name = layer_root.attrib.get("name", "")
            color = layer_root.attrib.get("color")
            if color:
                color = Color(color)
            opacity = float(layer_root.attrib.get("opacity", 1))
            visible = bool(int(layer_root.attrib.get("visible", True)))
            offsetx = int(layer_root.attrib.get("offsetx", 0))
            offsety = int(layer_root.attrib.get("offsety", 0))
            draworder = layer_root.attrib.get("draworder")
            properties = []
            objects = []

            for ogchild in layer_root:
                if ogchild.tag == "properties":
                    properties.extend(get_properties(ogchild))
                elif ogchild.tag == "object":
                    oid = ogchild.attrib.get("id")
                    oname = ogchild.attrib.get("name", "")
                    otype = ogchild.attrib.get("type", "")
                    ox = int(ogchild.attrib.get("x", 0))
                    oy = int(ogchild.attrib.get("y", 0))
                    owidth = int(ogchild.attrib.get("width", 0))
                    oheight = int(ogchild.attrib.get("height", 0))
                    orotation = float(ogchild.attrib.get("rotation", 0))
                    ogid = ogchild.attrib.get("gid")
                    if ogid is not None:
                        ogid = int(ogid)
                    ovisible = bool(int(ogchild.attrib.get("visible",
                                                           True)))
                    oproperties = []
                    oellipse = False
                    opolygon = None
                    opolyline = None
                    otext = None

                    for ochild in ogchild:
                        if ochild.tag == "properties":
                            oproperties.extend(get_properties(ochild))
                        elif ochild.tag == "ellipse":
                            oellipse = True
                        elif ochild.tag == "polygon":
                            s = ochild.attrib.get("points", "").strip()
                            opolygon = []
                            for coord in s.split():
                                pos = []
                                for n in coord.split(','):
                                    if n.isdigit():
                                        pos.append(int(n))
                                    else:
                                        pos.append(float(n))
                                opolygon.append(tuple(pos))
                        elif ochild.tag == "polyline":
                            s = ochild.attrib.get("points", "").strip()
                            opolyline = []
                            for coord in s.split():
                                pos = []
                                for n in coord.split(','):
                                    if n.isdigit():
                                        pos.append(int(n))
                                    else:
                                        pos.append(float(n))
                                opolyline.append(tuple(pos))
                        elif ochild.tag == "text":
                            ttext = ochild.text
                            tfontfamily = ochild.attrib.get("fontfamily")
                            tpixelsize = int(ochild.attrib.get("pixelsize"))
                            twrap = bool(int(ochild.attrib.get("wrap")))
                            tcolor = ochild.attrib.get("color")
                            if tcolor:
                                tcolor = Color(tcolor)
                            tbold = bool(int(ochild.attrib.get("bold")))
                            titalic = bool(int(ochild.attrib.get("italic")))
                            tunderline = bool(int(ochild.attrib.get("underline")))
                            tstrikeout = bool(int(ochild.attrib.get("strikeout")))
                            tkerning = bool(int(ochild.attrib.get("kerning")))
                            thalign = ochild.attrib.get("halign")
                            tvalign = ochild.attrib.get("valign")
                            otext = Text(ttext, tfontfamily, tpixelsize,
                                         twrap, tcolor, tbold, titalic,
                                         tunderline, tstrikeout, tkerning,
                                         thalign, tvalign)

                    objects.append(Object(oname, otype, ox, oy, owidth,
                                          oheight, orotation, ogid,
                                          ovisible, oproperties, oellipse,
                                          opolygon, opolyline, oid, otext))

            return ObjectGroup(name, color, opacity, visible, offsetx, offsety,
                               draworder, properties, objects)

        def get_imagelayer(layer_root):
            name = layer_root.attrib.get("name", "")
            x = int(layer_root.attrib.get("offsetx", layer_root.attrib.get("x", 0)))
            y = int(layer_root.attrib.get("offsety", layer_root.attrib.get("y", 0)))
            opacity = float(layer_root.attrib.get("opacity", 1))
            visible = bool(int(layer_root.attrib.get("visible", True)))
            properties = []
            image = None

            for child in layer_root:
                if child.tag == "properties":
                    properties.extend(get_properties(child))
                elif child.tag == "image":
                    image = get_image(child)

            return ImageLayer(name, x, y, opacity, visible, properties, image)

        def get_grouplayer(layer_root):
            name = layer_root.attrib.get("name", "")
            x = int(layer_root.attrib.get("offsetx", layer_root.attrib.get("x", 0)))
            y = int(layer_root.attrib.get("offsety", layer_root.attrib.get("y", 0)))
            opacity = float(layer_root.attrib.get("opacity", 1))
            visible = bool(int(layer_root.attrib.get("visible", True)))
            properties = []
            layers = []

            for child in layer_root:
                if child.tag == "properties":
                    properties.extend(get_properties(child))
                elif child.tag == "layer":
                    layers.append(get_layer(child))
                elif child.tag == "objectgroup":
                    layers.append(get_objectgroup(child))
                elif child.tag == "imagelayer":
                    layers.append(get_imagelayer(child))
                elif child.tag == "group":
                    layers.append(get_grouplayer(child))

            return GroupLayer(name, x, y, opacity, visible, properties, layers)

        for child in root:
            if child.tag == "properties":
                self.properties.extend(get_properties(child))
            elif child.tag == "tileset":
                firstgid = int(child.attrib.get("firstgid"))
                source = child.attrib.get("source")

                if source is not None:
                    source = os.path.join(fd, source)
                    troot = ET.parse(source).getroot()
                    td = os.path.dirname(source)
                else:
                    troot = child
                    td = fd

                name = troot.attrib.get("name", "")
                tilewidth = int(troot.attrib.get("tilewidth", 32))
                tileheight = int(troot.attrib.get("tileheight", 32))
                spacing = int(troot.attrib.get("spacing", 0))
                margin = int(troot.attrib.get("margin", 0))
                tilecount = troot.attrib.get("tilecount")
                if tilecount is not None:
                    tilecount = int(tilecount)
                columns = troot.attrib.get("columns")
                if columns is not None:
                    columns = int(columns)

                xoffset = 0
                yoffset = 0
                properties = []
                image = None
                terraintypes = []
                tiles = []

                for tchild in troot:
                    if tchild.tag == "tileoffset":
                        xoffset = int(tchild.attrib.get("x", xoffset))
                        yoffset = int(tchild.attrib.get("y", yoffset))
                    elif tchild.tag == "properties":
                        properties.extend(get_properties(tchild))
                    elif tchild.tag == "image":
                        image = get_image(tchild, td)
                    elif tchild.tag == "terraintypes":
                        for terrain in tchild.findall("terrain"):
                            trname = terrain.attrib.get("name")
                            trtile = terrain.attrib.get("tile")
                            trproperties = []
                            for trchild in terrain:
                                if trchild.tag == "properties":
                                    trproperties.extend(get_properties(
                                        trchild))
                            terraintypes.append(TerrainType(trname, trtile,
                                                            trproperties))
                    elif tchild.tag == "tile":
                        tid = tchild.attrib.get("id")
                        if tid is not None:
                            tid = int(tid)
                        ttype = tchild.attrib.get("type")
                        titerrain = tchild.attrib.get("terrain")
                        tiprobability = tchild.attrib.get("probability")
                        tiproperties = []
                        timage = None
                        tianimation = None
                        for tichild in tchild:
                            if tichild.tag == "properties":
                                tiproperties.extend(get_properties(tichild))
                            elif tichild.tag == "image":
                                timage = get_image(tichild, td)
                            elif tichild.tag == "animation":
                                tianimation = get_animation(tichild)
                        tiles.append(Tile(tid, titerrain, tiprobability,
                                          tiproperties, timage, tianimation,
                                          ttype))

                self.tilesets.append(Tileset(firstgid, name, tilewidth,
                                             tileheight, source, spacing,
                                             margin, xoffset, yoffset,
                                             tilecount, columns, properties,
                                             image, terraintypes, tiles))
            elif child.tag == "layer":
                self.layers.append(get_layer(child))
            elif child.tag == "objectgroup":
                self.layers.append(get_objectgroup(child))
            elif child.tag == "imagelayer":
                self.layers.append(get_imagelayer(child))
            elif child.tag == "group":
                self.layers.append(get_grouplayer(child))

        return self

    def save(self, fname, data_encoding="base64", data_compression=True):
        """
        Save the object to the file with the indicated name.

        Arguments:

        - ``data_encoding`` -- The encoding to use for layers.  Can be
          ``"base64"`` or ``"csv"``.  Set to :const:`None` for the
          default encoding (currently ``"base64"``).
        - ``data_compression`` -- Whether or not compression should be
          used on layers if possible (currently only possible for
          base64-encoded data).
        """
        if data_encoding is None:
            data_encoding = "base64"

        def clean_attr(d):
            new_d = {}
            for i in d:
                if d[i] is not None:
                    new_d[i] = str(d[i])
            return new_d

        bgc = str(self.backgroundcolor) if self.backgroundcolor else None
        attr = {"version": self.version, "orientation": self.orientation,
                "renderorder": self.renderorder, "width": self.width,
                "height": self.height, "tilewidth": self.tilewidth,
                "tileheight": self.tileheight, "staggeraxis": self.staggeraxis,
                "staggerindex": self.staggerindex,
                "hexsidelength": self.hexsidelength, "backgroundcolor": bgc,
                "nextobjectid": self.nextobjectid}
        root = ET.Element("map", attrib=clean_attr(attr))
        fd = os.path.dirname(fname)

        def get_properties_elem(properties, fd=fd):
            elem = ET.Element("properties")
            for prop in properties:
                value = str(prop.value)
                type_ = None
                text = None
                if isinstance(prop.value, bool):
                    value = "true" if prop.value else "false"
                    type_ = "bool"
                elif isinstance(prop.value, int):
                    type_ = "int"
                elif isinstance(prop.value, float):
                    type_ = "float"
                elif isinstance(prop.value, Color):
                    type_ = "color"
                elif isinstance(prop.value, pathlib.PurePath):
                    value = prop.value.as_posix()
                    type_ = "file"

                prop_attr = {"name": prop.name}
                if '\n' in value:
                    text = value
                else:
                    prop_attr["value"] = value
                if type_:
                    prop_attr["type"] = type_

                elem.append(ET.Element(
                    "property", attrib=clean_attr(prop_attr), text=text))

            return elem

        def get_image_elem(image_obj, fd=fd):
            attr = {"format": image_obj.format, "trans": image_obj.trans,
                    "width": image_obj.width, "height": image_obj.height}
            if image_obj.source:
                pth = pathlib.PurePath(os.path.relpath(image_obj.source, fd))
                attr["source"] = pth.as_posix()
            elem = ET.Element("image", attrib=clean_attr(attr))

            if image_obj.data is not None:
                data_elem = ET.Element("data")
                data_elem.text = image_obj.data
                elem.append(data_elem)

            return elem

        def get_animation_elem(animation, fd=fd):
            elem = ET.Element("animation")
            for animation_obj in animation:
                attr = {"tileid": animation_obj.tileid,
                        "duration": animation_obj.duration}
                elem.append(ET.Element("frame", attrib=clean_attr(attr)))

            return elem

        def get_layer_elem(layer, fd=fd, data_encoding=data_encoding,
                           data_compression=data_compression):
            attr = {"name": layer.name}
            attr["width"] = layer.width
            attr["height"] = layer.height
            if layer.opacity != 1:
                attr["opacity"] = layer.opacity
            if not layer.visible:
                attr["visible"] = "0"
            if layer.offsetx:
                attr["offsetx"] = layer.offsetx
            if layer.offsety:
                attr["offsety"] = layer.offsety
            elem = ET.Element("layer", attrib=clean_attr(attr))

            if layer.properties:
                elem.append(get_properties_elem(layer.properties))

            tile_n = [int(i) for i in layer.tiles]
            attr = {"encoding": data_encoding,
                    "compression": "zlib" if data_compression else None}
            data_elem = ET.Element("data", attrib=clean_attr(attr))
            data_elem.text = data_encode(tile_n, data_encoding,
                                         data_compression)
            elem.append(data_elem)

            return elem

        def get_objectgroup_elem(layer, fd=fd, data_encoding=data_encoding,
                                 data_compression=data_compression):
            c = str(layer.color) if layer.color else None
            attr = {"name": layer.name, "color": c}
            if layer.opacity != 1:
                attr["opacity"] = layer.opacity
            if not layer.visible:
                attr["visible"] = "0"
            if layer.offsetx:
                attr["offsetx"] = layer.offsetx
            if layer.offsety:
                attr["offsety"] = layer.offsety
            if layer.draworder:
                attr["draworder"] = layer.draworder
            elem = ET.Element("objectgroup", attrib=clean_attr(attr))

            if layer.properties:
                elem.append(get_properties_elem(layer.properties))

            for obj in layer.objects:
                attr = {"id": obj.id, "name": obj.name, "type": obj.type,
                        "x": obj.x, "y": obj.y, "gid": obj.gid}
                if obj.width:
                    attr["width"] = obj.width
                if obj.height:
                    attr["height"] = obj.height
                if obj.rotation:
                    attr["rotation"] = obj.rotation
                if not obj.visible:
                    attr["visible"] = "0"
                object_elem = ET.Element("object", attrib=clean_attr(attr))

                if obj.ellipse:
                    object_elem.append(ET.Element("ellipse"))
                elif obj.polygon is not None:
                    points = ' '.join(['{},{}'.format(*T)
                                       for T in obj.polygon])
                    poly_elem = ET.Element("polygon",
                                           attrib={"points": points})
                    object_elem.append(poly_elem)
                elif obj.polyline is not None:
                    points = ' '.join(['{},{}'.format(*T)
                                       for T in obj.polyline])
                    poly_elem = ET.Element("polyline",
                                           attrib={"points": points})
                    object_elem.append(poly_elem)
                elif obj.text:
                    c = str(obj.text.color) if obj.text.color else None
                    tattr = {"fontfamily": obj.text.fontfamily,
                             "pixelsize": obj.text.pixelsize, "color": c,
                             "halign": obj.text.halign,
                             "valign": obj.text.valign}
                    if obj.text.wrap:
                        tattr["wrap"] = "1"
                    if obj.text.bold:
                        tattr["bold"] = "1"
                    if obj.text.italic:
                        tattr["italic"] = "1"
                    if obj.text.underline:
                        tattr["underline"] = "1"
                    if obj.text.strikeout:
                        tattr["strikeout"] = "1"
                    if not obj.text.kerning:
                        tattr["kerning"] = "0"
                    text_elem = ET.Element("text", attrib=clean_attr(tattr))
                    text_elem.text = obj.text.text
                    object_elem.append(text_elem)

                elem.append(object_elem)

            return elem

        def get_imagelayer_elem(layer, fd=fd, data_encoding=data_encoding,
                                data_compression=data_compression):
            attr = {"name": layer.name, "offsetx": layer.offsetx,
                    "offsety": layer.offsety, "x": layer.offsetx,
                    "y": layer.offsety}
            if layer.opacity != 1:
                attr["opacity"] = layer.opacity
            if not layer.visible:
                attr["visible"] = "0"
            elem = ET.Element("imagelayer", attrib=clean_attr(attr))

            if layer.properties:
                elem.append(get_properties_elem(layer.properties))

            if layer.image:
                elem.append(get_image_elem(layer.image))

            return elem

        def get_grouplayer_elem(layer, fd=fd, data_encoding=data_encoding,
                                data_compression=data_compression):
            attr = {"name": layer.name, "offsetx": layer.offsetx,
                    "offsety": layer.offsety}
            if layer.opacity != 1:
                attr["opacity"] = layer.opacity
            if not layer.visible:
                attr["visible"] = "0"
            elem = ET.Element("group", attrib=clean_attr(attr))

            if layer.properties:
                elem.append(get_properties_elem(layer.properties))

            for sublayer in layer.layers:
                if isinstance(sublayer, Layer):
                    elem.append(get_layer_elem(sublayer))
                elif isinstance(sublayer, ObjectGroup):
                    elem.append(get_objectgroup_elem(sublayer))
                elif isinstance(sublayer, ImageLayer):
                    elem.append(get_imagelayer_elem(sublayer))
                elif isinstance(sublayer, GroupLayer):
                    elem.append(get_grouplayer_elem(sublayer))
                else:
                    e = "{} is not a supported layer type.".format(
                        sublayer.__class__.__name__)
                    raise ValueError(e)

            return elem

        if self.properties:
            root.append(get_properties_elem(self.properties))

        for tileset in self.tilesets:
            attr = {"firstgid": tileset.firstgid, "name": tileset.name,
                    "tilewidth": tileset.tilewidth,
                    "tileheight": tileset.tileheight}
            if tileset.source:
                pth = pathlib.PurePath(os.path.relpath(tileset.source, fd))
                attr["source"] = pth.as_posix()
            if tileset.spacing:
                attr["spacing"] = tileset.spacing
            if tileset.margin:
                attr["margin"] = tileset.margin
            if tileset.tilecount:
                attr["tilecount"] = tileset.tilecount
            if tileset.columns:
                attr["columns"] = tileset.columns
            elem = ET.Element("tileset", attrib=clean_attr(attr))

            if tileset.xoffset or tileset.yoffset:
                attr = {"x": tileset.xoffset, "y": tileset.yoffset}
                offset_elem = ET.Element("tileoffset", attrib=clean_attr(attr))
                elem.append(offset_elem)

            if tileset.properties:
                elem.append(get_properties_elem(tileset.properties))

            if tileset.image:
                elem.append(get_image_elem(tileset.image))

            if tileset.animation:
                elem.append(get_animation_elem(tileset.animation))

            if tileset.terraintypes:
                ttypes_elem = ET.Element("terraintypes")

                for terrain in tileset.terraintypes:
                    attr = {"name": terrain.name, "tile": terrain.tile}
                    terrain_elem = ET.Element("terrain",
                                              attrib=clean_attr(attr))

                    if terrain.properties:
                        prop_elem = get_properties_elem(terrain.properties)
                        terrain_elem.append(prop_elem)

                    ttypes_elem.append(terrain_elem)

                elem.append(ttypes_elem)

            for tile in tileset.tiles:
                attr = {"id": tile.id, "terrain": tile.terrain,
                        "probability": tile.probability}
                if tile.type:
                    attr["type"] = tile.type
                tile_elem = ET.Element("tile", attrib=clean_attr(attr))

                if tile.properties:
                    tile_elem.append(get_properties_elem(tile.properties))

                if tile.image:
                    tile_elem.append(get_image_elem(tile.image))

                elem.append(tile_elem)

            root.append(elem)

        for layer in self.layers:
            if isinstance(layer, Layer):
                root.append(get_layer_elem(layer))
            elif isinstance(layer, ObjectGroup):
                root.append(get_objectgroup_elem(layer))
            elif isinstance(layer, ImageLayer):
                root.append(get_imagelayer_elem(layer))
            elif isinstance(layer, GroupLayer):
                root.append(get_grouplayer_elem(layer))
            else:
                e = "{} is not a supported layer type.".format(
                    layer.__class__.__name__)
                raise ValueError(e)

        tree = ET.ElementTree(root)
        tree.write(fname, encoding="UTF-8", xml_declaration=True)


class Color(object):

    """
    .. attribute:: red

       The red component of the color as an integer, where ``0``
       indicates no red intensity and ``255`` indicates full red
       intensity.

    .. attribute:: green

       The green component of the color as an integer, where ``0``
       indicates no green intensity and ``255`` indicates full green
       intensity.

    .. attribute:: blue

       The blue component of the color as an integer, where ``0``
       indicates no blue intensity and ``255`` indicates full blue
       intensity.

    .. attribute:: alpha

       The alpha transparency of the color as an integer, where ``0``
       indicates full transparency and ``255`` indicates full opacity.

    .. attribute:: hex_string

       The hex string representation of the color used by the TMX file.
       The format of the string is either ``"#RRGGBB"`` or
       ``"#AARRGGBB"``.  The hash at the beginning is optional.
    """

    def __init__(self, hex_string="#000000"):
        self.hex_string = hex_string

    @property
    def red(self):
        return self.__r

    @red.setter
    def red(self, value):
        self.__r = max(0, min(value, 255))

    @property
    def green(self):
        return self.__g

    @green.setter
    def green(self, value):
        self.__g = max(0, min(value, 255))

    @property
    def blue(self):
        return self.__b

    @blue.setter
    def blue(self, value):
        self.__b = max(0, min(value, 255))

    @property
    def alpha(self):
        return self.__a

    @alpha.setter
    def alpha(self, value):
        self.__a = max(0, min(value, 255))

    @property
    def hex_string(self):
        if self.alpha == 255:
            r, g, b = [hex(c)[2:].zfill(2) for c in (self.red, self.green,
                                                     self.blue)]
            return "#{}{}{}".format(r, g, b)
        else:
            r, g, b, a = [hex(c)[2:].zfill(2) for c in (self.red, self.green,
                                                        self.blue, self.alpha)]
            return "#{}{}{}{}".format(a, r, g, b)

    @hex_string.setter
    def hex_string(self, value):
        if value.startswith("#"):
            value = value[1:]

        if len(value) == 6:
            r, g, b = [int(value[i:(i + 2)], 16)
                       for i in six.moves.range(0, 6, 2)]
            self.red, self.green, self.blue = r, g, b
            self.alpha = 255
        elif len(value) == 8:
            a, r, g, b = [int(value[i:(i + 2)], 16) for i in range(0, 8, 2)]
            self.red, self.green, self.blue, self.alpha = r, g, b, a
        else:
            raise ValueError("Invalid color string.")

    def __iter__(self):
        return str(self)

    def __repr__(self):
        return self.hex_string

    def __str__(self):
        return self.hex_string

    def __getitem__(self, index):
        return str(self)[index]


class Image(object):

    """
    .. attribute:: format

       Indicates the format of image data if embedded.  Should be an
       extension like ``"png"``, ``"gif"``, ``"jpg"``, or ``"bmp"``.
       Set to :const:`None` to not specify the format.

    .. attribute:: source

       The location of the image file referenced.  If set to
       :const:`None`, the image data is embedded.

    .. attribute:: trans

       A :class:`Color` object indicating the transparent color of the
       image, or :const:`None` if no color is treated as transparent.

    .. attribute:: width

       The width of the image in pixels; used for tile index correction
       when the image changes.  If set to :const:`None`, the image width
       is not explicitly specified.

    .. attribute:: height

       The height of the image in pixels; used for tile index correction
       when the image changes.  If set to :const:`None`, the image
       height is not explicitly specified.

    .. attribute:: data

       The image data if embedded, or :const:`None` if an external image
       is referenced.
    """

    def __init__(self, format_=None, source=None, trans=None, width=None,
                 height=None, data=None):
        self.format = format_
        self.source = source
        self.trans = trans
        self.width = width
        self.height = height
        self.data = data


class Text(object):

    """
    .. attribute:: text

       The text displayed.

    .. attribute:: fontfamily

       The font family used.

    .. attribute:: pixelsize

       The size of the font in pixels.

    .. attribute:: wrap

       Whether or not word wrapping is enabled.

    .. attribute:: color

       A :class:`Color` object indicating the color of the text.

    .. attribute:: bold

       Whether or not the font is bold.

    .. attribute:: italic

       Whether or not the font is italic.

    .. attribute:: underline

       Whether or not a line should be drawn below the text.

    .. attribute:: strikeout

       Whether or not a line should be drawn through the text.

    .. attribute:: kerning

       Whether or not kerning should be used.

    .. attribute:: halign

       Horizontal alignment of the text within the object (``"left"``,
       ``"center"``, or ``"right"``).

    .. attribute:: valign

       Vertical alignment of the text within the object (``"top"``,
       ``"center"``, or ``"bottom"``).
    """

    def __init__(self, text="", fontfamily="sans-serif", pixelsize=16,
                 wrap=False, color=Color("#000000"), bold=False, italic=False,
                 underline=False, strikeout=False, kerning=True, halign="left",
                 valign="top"):
        self.text = text
        self.fontfamily = fontfamily
        self.pixelsize = pixelsize
        self.wrap = wrap
        self.color = color
        self.bold = bold
        self.italic = italic
        self.underline = underline
        self.strikeout = strikeout
        self.kerning = kerning
        self.halign = halign
        self.valign = valign


class ImageLayer(object):

    """
    .. attribute:: name

       The name of the image layer.

    .. attribute:: offsetx

       The x position of the image layer in pixels.

    .. attribute:: offsety

       The y position of the image layer in pixels.

    .. attribute:: opacity

       The opacity of the image layer as a value from 0 to 1.

    .. attribute:: visible

       Whether or not the image layer is visible.

    .. attribute:: properties

       A list of :class:`Property` objects indicating the properties of
       the image layer.

    .. attribute:: image

       An :class:`Image` object indicating the image of the image layer.
    """

    def __init__(self, name, offsetx, offsety, opacity=1, visible=True,
                 properties=None, image=None):
        self.name = name
        self.offsetx = offsetx
        self.offsety = offsety
        self.opacity = opacity
        self.visible = visible
        self.properties = properties if properties else []
        self.image = image


class Layer(object):

    """
    .. attribute:: name

       The name of the layer.

    .. attribute:: opacity

       The opacity of the layer as a value from 0 to 1.

    .. attribute:: visible

       Whether or not the layer is visible.

    .. attribute:: offsetx

       Rendering offset for this layer in pixels.

    .. attribute:: offsety

       Rendering offset for this layer in pixels.

    .. attribute:: properties

       A list of :class:`Property` objects indicating the properties of
       the layer.

    .. attribute:: tiles

       A list of :class:`LayerTile` objects indicating the tiles of the
       layer.

       The coordinates of each tile is determined by the tile's index
       within this list.  Exactly how the tiles are positioned is
       determined by the map orientation.
    """

    def __init__(self, name, opacity=1, visible=True, offsetx=0, offsety=0,
                 properties=None, tiles=None, width=0, height=0):
        self.name = name
        self.opacity = opacity
        self.visible = visible
        self.offsetx = offsetx
        self.offsety = offsety
        self.properties = properties if properties else []
        self.tiles = tiles if tiles else []
        self.width = width
        self.height = height


class LayerTile(object):
    """
    .. attribute:: gid

       The global ID of the tile.  A value of ``0`` indicates no tile at
       this position.

    .. attribute:: hflip

       Whether or not the tile is flipped horizontally.

    .. attribute:: vflip

       Whether or not the tile is flipped vertically.

    .. attribute:: dflip

       Whether or not the tile is flipped diagonally (X and Y axis
       swapped).
    """

    def __init__(self, gid, hflip=False, vflip=False, dflip=False):
        self.gid = gid
        self.hflip = hflip
        self.vflip = vflip
        self.dflip = dflip

    def __int__(self):
        r = self.gid
        if self.hflip:
            r |= 2 ** 31
        if self.vflip:
            r |= 2 ** 30
        if self.dflip:
            r |= 2 ** 29

        return r


class Object(object):

    """
    .. attribute:: id

       Unique ID of the object as a string if set, or :const:`None`
       otherwise.

    .. attribute:: name

       The name of the object.  An arbitrary string.

    .. attribute:: type

       The type of the object.  An arbitrary string.

    .. attribute:: x

       The x coordinate of the object in pixels.  This is the
       left edge of the object in orthogonal orientation, and the center
       of the object otherwise.

    .. attribute:: y

       The y coordinate of the object in pixels.  This is the bottom
       edge of the object.

    .. attribute:: width

       The width of the object in pixels.

    .. attribute:: height

       The height of the object in pixels.

    .. attribute:: rotation

       The rotation of the object in degrees clockwise.

    .. attribute:: gid

       The tile to use as the object's image.  Set to :const:`None` for
       no reference to a tile.

    .. attribute:: visible

       Whether or not the object is visible.

    .. attribute:: properties

       A list of :class:`Property` objects indicating the object's
       properties.

    .. attribute:: ellipse

       Whether or not the object should be an ellipse.

    .. attribute:: polygon

       A list of coordinate pair tuples relative to the object's
       position indicating the points of the object's representation as
       a polygon.  Set to :const:`None` to not represent the object as a
       polygon.

    .. attribute:: polyline

       A list of coordinate pair tuples relative to the object's
       position indicating the points of the object's representation as
       a polyline.  Set to :const:`None` to not represent the object as
       a polyline.

    .. attribute:: text

       A :class:`Text` object indicating the object's representation as
       text.  Set to :const:`None` to not represent the object as text.
    """

    def __init__(self, name, type_, x, y, width=0, height=0, rotation=0,
                 gid=None, visible=True, properties=None, ellipse=False,
                 polygon=None, polyline=None, id_=None, text=None):
        self.name = name
        self.type = type_
        self.x = x
        self.y = y
        self.id = id_
        self.width = width
        self.height = height
        self.rotation = rotation
        self.gid = gid
        self.visible = visible
        self.properties = properties if properties else []
        self.ellipse = ellipse
        self.polygon = polygon
        self.polyline = polyline
        self.text = text


class ObjectGroup(object):

    """
    .. attribute:: name

       The name of the object group.

    .. attribute:: color

       A :class:`Color` object indicating the color used to display the
       objects in this group.  Set to :const:`None` for no color
       definition.

    .. attribute:: opacity

       The opacity of the object group as a value from 0 to 1.

    .. attribute:: visible

       Whether or not the object group is visible.

    .. attribute:: offsetx

       Rendering offset for this layer in pixels.

    .. attribute:: offsety

       Rendering offset for this layer in pixels.

    .. attribute:: draworder

       Can be "topdown" or "index".  Set to :const:`None` to not define
       this.

    .. attribute:: properties

       A list of :class:`Property` objects indicating the object group's
       properties

    .. attribute:: objects:

       A list of :class:`Object` objects indicating the object group's
       objects.
    """

    def __init__(self, name, color=None, opacity=1, visible=True, offsetx=0,
                 offsety=0, draworder=None, properties=None, objects=None):
        self.name = name
        self.color = color
        self.opacity = opacity
        self.visible = visible
        self.offsetx = offsetx
        self.offsety = offsety
        self.draworder = draworder
        self.properties = properties if properties else []
        self.objects = objects if objects else []


class GroupLayer(object):

    """
    .. attribute:: name

       The name of the group layer.

    .. attribute:: offsetx

       Rendering offset for the group layer in pixels.

    .. attribute:: offsety

       Rendering offset for the group layer in pixels.

    .. attribute:: opacity

       The opacity of the group layer as a value from 0 to 1.

    .. attribute:: visible

       Whether or not the group layer is visible.

    .. attribute:: properties

       A list of :class:`Property` objects indicating the group layer's
       properties.

    .. attribute:: layers

       A list of :class:`Layer`, :class:`ObjectGroup`,
       :class:`GroupLayer`, and :class:`ImageLayer` objects indicating
       the map's tile layers, object groups, group layers, and image
       layers, respectively.  Those that appear in this list first are
       rendered first (i.e. furthest in the back).
    """

    def __init__(self, name, offsetx=0, offsety=0, opacity=1, visible=True,
                 properties=None, layers=None):
        self.name = name
        self.offsetx = offsetx
        self.offsety = offsety
        self.opacity = opacity
        self.visible = visible
        self.properties = properties if properties else []
        self.layers = layers if layers else []


class Property(object):

    """
    .. attribute:: name

       The name of the property.

    .. attribute:: value

       The value of the property.
       
       The following types are specially recognized by the TMX format
       and preserved when saving:

       - Integers
       - Floats
       - Booleans
       - :class:`Color` objects
       - :class:`pathlib.PurePath` objects

       Any other type is implicitly converted to and stored as a string
       when the TMX file is saved.
    """

    def __init__(self, name, value):
        self.name = name
        self.value = value


class TerrainType(object):

    """
    .. attribute:: name

       The name of the terrain type.

    .. attribute:: tile

       The local tile ID of the tile that represents the terrain
       visually.

    .. attribute:: properties

       A list of :class:`Property` objects indicating the terrain type's
       properties.
    """

    def __init__(self, name, tile, properties=None):
        self.name = name
        self.tile = tile
        self.properties = properties if properties else []


class Tile(object):

    """
    .. attribute:: id

       The local tile ID within its tileset.

    .. attribute:: type

       The type of the tile.  An arbitrary string.  Set to :const:`None`
       to not define a type.

    .. attribute:: terrain

       Defines the terrain type of each corner of the tile, given as
       comma-separated indexes in the list of terrain types in the order
       top-left, top-right, bottom-left, bottom-right.  Leaving out a
       value means that corner has no terrain. Set to :const:`None` for
       no terrain.

    .. attribute:: probability

       A percentage indicating the probability that this tile is chosen
       when it competes with others while editing with the terrain tool.
       Set to :const:`None` to not define this.

    .. attribute:: properties

       A list of :class:`Property` objects indicating the tile's
       properties.

    .. attribute:: image

       An :class:`Image` object indicating the tile's image.  Set to
       :const:`None` for no image.

    .. attribute:: animation

       A list of :class:`Frame` objects indicating this tile's animation.
       Set to :const:`None` for no animation.
    """

    def __init__(self, id_, terrain=None, probability=None, properties=None,
                 image=None, animation=None, type_=None):
        self.id = id_
        self.type = type_
        self.terrain = terrain
        self.probability = probability
        self.properties = properties if properties else []
        self.image = image
        self.animation = animation


class Tileset(object):

    """
    .. attribute:: firstgid

       The first global tile ID of this tileset (this global ID maps to
       the first tile in this tileset).

    .. attribute:: name

       The name of this tileset.

    .. attribute:: tilewidth

       The (maximum) width of the tiles in this tileset.

    .. attribute:: tileheight

       The (maximum) height of the tiles in this tileset.

    .. attribute:: source

       The external TSX (Tile Set XML) file to store this tileset in.
       If set to :const:`None`, this tileset is stored in the TMX file.

    .. attribute:: spacing

       The spacing in pixels between the tiles in this tileset (applies
       to the tileset image).

    .. attribute:: margin

       The margin around the tiles in this tileset (applies to the
       tileset image).

    .. attribute:: xoffset

       The horizontal offset of the tileset in pixels (positive is
       right).

    .. attribute:: yoffset

       The vertical offset of the tileset in pixels (positive is down).

    .. attribute:: tilecount

       The number of tiles in this tileset.  Set to :const:`None` to not
       specify this.

    .. attribute:: columns

       The number of tile columns in the tileset.  Set to :const:`None`
       to not specify this.

    .. attribute:: properties

       A list of :class:`Property` objects indicating the tileset's
       properties.

    .. attribute:: image

       An :class:`Image` object indicating the tileset's image.  Set to
       :const:`None` for no image.

    .. attribute:: terraintypes

       A list of :class:`TerrainType` objects indicating the tileset's
       terrain types.

    .. attribute:: tiles

       A list of :class:`Tile` objects indicating the tileset's tile
       properties.
    """

    def __init__(self, firstgid, name, tilewidth, tileheight, source=None,
                 spacing=0, margin=0, xoffset=0, yoffset=0, tilecount=None,
                 columns=None, properties=None, image=None, terraintypes=None,
                 tiles=None):
        self.firstgid = firstgid
        self.name = name
        self.tilewidth = tilewidth
        self.tileheight = tileheight
        self.source = source
        self.spacing = spacing
        self.margin = margin
        self.xoffset = xoffset
        self.yoffset = yoffset
        self.tilecount = tilecount
        self.columns = columns
        self.properties = properties if properties else []
        self.image = image
        self.terraintypes = terraintypes if terraintypes else []
        self.tiles = tiles if tiles else []


class Frame(object):

    """
    .. attribute:: tileid

       Global ID of the tile for this animation frame.

    .. attribute:: duration

       Time length of this frame in milliseconds.
    """

    def __init__(self, tid, duration):
        self.tileid = tid
        self.duration = duration


def data_decode(data, encoding, compression=None):
    """
    Decode encoded data and return a list of integers it represents.

    This is a low-level function used internally by this library; you
    don't typically need to use it.

    Arguments:

    - ``data`` -- The data to decode.
    - ``encoding`` -- The encoding of the data.  Can be ``"base64"`` or
      ``"csv"``.
    - ``compression`` -- The compression method used.  Valid compression
      methods are ``"gzip"`` and ``"zlib"``.  Set to :const:`None` for
      no compression.
    """
    if encoding == "csv":
        return [int(i) for i in data.strip().split(",")]
    elif encoding == "base64":
        data = base64.b64decode(data.strip().encode("latin1"))

        if compression == "gzip":
            # data = gzip.decompress(data)
            with gzip.GzipFile(fileobj=six.BytesIO(data)) as f:
                data = f.read()
        elif compression == "zlib":
            data = zlib.decompress(data)
        elif compression:
            e = 'Compression type "{}" not supported.'.format(compression)
            raise ValueError(e)

        if six.PY2:
            ndata = [ord(c) for c in data]
        else:
            ndata = [i for i in data]

        data = []
        for i in six.moves.range(0, len(ndata), 4):
            n = (ndata[i]  + ndata[i + 1] * (2 ** 8) +
                 ndata[i + 2] * (2 ** 16) + ndata[i + 3] * (2 ** 24))
            data.append(n)

        return data
    else:
        e = 'Encoding type "{}" not supported.'.format(encoding)
        raise ValueError(e)


def data_encode(data, encoding, compression=True):
    """
    Encode a list of integers and return the encoded data.

    This is a low-level function used internally by this library; you
    don't typically need to use it.

    Arguments:

    - ``data`` -- The list of integers to encode.
    - ``encoding`` -- The encoding of the data.  Can be ``"base64"`` or
      ``"csv"``.
    - ``compression`` -- Whether or not compression should be used if
      supported.
    """
    if encoding == "csv":
        return ','.join([str(i) for i in data])
    elif encoding == "base64":
        ndata = []
        for i in data:
            n = [i % (2 ** 8), i // (2 ** 8), i // (2 ** 16), i // (2 ** 24)]
            ndata.extend(n)

        if six.PY2:
            data = b''.join([chr(i) for i in ndata])
        else:
            data = b''.join([bytes((i,)) for i in ndata])

        if compression:
            data = zlib.compress(data)

        return base64.b64encode(data).decode("latin1")
    else:
        e = 'Encoding type "{}" not supported.'.format(encoding)
        raise ValueError(e)
