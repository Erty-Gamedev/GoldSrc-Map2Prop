# -*- coding: utf-8 -*-
"""
Created on Fri May 26 17:18:27 2023

@author: Erty
"""


from pathlib import Path
from PIL import Image
from formats import InvalidFormatException, unpack


PALETTE_SIZE = 768  # 256 * 3


class DirEntry:
    def __init__(self, data: bytes):
        self.filepos = unpack('<l', data[0:4])[0]
        self.disksize = unpack('<l', data[4:8])[0]
        self.size = unpack('<l', data[8:12])[0]
        self.type = unpack('<b', data[12:13])[0]
        self.compression = unpack('<?', data[13:14])[0]
        self.padding = unpack('<h', data[14:16])[0]
        self.name = unpack('<16s', data[16:32])[0]

    def __str__(self):
        return self.name


class TextureEntry:
    def __init__(self, data: bytes):
        self.name = unpack('<16s', data[0:16])[0].split(
            b'\x00', 1)[0].decode('ascii')
        self.width = unpack('<L', data[16:20])[0]
        self.height = unpack('<L', data[20:24])[0]
        self.mipoffset0 = unpack('<L', data[24:28])[0]
        self.mipoffset1 = unpack('<L', data[28:32])[0]
        self.mipoffset2 = unpack('<L', data[32:36])[0]
        self.mipoffset3 = unpack('<L', data[36:40])[0]
        self.basetexturedata = data[40:self.mipoffset1]
        self.image = Image.frombytes(
            'P', (self.width, self.height), self.basetexturedata, 'raw')
        self.image.putpalette(data[-PALETTE_SIZE-2:-2])

    def __str__(self):
        return self.name


class Wad3Reader:
    """
    Reads all the textures from the specified .wad package
    as PIL Images with preserved indexed palette.
    The instance can be accessed as a dictionary that maps
    texture name to its Image instance.
    """

    def __init__(self, file: Path):
        self.file = file
        with file.open('rb') as wadfile:
            data = wadfile.read()

            header = data[0:12]
            magic = header[0:4]
            if magic != bytes('WAD3', 'ascii'):
                raise InvalidFormatException(
                    f"{file} is not a valid WAD3 file.")

            num_dir_entries = unpack('<l', header[4:8])[0]
            dir_offset = unpack('<l', header[8:])[0]

            self.header = {
                'magic': magic,
                'num_dir_entries': num_dir_entries,
                'dir_offset': dir_offset,
            }

            directories = data[dir_offset:]

            self.dir_entries = []
            self.textures = {}
            for i in range(0, 32 * num_dir_entries, 32):
                entry = DirEntry(directories[i:i+32])
                self.dir_entries.append(entry)
                filepos = entry.filepos
                disksize = entry.disksize

                texture = TextureEntry(
                    data[filepos:filepos+disksize]
                )
                self.textures[texture.name.lower()] = texture

    def __contains__(self, texture) -> bool:
        return texture.lower() in self.textures

    def __getitem__(self, texture) -> Image:
        return self.textures[texture.lower()].image
