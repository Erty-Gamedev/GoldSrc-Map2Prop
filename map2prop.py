# -*- coding: utf-8 -*-
"""
GoldSrc Map2Prop is a tool for converting .map, .rmf and .jmf files,
as well as .obj files exported from J.A.C.K, to GoldSrc .smd file that
can then be compiled into a GoldSrc format studio model
without the hassle of using an 3D editor.

@author: Erty
"""

from typing import Final
import sys
from pathlib import Path
import logging
from logutil import setup_logger, shutdown_logger
from configutil import config
from formats import MissingTextureException
from formats.base_classes import BaseReader
from formats.export import process_models, rewrite_map


enter_to_exit = 'Press Enter to exit...'
running_as_exe: Final[bool] = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


class InvalidFileException(Exception):
    pass


def main() -> None:
    if config.input:
        filename = config.input
    else:
        if running_as_exe:
            logger.info('Please drag-and-drop a file onto the executable')
            config.app_exit(2)
        else:
            filename = r'test/cratetest.obj'

    logger.info(filename)

    filepath = Path(filename)
    extension = filepath.suffix.lower()

    filedir = filepath.parent
    filename = filepath.stem

    outputdir = filedir / config.output_dir
    if not outputdir.is_dir():
        outputdir.mkdir()

    filereader: BaseReader
    if extension == '.obj':
        from formats.obj_reader import ObjReader
        filereader = ObjReader(filepath, outputdir)
    elif extension == '.rmf':
        from formats.rmf_reader import RmfReader
        filereader = RmfReader(filepath, outputdir)
    elif extension == '.jmf':
        from formats.jmf_reader import JmfReader
        filereader = JmfReader(filepath, outputdir)
    elif extension == '.map':
        from formats.map_reader import MapReader
        filereader = MapReader(filepath, outputdir)
    else:
        logger.info('Invalid file type. Must be .map, .obj, .rmf, or .jmf, '\
                f"but was {extension}")
        raise InvalidFileException(
            'File type must be .map, .obj, .rmf, or .jmf!')

    returncode = process_models(filename, outputdir, filereader)

    if config.mapcompile:
        if returncode > 0:
            config.app_exit(3,'Something went wrong while compiling the models. '\
                            'Check the logs')
        else:
            rewrite_map(filepath, filereader)


if __name__ == '__main__':
    setup_logger()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    if not config:
        logger.error('Could not parse config file, exiting...')
        exit(2)

    try:
        main()
    except MissingTextureException as e:
        logger.info(str(e))
    except Exception as e:
        logger.exception(str(e))
        config.app_exit(1, str(e))
    finally:
        if running_as_exe and not config.autoexit:
            input(enter_to_exit)
        shutdown_logger(logger)
