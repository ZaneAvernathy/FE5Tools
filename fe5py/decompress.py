

from math import ceil
from typing import ByteString, Optional
from .memory import read_byte, read_byte_range
from copy import copy


__all__ = [
  "decompress",
  ]


# Internal decompression handlers


def _literal(
    data: ByteString,
    offset: int,
    out: ByteString,
    ) -> tuple[ByteString, ByteString, int]:
  """
  Method 0-3: literal bytes

  Compressed data is a group of raw bytes that gets copied
  verbatim into the output.

  Format:
  NN DD ...

  where:
  NN is the number of bytes to copy - 1
  DD ... is the data to be copied to the output

  Example:
  Compressed:   02 3C 04 28
  Decompressed: 3C 04 28

  """
  size = read_byte(data, offset) + 1
  start = offset + 1

  decomp = read_byte_range(data, start, size)
  disp = size + 1
  comp = read_byte_range(data, offset, disp)

  return (comp, decomp, disp)


def _orr(
    data: ByteString,
    offset: int,
    out: ByteString,
    ) -> tuple[ByteString, ByteString, int]:
  """
  Method 4: ORRed bytes

  Compressed data is a set of nybbles that are ORRed
  with a common value according to a submethod.

  Format:
  ML SV DD ...

  where:
  M is the method (ORR in this case)
  L is the length of the nybble list - 2
  S is the submethod
  V is either the common value or just another nybble
  DD ... are nybbles to combine

  Submethods:
  0: Repeated upper nybble
  1-7: Repeated lower nybble
  8: Repeated upper zero
  9: Repeated lower zero
  A-D: Repeated upper F
  E: Repeated lower F

  Example:
  Compressed:   40 01 23
  Decompressed: 12 13

  """

  length = (read_byte(data, offset) & 0x0F) + 2
  submethod = read_byte(data, offset + 1) >> 4

  chunk = lambda i: read_byte(data, offset + 2 + (i // 2))
  shift = lambda i: 4 * ((1 - (i % 2)))
  nybbles = [(chunk(i) >> shift(i)) & 0x0F for i in range(length)]

  # Submethods 8+ treat this as a regular nybble.
  val = read_byte(data, offset + 1) & 0x0F
  if submethod >= 8:
    nybbles.insert(0, val)

  # Repeated upper nybble
  if (submethod == 0):
    decomp = bytearray([(val << 4) | n for n in nybbles])

  # Repeated lower nybble
  elif (submethod < 8):
    decomp = bytearray([(n << 4) | val for n in nybbles])

  # Repeated upper zero
  elif (submethod == 8):
    decomp = bytearray(nybbles)

  # Repeated lower zero
  elif (submethod == 9):
    decomp = bytearray([n << 4 for n in nybbles])

  # Repeated upper F
  elif (submethod < 0x0E):
    decomp = bytearray([0xF0 | n for n in nybbles])

  # Repeated upper F
  elif (submethod == 0x0E):
    decomp = bytearray([(n << 4) | 0x0F for n in nybbles])

  disp = ceil(length / 2) + 2
  comp = read_byte_range(data, offset, disp)

  return (comp, decomp, disp)


def _double(
    data: ByteString,
    offset: int,
    out: ByteString,
    ) -> tuple[ByteString, ByteString, int]:
  """
  Method 5: Doubled bytes

  Compressed data is a set of bytes that are
  copied twice into the output.

  Format:
  ML DD ...

  where:
  M is the method (double in this case)
  L is the length of bytes to double - 1
  DD ... are bytes to double

  Example:
  Compressed:   52 00 0F 70
  Decompressed: 00 00 0F 0F 70 70

  """
  length = (read_byte(data, offset) & 0x0F) + 1
  start= offset + 1
  decomp = b"".join([
    bytes([i, i]) for i in read_byte_range(data, start, length)
    ])
  disp = length + 1
  comp = read_byte_range(data, offset, disp)
  return (comp, decomp, disp)


def _append(
    data: ByteString,
    offset: int,
    out: ByteString,
    ) -> tuple[ByteString, ByteString, int]:
  """
  Method 6-7: Appended bytes

  Compressed data has a common byte that is
  duplicated before or after each data byte.

  Format:
  ML VV DD ...

  where:
  M is the method (append in this case)
  L is the length of bytes to be appended to - 2
  VV is the byte that will be appended to each data byte
  DD ... are the data bytes

  When the method is 6, the value appears before the data bytes.
  When 7, it appears after.

  Example:
  Compressed:   71 3F 9B 1C EC
  Decompressed: 9B 3F 1C 3F EC 3F

  """
  length = (read_byte(data, offset) & 0x0F) + 2
  submethod = (read_byte(data, offset) >> 4) & 0b1
  val = read_byte(data, offset + 1)
  start = offset + 2
  decomp = read_byte_range(data, start, length)
  for i in range(submethod, 2 * length, 2):
    decomp.insert(i, val)
  disp = length + 2
  comp = read_byte_range(data, offset, disp)
  return (comp, decomp, disp)


def _lookback(
    data: ByteString,
    offset: int,
    out: ByteString,
    ) -> tuple[ByteString, ByteString, int]:
  """
  Method 8-D: Lookback in decompressed output

  Compressed data describes a distance and length
  in the current decompressed bytes to copy into the output.

  There are two formats: short and long.

  Short format in bits:
  M0LL LLDD DDDD DDDD

  where:
  M is the method bit (bit 0x80 for lookback)
  0 is unset
  L is the length - 2
  D is the distance backwards in the output

  Example:
  Current Output: 00 04 00 06
  Compressed:     84 02
  Decompressed:   00 06 00

  Long format in bits:
  MM0L LLLL LDDD DDDD DDDD DDDD
  M is the method bits (bits 0x80 and 0x40 for long lookback)
  0 is unset
  L is the length - 2
  D is the distance backwards in the output

  Current Output: 78 00 00 00 00
  Compressed:     CD 80 01
  Decompressed:   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
                  00 00 00 00 00 00 00 00 00 00 00 00 00

  Notice that the decompressor has no problems copying
  freshly-emitted bytes. This often gets used to copy
  patterns.

  """
  submethod = read_byte(data, offset) >> 4

  # Short lookback
  if (submethod < 0x0C):
    length = ((read_byte(data, offset) - 0x80) >> 2) + 2
    start = (
      ((read_byte(data, offset) & 0x03) << 8)
      | read_byte(data, offset + 1)
      )
    disp = 2

  # Long lookback
  else:
    length = (
      ((read_byte(data, offset) & 0x1F) << 1)
      | (read_byte(data, offset + 1) >> 7)
      ) + 2
    start = (((read_byte(data, offset + 1) & 0x7F) << 8)
            | read_byte(data, offset + 2))
    disp = 3

  comp = read_byte_range(data, offset, disp)

  decomp = copy(out)
  start = len(out) - start
  for i in range(length):
    decomp.append(decomp[start+i])

  decomp = decomp[len(out):]

  return (comp, decomp, disp)


def _rle(
    data: ByteString,
    offset: int,
    out: ByteString,
    ) -> tuple[ByteString, ByteString, int]:
  """
  Method E: Run-length encoding

  Compressed data is a single byte to be repeated
  some number of times into the output.

  Format:
  ML LL DD

  where:
  M is the method (RLE in this case)
  L is the length - 3
  DD is the byte to be repeated

  Example:
  Compressed:     E0 00 12
  Decompressed:   12 12 12

  """
  length = (((read_byte(data, offset) & 0x0F) << 8)
           | read_byte(data, offset + 1)) + 3
  val = read_byte(data, offset + 2)
  disp = 3
  comp = read_byte_range(data, offset, disp)
  decomp = bytearray([val for i in range(length)])
  return (comp, decomp, disp)


def _special(
    data: ByteString,
    offset: int,
    out: ByteString,
    ) -> tuple[ByteString, ByteString, int]:
  """
  Method F: Special methods

  This method has two submethods: short RLE and compressed lookback.
  There are two forms of compressed lookback: short and long.

  Short RLE has the same goal as normal RLE.

  Short RLE format in bits:
  MMMM 0LLL DDDD DDDD

  where:
  M is the method (Special in this case)
  0 is unset
  L is the length - 3
  D is the byte to be repeated

  Example:
  Compressed:     F1 80
  Decompressed:   80 80 80 80

  Compressed lookback is similar to lookback except it is going
  backwards in the compressed data, not the decompressed data, and is
  repeating a number of methods.

  Long compressed lookback format in bits:
  MMMM M0LL LLLD DDDD DDDD DDDD

  where:
  M is the method (Special in this case)
  0 is unset
  L is the number of methods to repeat - 3
  D is the distance backwards in the compression - 3

  Short compressed lookback format in bits:
  MMMM MM0L LLDD DDDD

  where:
  M is the method (Special in this case)
  0 is unset
  L is the number of methods to repeat - 3
  D is the distance backwards in the compression

  """
  submethod = read_byte(data, offset) & 0x0F

  # Short RLE
  if (submethod < 8):

    length = (read_byte(data, offset) & 0x07) + 3
    val = read_byte(data, offset + 1)
    decomp = bytearray([val for i in range(length)])
    disp = 2
    comp = read_byte_range(data, offset, disp)

    return (comp, decomp, disp)

  # Long compressed lookback
  elif (submethod < 0x0C):

    length = (
      ((read_byte(data, offset) & 0x03) << 3)
      | (read_byte(data, offset + 1) >> 5)
      ) + 3
    distance = (
      ((read_byte(data, offset + 1) & 0x1F) << 8) | read_byte(data, offset + 2)
      )
    disp = 3

  # Compressed lookback
  else:

    length = (
      ((read_byte(data, offset) & 0b1) << 2)
      | (read_byte(data, offset + 1) >> 6)
      ) + 3
    distance = read_byte(data, offset + 1) & 0x3F
    disp = 2

  pos = offset - distance

  # Copy these so that we can act like we're appending to
  # the output without actually affecting anything.

  temp_out = bytearray(copy(out))
  temp_data = bytearray(copy(data))

  temp_size = distance if (pos+length) > offset else length
  temp_methods = read_byte_range(data, pos, temp_size)

  # Insert the methods from backwards in the compressed data,
  # replacing the bytes that make up the compressed lookback.

  temp_data[offset:offset+disp] = temp_methods

  # Decompress as if those bytes are normally there.

  i = offset
  while i < (offset + length):
    c, d, di = _decompress_single(temp_data, i, temp_out)

    temp_out.extend(d)
    i += di

  if i > (offset + temp_size):
    disp = length

  decomp = temp_out[len(out):]
  comp = read_byte_range(data, offset, disp)

  return (comp, decomp, disp)


def _debugprint(data: ByteString):
  """Internal helper to print bytes."""
  s = " ".join([f"{b:02X}" for b in data])
  c = [s[i:i+(3*16)] for i in range(0, len(s), 3 * 16)]
  print("\n".join(c))


# Method byte: (decompression handler, debug name)
decomp_handlers = {
  0x00: (_literal, "Literal bytes"),
  0x01: (_literal, "Literal bytes"),
  0x02: (_literal, "Literal bytes"),
  0x03: (_literal, "Literal bytes"),
  0x04: (_orr, "ORRed bytes"),
  0x05: (_double, "Doubled bytes"),
  0x06: (_append, "Pre-appended bytes"),
  0x07: (_append, "Post-appended bytes"),
  0x08: (_lookback, "Short lookback"),
  0x09: (_lookback, "Short lookback"),
  0x0A: (_lookback, "Short lookback"),
  0x0B: (_lookback, "Short lookback"),
  0x0C: (_lookback, "Long lookback"),
  0x0D: (_lookback, "Long lookback"),
  0x0E: (_rle, "Run-length encoding"),
  0x0F: (_special, "Special"),
  }


def _decompress_single(
    data: ByteString,
    offset: int,
    out: ByteString,
    ) -> tuple[ByteString, ByteString, int]:
  """
  Internal helper to decompress a single compressed method.
  """

  method = read_byte(data, offset) >> 4

  handler, _ = decomp_handlers[method]
  comp, decomp, disp = handler(data, offset, out)

  return (comp, decomp, disp)


def decompress(
    data: ByteString,
    offset: int = 0,
    out: Optional[ByteString] = None,
    ) -> tuple[ByteString, int]:
  """
  Decompresses a compressed chunk of data. Returns the decompressed data and
  the compressed size of the chunk. If an existing bytearray `out` is
  specified, the decompressed data will be appended to the end of it.
  """

  start = copy(offset)

  if out is None:
    out = bytearray()

  # Mostly for potential debugging.
  seen = []

  while (method := read_byte(data, offset)) != 0xFF:

    method >>= 4

    handler, name = decomp_handlers[method]
    comp, decomp, disp = handler(data, offset, out)

    seen.append((offset, name, comp, decomp, disp))
    out.extend(decomp)

    offset += disp

  offset += 1

  # Debugging code!

  #for (offset, name, comp, decomp, disp) in seen:
  #  print(f"0x{offset:06X}: {name}")
  #  print(f"Compressed size: {disp:04X}")
  #  print("Compressed bytes:")
  #  _debugprint(comp)
  #  print("Decompressed bytes:")
  #  _debugprint(decomp)
  #  print()

  return (out, offset - start)

