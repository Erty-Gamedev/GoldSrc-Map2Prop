# -*- coding: utf-8 -*-
"""
Created on Tue Jul  4 19:01:21 2023

@author: Erty
"""

from pathlib import Path
from collections import OrderedDict
from logutil import get_logger, shutdown_logger
from formats import Face
from formats.wad3_reader import Wad3Reader, TextureEntry
from configutil import config
from shutil import copy2


class WadHandler:
    WAD_SKIP_LIST = [
        'cached',
        'decals',
        'fonts',
        'gfx',
        'spraypaint',
        'tempdecal',
    ]
    SKIP_TEXTURES = [
        'aaatrigger', 'bevel', 'black_hidden',
        'clip', 'clipbevel', 'clipbevelbrush',
        'cliphull1', 'cliphull2', 'cliphull3',
        'contentempty', 'hint', 'noclip', 'null',
        'skip', 'sky', 'solidhint', 'origin'
    ]

    def __init__(self, filedir: Path, outputdir: Path):
        self.__logger = get_logger(__name__)
        self.__filedir = filedir
        self.__outputdir = outputdir
        self.__wad_list = None
        self.__cache_size = config.wad_cache
        self.wads = OrderedDict()
        self.__textures = {}

    def __del__(self):
        shutdown_logger(self.__logger)

    def __get_wad_list(self) -> list:
        cls = self.__class__
        if self.__wad_list is None:
            wad_list = []

            # If set, prioritize config file .wad list
            if config.wad_list:
                wad_list.extend(config.wad_list)

            # Prioritise .wad files from mod folder
            globs = []
            if config.mod_path:
                globs.extend(config.mod_path.glob('*.wad'))

            # Finally add any .wad files from the source file dir
            globs.extend(self.__filedir.glob('*.wad'))

            # Filter out .wad files from skip list
            for glob in globs:
                if glob.stem.lower() in cls.WAD_SKIP_LIST:
                    continue
                wad_list.append(glob)

            self.__wad_list = wad_list

        return self.__wad_list

    def __get_wad_reader(self, wad):
        if wad not in self.wads:
            if self.__cache_size > 0 and len(self.wads) >= self.__cache_size:
                self.wads.popitem(last=False)
            self.wads[wad] = Wad3Reader(wad)
        return self.wads[wad]

    def __check_wads(self, texture: str) -> bool:
        texfile = f"{texture}.bmp"
        for wad in self.__get_wad_list():
            reader = self.__get_wad_reader(wad)
            if texture in reader:
                self.__textures[texture] = reader[texture]
                self.__logger.info(f"""\
Extracting {texture} from {reader.file}.""")
                reader[texture].save(self.__outputdir / texfile)
                return True
        return False

    def check_texture(self, texture: str) -> str:
        if texture.lower() in self.SKIP_TEXTURES:
            return True

        texfile = f"{texture}.bmp"
        check = True
        if not (self.__outputdir / texfile).exists():
            if (self.__filedir / texfile).exists():
                copy2(self.__filedir / texfile, self.__outputdir / texfile)
            else:
                self.__logger.info(f"""\
Texture {texture}.bmp not found in input file's directory. \
Searching directory for .wad packages...""")

                if (check := self.__check_wads(texture)) is False:
                    self.__logger.info(f"""\
Texture {texture} not found in neither input file's directory \
or any .wad packages within that directory. Please place the .wad package \
containing the texture in the input file's directory and re-run the \
application or extract the textures manually prior to compilation.""")
        return check

    def get_texture(self, texture: str) -> TextureEntry:
        return self.__textures[texture]

    def set_wadlist(self, wads: list) -> None:
        if wads and isinstance(wads, (list, tuple)):
            self.__wad_list = [Path(w) for w in wads]

    @classmethod
    def skip_face(cls, face: Face) -> bool:
        return face.texture['name'].lower() in cls.SKIP_TEXTURES
