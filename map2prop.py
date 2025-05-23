"""
GoldSrc Map2Prop is a tool for converting .map, .rmf, .jmf, and .ol files,
as well as .obj files exported from J.A.C.K, to GoldSrc .smd file that
can then be compiled into a GoldSrc format studio model
without the hassle of using an 3D editor.
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

setup_logger()
logger = logging.getLogger(__name__)

RUNNING_AS_EXE: Final[bool] = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


class InvalidFileException(Exception):
    pass


def main() -> None:
    if not config.input:
        config.argparser.print_help()
        return config.app_exit(2)

    filename = config.input
    filepath = Path(filename)

    if config.mapcompile:
        if config.force_rmf:
            filepath = filepath.parent / f"{filepath.stem}.rmf"
        elif config.force_jmf:
            filepath = filepath.parent / f"{filepath.stem}.jmf"

    extension = filepath.suffix.lower()

    if not filepath.exists():
        if extension.strip() == '' and Path(f"{filename}.map").exists():
            filepath = Path(f"{filename}.map")
            extension = '.map'
        else:
            raise FileNotFoundError(f"Input file {filename} was not found")

    if config.mapcompile and (extension in ('.obj', '.ol')):
        raise InvalidFileException('Invalid file type. '\
            '--mapcompile can only be used with map formats, '\
            f"but file was {extension}")

    logger.info(filepath)
    if config.mapcompile:
        logger.info('Using --mapcompile')

    filedir = filepath.parent
    filename = filepath.stem

    if config.mapcompile:
        if not config.mod_path or not config.mod_path.exists():
            raise NotADirectoryError('Mod folder not configured or does not exist '\
                        f" for game config '{config.game_config}'. "\
                        'Check config.ini')

        outputdir = (config.mod_path / 'models') / config.output_dir
    else:
        outputdir = filedir / config.output_dir
    if not outputdir.is_dir():
        outputdir.mkdir()

    if config.eager:
        import ear_clip
        ear_clip.IS_EAGER = True

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
    elif extension == '.ol':
        from formats.ol_reader import OLReader
        libary_reader = OLReader(filepath, outputdir)

        logger.info(f"Finished reading prefab library, "\
                    f"proceeding to convert {libary_reader.dir_num_entries} models")

        for prefabname, filereader in libary_reader.rmf_files.items():
            returncode = process_models(prefabname, outputdir, filereader)
            if returncode > 0:
                logger.warning(
                    f"Something went wrong with compiling prefab \"{prefabname}\" "\
                    f"in {filepath}")
        return
    else:
        logger.info('Invalid file type. Must be .map, .obj, .rmf, .jmf, or .ol '\
                f"but was {extension}")
        raise InvalidFileException(
            'File type must be .map, .obj, .rmf, .jmf or .ol!')

    returncode = process_models(filename, outputdir, filereader)

    if config.mapcompile:
        if returncode > 0:
            config.app_exit(3,'Something went wrong while compiling the models. '\
                            'Check the logs')
        else:
            rewrite_map(filepath, filereader)


if __name__ == '__main__':
    if not config:
        logger.error('Could not parse config file, exiting...')
        exit(2)
    
    logger.setLevel(logging.DEBUG if config.debug else logging.INFO)

    try:
        main()
    except MissingTextureException as e:
        logger.info(str(e))
    except Exception as e:
        logger.exception(str(e))
        config.app_exit(1, str(e))
    finally:
        if RUNNING_AS_EXE and not config.autoexit:
            input('Press Enter to exit...')
        shutdown_logger(logger)
