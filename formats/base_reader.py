# -*- coding: utf-8 -*-
"""
Created on Thu Feb 29 12:23:05 2024

@author: Erty
"""

from pathlib import Path
from formats.wad_handler import WadHandler


class BaseReader:
    """Base class for format readers"""

    def __init__(self, filepath: Path, outputdir: Path):
        self.filepath: Path
        self.entities: list
        self.brushes: list
        self.properties: dict
        self.entity_paths: list

        self.allfaces: list
        self.allvertices: list
        self.vn_map: dict
        self.maskedtextures: list

        self.checked: list
        self.textures: dict
        self.missing_textures: bool

        self.filedir: Path
        self.wadhandler: WadHandler
