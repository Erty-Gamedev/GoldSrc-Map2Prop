# -*- coding: utf-8 -*-
"""
Created on Tue May 30 21:59:28 2023

@author: Erty
"""

import os
import sys
import configparser
from pathlib import Path


class ConfigUtil:
    def __init__(self, filepath: Path):
        self.config = configparser.ConfigParser()
        if filepath.exists():
            self.config.read(filepath)
        else:
            self.__create_default_config()
            with filepath.open('w') as configfile:
                self.config.write(configfile)

    @property
    def studiomdl(self) -> Path:
        return Path(self.config['AppConfig'].get('studiomdl', False))

    @property
    def mod_path(self) -> Path:
        game = self.config['AppConfig'].get('game config', False)
        steamdir = self.config['AppConfig'].get('steam directory', False)

        if not (game and steamdir):
            return None

        return (Path(steamdir) / r'steamapps\common'
                / self.config[game].get('game')
                / self.config[game].get('mod'))

    @property
    def wad_list(self) -> list:
        wads = (self.config['AppConfig'].get('wad list', '').rstrip(' ,')
                .replace("\n", '').split(','))
        return [Path(wad) for wad in wads if wad != '']

    @property
    def autocompile(self) -> bool:
        return self.config['AppConfig'].getboolean('autocompile', False)

    @property
    def smoothing(self) -> bool:
        return self.config['AppConfig'].getboolean('smoothing', False)

    @property
    def smoothing_treshhold(self) -> float:
        return self.config['AppConfig'].getfloat('smoothing threshold', 60.0)

    def __create_default_config(self):
        self.config['AppConfig'] = {
            'smoothing': 'no',
            'smoothing threshold': 60.0,
            'steam directory': r'C:\Program Files (x86)\Steam',
            'game config': 'halflife',
            'studiomdl': (r'%(steam directory)s\steamapps\common'
                          + r'\Sven Co-op SDK\modelling\studiomdl.exe'),
            'autocompile': 'yes',
            'wad list': ''
        }
        self.config['halflife'] = {
            'game': 'Half-Life',
            'mod': 'valve',
        }
        self.config['svencoop'] = {
            'game': 'Sven Co-op',
            'mod': 'svencoop',
        }
        self.config['cstrike'] = {
            'game': 'Half-Life',
            'mod': 'cstrike',
        }


if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
elif __file__:
    app_dir = os.path.dirname(__file__)

config = ConfigUtil(Path(app_dir) / 'config.ini')
