# -*- coding: utf-8 -*-
"""
Created on Tue May 30 21:59:28 2023

@author: Erty
"""

import os
import sys
import argparse
import configparser
from logutil import get_logger, shutdown_logger
from pathlib import Path


VERSION = '0.8.2-beta'


class ConfigUtil:
    def __init__(self, filepath: Path):
        self.args = None
        self.config = configparser.ConfigParser()
        if filepath.exists():
            self.config.read(filepath)
        else:
            self.__create_default_config()
            with filepath.open('w') as configfile:
                self.config.write(configfile)

        self.parser = argparse.ArgumentParser(
            prog='GoldSrc Map2Prop',
            description='Converts a .rmf/.jmf or J.A.C.K .obj into goldsrc\
.smd files for model creation.',
            exit_on_error=False
        )

    def app_exit(self, status: int = 0, message: str = ''):
        self.parser.exit(status, message)

    def parseargs(self, running_as_exe: bool):
        if True or running_as_exe:
            self.parser.add_argument('input', nargs='?', type=str,
                                     help='.rmf/.jmf/.obj file to convert')
        self.parser.add_argument(
            '-v', '--version', action='version', version=f"%(prog)s {VERSION}",
            help='display current version')

        general = self.parser.add_argument_group('general arguments')
        general.add_argument(
            '-o', '--output', type=str, metavar='',
            help='specify an output directory')
        general.add_argument(
            '-g', '--game_config', type=str, metavar='',
            help='game setup to use from config.ini')
        general.add_argument(
            '-m', '--studiomdl', type=str, metavar='',
            help='path to SC studiomdl.exe')
        general.add_argument(
            '-w', '--wad_list', type=str, metavar='',
            help='path to text file listing .wad files')
        general.add_argument(
            '-c', '--wad_cache', type=int, metavar='',
            help='max number of .wad files to keep in memory',)
        general.add_argument(
            '-s', '--smoothing', type=float, default=0.0, metavar='',
            help='angle threshold for applying smoothing '
                 + '(use %(default)s to smooth all edges)')
        general.add_argument(
            '-a', '--autocompile', action='store_true',
            help='compile model after conversion')

        qc = self.parser.add_argument_group('.qc options')
        qc.add_argument(
            '--outputname', type=str, metavar='',
            help='filename for the finished model')
        qc.add_argument(
            '--scale', type=float, metavar='1.0',
            help='scale the model by this amount')
        qc.add_argument(
            '--gamma', type=float, metavar='1.8', default=1.8,
            help='darken/brighten textures (default %(default)s)')
        qc.add_argument(
            '--offset', nargs=3, metavar=('x', 'y', 'z'),
            help='X Y Z offset to apply to the model')
        qc.add_argument(
            '--rotate', type=float, metavar='0.0',
            help='rotate the model by this many degrees')

        self.args = self.parser.parse_args()
        if self.args.input is None:
            raise IndexError()
        self.input = self.args.input

    @property
    def qc_outname(self) -> str:
        return self.args.outputname if self.args.outputname else None

    @property
    def qc_scale(self) -> float:
        return self.args.scale if self.args.scale else 1.0

    @property
    def qc_gamma(self) -> float:
        return self.args.gamma if self.args.gamma else 1.8

    @property
    def qc_offset(self) -> str:
        if self.args.offset:
            return ' '.join([f"{i}" for i in self.args.offset])
        return '0 0 0'

    @property
    def qc_rotate(self) -> float:
        return (270.0 + (self.args.rotate if self.args.rotate else 0.0)) % 360

    @property
    def output_dir(self) -> Path:
        if self.args.output:
            path = self.args.output
        else:
            path = self.config['AppConfig'].get('output directory', None)
        return path if path is None else Path(path)

    @property
    def game_config(self) -> str:
        if self.args.game_config:
            return self.args.game_config
        return self.config['AppConfig'].get('game config', False)

    @property
    def studiomdl(self) -> Path:
        if self.args.studiomdl:
            return Path(self.args.studiomdl)
        if studiomdl := (self.config['AppConfig'].get('studiomdl', False)):
            return Path(studiomdl)
        return None

    @property
    def mod_path(self) -> Path:
        game = self.game_config
        steamdir = self.config['AppConfig'].get('steam directory', False)

        if not game or not steamdir:
            return None

        return (Path(steamdir) / r'steamapps\common'
                / self.config[game].get('game')
                / self.config[game].get('mod'))

    @property
    def wad_list(self) -> list:
        if self.args.wad_list:
            with Path(self.args.wad_list).open('r') as file:
                return [Path(wad.rstrip()) for wad
                        in list(file) if wad.rstrip() != '']
        wads = (self.config['AppConfig'].get('wad list', '').rstrip(' ,')
                .replace("\n", '').split(','))
        return [Path(wad) for wad in wads if wad != '']

    @property
    def wad_cache(self) -> int:
        if self.args.wad_cache:
            return self.args.wad_cache
        return self.config['AppConfig'].getint('wad cache', 10)

    @property
    def autocompile(self) -> bool:
        return (self.args.autocompile
                or self.config['AppConfig'].getboolean('autocompile', False))

    @property
    def smoothing(self) -> bool:
        return bool(self.args.smoothing
                    or self.config['AppConfig'].getboolean('smoothing', False))

    @property
    def smoothing_treshhold(self) -> float:
        if self.args.smoothing:
            return self.args.smoothing
        return self.config['AppConfig'].getfloat('smoothing threshold', 60.0)

    def __create_default_config(self):
        self.config['AppConfig'] = {
            'smoothing': 'no',
            'smoothing threshold': 60.0,
            'output directory': r'\converted',
            'steam directory': r'C:\Program Files (x86)\Steam',
            'game config': 'halflife',
            'wad cache': 10,
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

logger = get_logger(__name__)
try:
    config = ConfigUtil(Path(app_dir) / 'config.ini')
except configparser.DuplicateOptionError:
    logger.exception('Config file parsing failed.')
    logger.info('If using wad_list in config.ini, make sure each '
                + "consequtive line is left-aligned with the first line.\n")
    config = None
except Exception:
    logger.exception('Config file parsing failed.')
    config = None
shutdown_logger(logger)
