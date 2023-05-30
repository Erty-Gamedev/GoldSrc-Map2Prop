# -*- coding: utf-8 -*-
"""
Created on Tue May 30 21:59:28 2023

@author: Erty
"""

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
        return Path(self.config['AppConfig']['studiomdl'])

    @property
    def mod_path(self) -> Path:
        game = self.config['AppConfig']['game config']
        mod = f"{self.config[game]['game']}\\{self.config[game]['mod']}"
        return (Path(self.config['AppConfig']['steam directory'])
                / f"steamapps\\common\\{mod}")

    @property
    def wad_list(self) -> list:
        wads = (self.config['AppConfig']['wad list'].rstrip(' ,')
                .replace("\n", '').split(','))
        return [Path(wad) for wad in wads]

    @property
    def autocompile(self) -> bool:
        return self.config['AppConfig'].getboolean('autocompile')

    def __create_default_config(self):
        self.config['AppConfig'] = {
            'smoothing': 'no',
            'smoothing threshold': 60,
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


config = ConfigUtil(Path(__file__).parent / 'config.ini')
