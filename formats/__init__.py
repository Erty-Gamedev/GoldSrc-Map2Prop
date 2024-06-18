# -*- coding: utf-8 -*-

from typing import Tuple
from io import BufferedReader
from struct import unpack


def read_byte(file: BufferedReader) -> bytes:
    """Reads a single byte from the buffer"""
    return unpack('<b', file.read(1))[0]


def read_bool(file: BufferedReader) -> bytes:
    """Reads a single byte from the buffer"""
    return unpack('<?', file.read(1))[0]


def read_short(file: BufferedReader) -> bytes:
    """Reads two bytes from the buffer"""
    return unpack('<h', file.read(2))[0]


def read_int(file: BufferedReader) -> int:
    """Reads 4 bytes (int32) from the buffer"""
    return unpack('<i', file.read(4))[0]


def read_float(file: BufferedReader) -> float:
    """Reads 4 bytes (float) from the buffer"""
    return unpack('<f', file.read(4))[0]


def read_double(file: BufferedReader) -> float:
    """Reads 8 bytes (double) from the buffer"""
    return unpack('<d', file.read(8))[0]


def read_string(file: BufferedReader, length: int) -> str:
    """Reads length bytes from the buffer"""
    return unpack(f"<{length}s", file.read(length))[0]


def read_ntstring(file: BufferedReader, length: int) -> str:
    """Reads a null-terminated string of a set length from the buffer"""
    strbytes = unpack(f"<{length}s", file.read(length))[0]
    string = ''
    for b in strbytes:
        if b == 0:
            break
        string += chr(b)
    return string


def read_lpstring(file: BufferedReader) -> str:
    """Reads a length-prefixed ascii string from the buffer"""
    strlen = int(read_byte(file))
    if strlen == 0:
        return ''
    if strlen < 0:
        strlen = 256 + strlen
    return read_ntstring(file, strlen)


def read_lpstring2(file: BufferedReader) -> str:
    """Reads a 4-byte length-prefixed ascii string from the buffer"""
    buffer = file.read(4)
    if len(buffer) < 4:
        raise EndOfFileException()
    strlen = unpack('<i', buffer)[0]
    if strlen == -1:
        return ''
    return read_ntstring(file, strlen)


def read_colour(file: BufferedReader) -> Tuple[int, int, int]:
    """Reads 3 bytes from the buffer"""
    return (
        unpack('<B', file.read(1))[0],
        unpack('<B', file.read(1))[0],
        unpack('<B', file.read(1))[0]
    )


def read_colour_rgba(file: BufferedReader) -> Tuple[int, int, int, int]:
    """Reads 4 bytes from the buffer"""
    return (
        unpack('<B', file.read(1))[0],
        unpack('<B', file.read(1))[0],
        unpack('<B', file.read(1))[0],
        unpack('<B', file.read(1))[0],
    )


def read_vector3D(file: BufferedReader) -> Tuple[float, float, float]:
    """Reads 12 bytes from the buffer"""
    return (
        read_float(file),
        read_float(file),
        read_float(file),
    )


def read_angles(file: BufferedReader) -> Tuple[float, float, float]:
    """Reads 12 bytes from the buffer"""
    return read_vector3D(file)


class InvalidFormatException(Exception):
    pass


class EndOfFileException(Exception):
    pass


class MissingTextureException(Exception):
    pass
