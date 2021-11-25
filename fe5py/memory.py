
from typing import ByteString


__all__ = [
  "read_byte", "read_word", "read_long",
  "read_byte_range", "read_word_range", "read_long_range",
  "lorom", "unlorom",
  ]


# Generic memory reads


def _r(
    size: int,
    data: ByteString,
    offset: int = 0,
    signed: bool = False,
    ) -> int:
  """Internal data reading helper."""
  return int.from_bytes(data[offset:offset+size], "little", signed=signed)


def read_byte(data: ByteString, offset: int = 0, signed: bool = False) -> int:
  """Reads a single byte."""
  return _r(1, data, offset, signed)


def read_word(data: ByteString, offset: int = 0, signed: bool = False) -> int:
  """Reads a single word."""
  return _r(2, data, offset, signed)


def read_long(data: ByteString, offset: int = 0, signed: bool = False) -> int:
  """Reads a single long."""
  return _r(3, data, offset, signed)


def read_byte_range(
    data: ByteString,
    offset: int,
    count: int,
    signed: bool = False
    ) -> ByteString:
  """Reads a number of bytes."""
  return bytearray([
    read_byte(data, pos, signed)
    for pos in range(offset, offset + (1 * count), 1)
    ])


def read_word_range(
    data: ByteString,
    offset: int,
    count: int,
    signed: bool = False
    ) -> ByteString:
  """Reads a number of words."""
  return bytearray([
    read_word(data, pos, signed)
    for pos in range(offset, offset + (2 * count), 2)
    ])


def read_long_range(
    data: ByteString,
    offset: int,
    count: int,
    signed: bool = False
    ) -> ByteString:
  """Reads a number of longs."""
  return bytearray([
    read_long(data, pos, signed)
    for pos in range(offset, offset + (3 * count), 3)
    ])


# SNES memory mapping


def lorom(address: int, fastROM: bool = True) -> int:
  """Converts a ROM address into its LoROM memory-mapped equivalent."""
  bank = address // 0x8000
  if fastROM: bank |= 0x80
  offset = (address & 0x7FFF) | 0x8000
  return (bank << 16) | offset


def unlorom(address: int) -> int:
  """Converts a LoROM address into its unmapped ROM equivalent."""
  bank = (address >> 16) & 0x7F
  offset = address & 0x7FFF
  return (bank << 15) | offset

