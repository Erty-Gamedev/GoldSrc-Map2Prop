"""
Utility class for arguments and config file parsing.
"""

from typing import Optional, List, Self
import os
import sys
import argparse
import configparser
import logging
import dataclasses
from logutil import shutdown_logger
from pathlib import Path


VERSION = '1.2.0'


@dataclasses.dataclass
class Args:
    """To help with typing"""
    input:        Optional[str] = None
    output:       Optional[str] = None
    mapcompile:   bool = False
    force_rmf:    bool = False
    force_jmf:    bool = False
    game_config:  Optional[str] = None
    studiomdl:    Optional[str] = None
    wad_list:     Optional[str] = None
    wad_cache:    Optional[int] = None
    smoothing:    Optional[float] = None
    autocompile:  bool = False
    timeout:      Optional[float] = None
    autoexit:     bool = False
    outputname:   Optional[str] = None
    scale:        Optional[float] = None
    gamma:        Optional[float] = None
    offset:       Optional[List[float]] = None
    rotate:       Optional[float] = None
    renamechrome: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        fields: List[str] = [f.name for f in dataclasses.fields(cls)]
        new_d = {}
        for key, value in d.items():
            if key in fields:
                new_d[key] = value
        return cls(**new_d)


class ConfigUtil:
    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath

        self._input:         Optional[str] = None
        self._output:        Path = Path('.')
        self._debug:         bool = False
        self._mapcompile:    bool = False
        self._force_rmf:     bool = False
        self._force_jmf:     bool = False
        self._game_config:   str = ''
        self._steamdir:      Optional[Path] = None
        self._studiomdl:     Optional[Path] = None
        self._wad_list:      List[Path] = []
        self._wad_cache:     int = 10
        self._smoothing:     float = 60.0
        self._autocompile:   bool = True
        self._timeout:       float = 60.0
        self._autoexit:      bool = False
        self._qc_outputname: str = ''
        self._qc_scale:      float = 1.0
        self._qc_gamma:      float = 1.8
        self._qc_offset:     str = '0 0 0'
        self._qc_rotate:     float = 270.0
        self._renamechrome:  bool = False
        self._eager:         bool = False

        self.load_configini()
        self.argparser = argparse.ArgumentParser(
            prog='Map2Prop',
            description='Converts a .map/.rmf/.jmf/.ol or J.A.C.K .obj into '\
                'goldsrc .smd files for model creation.',
            exit_on_error=False
        )
        self.load_args()
        self.read_configs()

    def app_exit(self, status: int = 0, message: str = '') -> None:
        self.argparser.exit(status, message)

    def load_configini(self) -> None:
        self.configini = configparser.ConfigParser(default_section='default')
        if self.filepath.exists():
            self.configini.read(self.filepath)
        else:
            self.create_default_config()
            with self.filepath.open('w') as configfile:
                self.configini.write(configfile)

    def load_args(self) -> None:
        self.argparser.add_argument('input', nargs='?', type=str,
                                 help='.map/.rmf/.jmf/.obj/.ol file to convert')
        self.argparser.add_argument(
            '-v', '--version', action='version', version=f"%(prog)s {VERSION}",
            help='display current version')
        self.argparser.add_argument(
            '-a', '--autocompile', action='store_true',
            help='compile model after conversion')
        self.argparser.add_argument(
            '-x', '--autoexit', action='store_true',
            help='don\'t ask for input after finish')
        self.argparser.add_argument(
            '-c', '--mapcompile', action='store_true',
            help='modify .map input to replace func_map2prop with model entities after compile'
        )

        forceformat = self.argparser.add_mutually_exclusive_group()
        forceformat.add_argument(
            '--forcermf', action='store_true',
            help='when using --mapcompile forces the use of the .rmf file as input instead of .map'
        )
        forceformat.add_argument(
            '--forcejmf', action='store_true',
            help='when using --mapcompile forces the use of the .jmf file as input instead of .map'
        )

        general = self.argparser.add_argument_group('general arguments')
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
            '-n', '--wad_cache', type=int, metavar='',
            help='max number of .wad files to keep in memory',)
        general.add_argument(
            '-s', '--smoothing', type=float, default=60.0, metavar='',
            help='angle threshold for applying smoothing '\
                '(use 0.0 to smooth all edges)')
        general.add_argument(
            '-t', '--timeout', type=float, default=60.0, metavar='',
            help='timeout for running studiomdl.exe (default %(default)s)')

        qc = self.argparser.add_argument_group('.qc options')
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
        
        misc = self.argparser.add_argument_group('misc options')
        misc.add_argument(
            '--renamechrome', action='store_true',
            help='rename chrome textures (disables chrome)'
        )
        misc.add_argument(
            '--eager', action='store_true',
            help='use eager triangulation algorithm (faster)'
        )

        self.args = Args.from_dict(vars(self.argparser.parse_args()))

    def read_configs(self) -> None:
        """Make sure we read configs and args in the correct order.
        CLI args should be prioritised over config.ini settings."""

        if self.args.game_config:
            self._game_config = self.args.game_config
        else:
            self._game_config = self.configini['default'].get('game config', 'default')

        configini = self.configini[self.game_config]

        steamdir = configini.get('steam directory', None)
        self._steamdir = Path(steamdir) if steamdir else None

        self._input = self.args.input

        if self.args.output:
            self._output = Path(self.args.output)
        else:
            self._output = Path(configini.get('output directory', '.'))

        self._debug = configini.getboolean('debug', False)

        self._mapcompile = self.args.mapcompile
        self._force_rmf = self.args.force_rmf
        self._force_jmf = self.args.force_jmf

        if self.args.studiomdl:
            self._studiomdl = Path(self.args.studiomdl)
        elif studiomdl := (configini.get('studiomdl', None)):
            self._studiomdl = Path(studiomdl)

        if self.args.wad_list:
            with Path(self.args.wad_list).open('r') as file:
                self._wad_list = [Path(wad.rstrip()) for wad
                                  in list(file) if wad.rstrip() != '']
        else:
            self._wad_list = [Path(wad) for wad in configini.get('wad list', '')
                              .rstrip(' ,').replace("\n", '').split(',') if wad]
        
        if self.args.wad_cache:
            self._wad_cache = self.args.wad_cache
        else:
            self._wad_cache = configini.getint('wad cache', 10)

        if self.args.smoothing:
            self._smoothing = self.args.smoothing
        else:
            self._smoothing = configini.getfloat('smoothing threshold', 60.0)

        self._autocompile = self.args.autocompile or configini.getboolean('autocompile', False)

        if self.args.timeout:
            self._timeout = self.args.timeout
        else:
            self._timeout = configini.getfloat('timeout', 60.0)
        
        self._autoexit = self.mapcompile or self.args.autoexit or configini.getboolean('autoexit', False) 
        
        if self.args.outputname:
            self._qc_outputname = self.args.outputname
        else:
            self._qc_outputname = ''

        self._qc_scale = self.args.scale if self.args.scale else 1.0

        self._qc_gamma = self.args.gamma if self.args.gamma else 1.8

        if self.args.offset:
            self._qc_offset = ' '.join([f"{i}" for i in self.args.offset])

        if self.args.rotate:
            self._qc_rotate = (270.0 + self.args.rotate) % 360

        self._renamechrome = self.args.renamechrome or configini.getboolean('rename chrome', False)

    @property
    def input(self) -> Optional[str]: return self._input
    @property
    def output_dir(self) -> Path: return self._output
    @property
    def debug(self) -> bool: return self._debug
    @property
    def mapcompile(self) -> bool: return self._mapcompile
    @property
    def force_rmf(self) -> bool: return self._force_rmf
    @property
    def force_jmf(self) -> bool: return self._force_jmf
    @property
    def game_config(self) -> str: return self._game_config
    @property
    def steamdir(self) -> Optional[Path]: return self._steamdir
    @property
    def studiomdl(self) -> Optional[Path]: return self._studiomdl
    @property
    def wad_list(self) -> List[Path]: return self._wad_list
    @property
    def wad_cache(self) -> int: return self._wad_cache
    @property
    def smoothing(self) -> float: return self._smoothing
    @property
    def autocompile(self) -> bool: return self._autocompile
    @property
    def timeout(self) -> float: return self._timeout
    @property
    def autoexit(self) -> bool: return self._autoexit
    @property
    def qc_outputname(self) -> str: return self._qc_outputname
    @property
    def qc_scale(self) -> float: return self._qc_scale
    @property
    def qc_gamma(self) -> float: return self._qc_gamma
    @property
    def qc_offset(self) -> str: return self._qc_offset
    @property
    def qc_rotate(self) -> float: return self._qc_rotate
    @property
    def renamechrome(self) -> bool: return self._renamechrome
    @property
    def eager(self) -> bool: return self._eager

    @property
    def mod_path(self) -> Optional[Path]:
        game = self.game_config

        if not game or not self.steamdir:
            return None

        return (self.steamdir / r'steamapps/common'
                / self.configini[game].get('game', '')
                / self.configini[game].get('mod', ''))

    def create_default_config(self):
        self.configini['default'] = {
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
        self.configini['halflife'] = {
            'game': 'Half-Life',
            'mod': 'valve',
        }
        self.configini['svencoop'] = {
            'game': 'Sven Co-op',
            'mod': 'svencoop',
        }
        self.configini['cstrike'] = {
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
