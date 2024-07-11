from typing import List, OrderedDict, Dict, Union, Literal
from pathlib import Path
from collections import OrderedDict
from PIL.Image import Image
import logging
from logutil import shutdown_logger
from formats.wad3_reader import Wad3Reader
from configutil import config
from shutil import copy2


logger = logging.getLogger(__name__)

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
        'aaatrigger', 'black_hidden', 'clipbevelbrush',
        'cliphull1', 'cliphull2', 'cliphull3',
        'contentempty', 'hint', 'noclip', 'null',
        'skip', 'solidhint',
    ]
    TOOL_TEXTURES = [
        'bevel', 'boundingbox', 'clipbevel', 'clip',
        'contentwater', 'origin'
    ]

    def __init__(self, filedir: Path, outputdir: Path):
        self.filedir: Path = filedir
        self.outputdir = outputdir
        self.wad_list: List[Path] = []
        self.cache_size: int = config.wad_cache
        self.wads: OrderedDict[Union[Path, str], Wad3Reader] = OrderedDict()
        self.textures: Dict[str, Image] = {}
        self.used_wads: List[Path] = []

    def __del__(self):
        shutdown_logger(logger)

    def get_wad_list(self) -> List[Path]:
        if not self.wad_list:
            wad_list = []

            # If set, prioritize config file .wad list
            if config.wad_list:
                wad_list.extend(config.wad_list)

            # Prioritise .wad files from mod folder and handle Steampipe
            globs: List[Path] = []
            if modpath := config.mod_path:
                if '_addon' in str(modpath):
                    globs.extend(modpath.glob('*.wad'))
                    modpath = modpath.parent / modpath.stem.replace('_addon', '')
                elif '_hd' in str(modpath):
                    globs.extend(modpath.glob('*.wad'))
                    modpath = modpath.parent / modpath.stem.replace('_hd', '')
                elif '_downloads' in str(modpath):
                    globs.extend(modpath.glob('*.wad'))
                    modpath = modpath.parent / modpath.stem.replace('_downloads', '')
                
                globs.extend(modpath.glob('*.wad'))

            # Finally add any .wad files from the source file dir
            globs.extend(self.filedir.glob('*.wad'))

            # Filter out .wad files from skip list
            glob: Path
            for glob in globs:
                if glob.stem.lower() in self.WAD_SKIP_LIST:
                    continue
                wad_list.append(glob)

            self.wad_list = wad_list

        return self.wad_list

    def get_wad_reader(self, wad: Path):
        if wad not in self.wads:
            if self.cache_size > 0 and len(self.wads) >= self.cache_size:
                self.wads.popitem(last=False)
            self.wads[wad] = Wad3Reader(wad)
        return self.wads[wad]

    def check_wads(self, texture: str) -> Union[Wad3Reader, Literal[False]]:
        for wad in self.get_wad_list():
            reader = self.get_wad_reader(wad)
            if texture in reader:
                if wad not in self.used_wads:
                    self.used_wads.append(wad)
                self.textures[texture] = reader[texture]
                return reader
        return False

    def check_texture(self, texture: str) -> bool:
        if texture.lower() in self.SKIP_TEXTURES or texture.lower() in self.TOOL_TEXTURES:
            return True
        
        if texture in self.textures:
            return True
        
        reader: Union[Wad3Reader, Literal[False]] = self.check_wads(texture)

        texfile = f"{texture}.bmp"

        if (self.outputdir / texfile).exists():
            return True

        if (self.filedir / texfile).exists():
            copy2(self.filedir / texfile, self.outputdir / texfile)
            return True
        
        if isinstance(reader, Wad3Reader):
            logger.info(f"Extracting {texture} from {reader.file}.")
            reader[texture].save(self.outputdir / f"{texture}.bmp")
            return True

        logger.info(f"Texture {texture} not found in neither input file's directory "\
            'or any .wad packages within that directory. Please place the .wad package '\
            'containing the texture in the input file\'s directory and re-run the '\
            'application or extract the textures manually prior to compilation.')
        return False

    def get_texture(self, texture: str) -> Image:
        return self.textures[texture]

    def set_wadlist(self, wads: list) -> None:
        if wads and isinstance(wads, (list, tuple)):
            self.wad_list = [Path(w) for w in wads]

    @classmethod
    def skip_face(cls, texture_name: str) -> bool:
        return texture_name.lower() in cls.SKIP_TEXTURES
