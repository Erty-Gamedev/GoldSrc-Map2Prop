# -*- coding: utf-8 -*-
"""
Utility class for arguments and config file parsing.

@author: Erty
"""

from typing import Optional, List
import os
import sys
import argparse
import configparser
import logging
from dataclasses import dataclass
from logutil import shutdown_logger
from pathlib import Path


VERSION = '0.9.0-beta'


@dataclass
class Args:
    input: Optional[str] = None
    output: Optional[str] = None
    game_config: Optional[str] = None
    studiomdl: Optional[str] = None
    wad_list: Optional[str] = None
    wad_cache: Optional[int] = None
    smoothing: Optional[float] = None
    autocompile: Optional[bool] = False
    timeout: Optional[float] = None
    autoexit: Optional[bool] = False
    outputname: Optional[str] = None
    scale: Optional[float] = None
    gamma: Optional[float] = None
    offset: Optional[List[float]] = None
    rotate: Optional[float] = None


class ConfigUtil:
    def __init__(self, filepath: Path) -> None:
        self.config = configparser.ConfigParser()
        if filepath.exists():
            self.config.read(filepath)
        else:
            self.create_default_config()
            with filepath.open('w') as configfile:
                self.config.write(configfile)

        self.parser = argparse.ArgumentParser(
            prog='GoldSrc Map2Prop',
            description='Converts a .map/.rmf/.jmf or J.A.C.K .obj into '\
                'goldsrc .smd files for model creation.',
            exit_on_error=False
        )

        self.parseargs()

    def app_exit(self, status: int = 0, message: str = '') -> None:
        self.parser.exit(status, message)

    def parseargs(self) -> None:
        self.parser.add_argument('input', nargs='?', type=str,
                                 help='.map/.rmf/.jmf/.obj file to convert')
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
            '-s', '--smoothing', type=float, default=60.0, metavar='',
            help='angle threshold for applying smoothing '\
                '(use 0.0 to smooth all edges)')
        general.add_argument(
            '-a', '--autocompile', action='store_true',
            help='compile model after conversion')
        general.add_argument(
            '-t', '--timeout', type=float, default=60.0, metavar='',
            help='timeout for running studiomdl.exe (default %(default)s)')
        general.add_argument(
            '-x', '--autoexit', action='store_true',
            help='don\'t ask for input after finish')

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
        
        misc = self.parser.add_argument_group('misc options')
        misc.add_argument(
            '--renamechrome', action='store_true',
            help='rename chrome textures (disables chrome)'
        )
        self.input = self.args.input

    @property
    def qc_outname(self) -> str:
        return self.args.outputname if self.args.outputname else ''

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
        return Path(path) if path else Path('.')

    @property
    def game_config(self) -> str:
        if self.args.game_config:
            return self.args.game_config
        return self.config['AppConfig'].get('game config', '')

    @property
    def studiomdl(self) -> Optional[Path]:
        if self.args.studiomdl:
            return Path(self.args.studiomdl)
        if studiomdl := (self.config['AppConfig'].get('studiomdl', None)):
            return Path(studiomdl) if studiomdl else None
        return None

    @property
    def mod_path(self) -> Optional[Path]:
        game = self.game_config
        steamdir = self.config['AppConfig'].get('steam directory', None)

        if not game or not steamdir:
            return None

        return (Path(steamdir) / r'steamapps/common'
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
        return bool(self.args.autocompile
                or self.config['AppConfig'].getboolean('autocompile', False))

    @property
    def timeout(self) -> float:
        if self.args.timeout:
            return self.args.timeout
        return self.config['AppConfig'].getfloat('timeout', 60.0)

    @property
    def autoexit(self) -> bool:
        if self.args.autoexit:
            return self.args.autoexit
        return self.config['AppConfig'].getboolean('autoexit', False)

    @property
    def smoothing(self) -> bool:
        return bool(self.args.smoothing
                    or self.config['AppConfig'].getboolean('smoothing', False))

    @property
    def smoothing_treshhold(self) -> float:
        if self.args.smoothing:
            return self.args.smoothing
        return self.config['AppConfig'].getfloat('smoothing threshold', 60.0)
    
    @property
    def renamechrome(self) -> bool:
        return bool(self.args.renamechrome
                    or self.config['AppConfig'].getboolean('rename chrome', False))

    def create_default_config(self):
        self.config['AppConfig'] = {
            'smoothing': 'no',
            'smoothing threshold': 60.0,
            'rename chrome': 'no',
            'output directory': r'/converted',
            'steam directory': r'C:/Program Files (x86)/Steam',
            'game config': 'halflife',
            'wad cache': 10,
            'studiomdl': (r'%(steam directory)s/steamapps/common'\
                          r'/Sven Co-op SDK/modelling/studiomdl.exe'),
            'autocompile': 'yes',
            'autoexit': 'no',
            'timeout': 60.0,
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

logger = logging.getLogger(__name__)
try:
    config: ConfigUtil = ConfigUtil(Path(app_dir) / 'config.ini')
except configparser.DuplicateOptionError as e:
    logger.exception('Config file parsing failed.')
    logger.info('If using wad_list in config.ini, make sure each '\
                "consequtive line is left-aligned with the first line.\n")
    raise e
except Exception as e:
    logger.exception('Config file parsing failed.')
    raise e
shutdown_logger(logger)
