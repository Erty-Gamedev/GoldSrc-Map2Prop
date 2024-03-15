# -*- coding: utf-8 -*-
"""
Created on Wed May 17 12:20:37 2023

@author: Erty
"""

import re
import os
import sys
import subprocess
from pathlib import Path
from logutil import get_logger, shutdown_logger
from geoutil import (Vector3D, PolyFace, average_normals,
                     average_near_normals, deg2rad)
from configutil import config
from formats import InvalidFormatException, MissingTextureException
from formats.base_reader import BaseReader


enter_to_exit = 'Press Enter to exit...'
running_as_exe = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


class InvalidFileException(Exception):
    pass


def main():

    try:
        config.parseargs()
        filename = config.input
    except IndexError:
        if running_as_exe:
            logger.info('Attempted to run without providing file')
            if not config.autoexit:
                input(enter_to_exit)
            config.app_exit(2, 'Attempted to run without providing file')
        else:
            filename = r'test/cratetest.obj'

    filepath = Path(filename)
    extension = filepath.suffix.lower()

    filedir = filepath.parents[0]
    filename = filepath.stem

    if config.output_dir is not None:
        outputdir = config.output_dir
    else:
        outputdir = Path('.')

    outputdir = filedir / outputdir

    # Create .smd
    if not outputdir.is_dir():
        outputdir.mkdir()

    filereader: BaseReader
    try:
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
            logger.info(
                'Invalid file type. Must be .obj, .rmf, or .jmf, but '
                + f"was {filepath.suffix}")
            raise InvalidFileException(
                'File type must be .obj, .rmf, or .jmf!')
    except MissingTextureException as e:
        logger.info(str(e))
        raise e
    except InvalidFormatException as e:
        logger.error(str(e))
        raise e
    except ValueError as e:
        logger.error(str(e))
        raise e

    smooth = False
    smoothing = 0.0
    if config.smoothing:
        smooth = True
        smoothing = config.smoothing_treshhold

    # If set with filename, let it override config
    if match := re.search(r'_smooth\d{0,3}$', filename, re.I):
        smooth = True
        smoothing = match.group(0)[len('_smooth'):]
        if smoothing == '':
            smoothing = 0.0
        else:
            smoothing = int(smoothing)

    if smooth:
        if smoothing > 0.0:
            averaged_normals = {}
            smooth_rad = deg2rad(smoothing)

            for point in filereader.allvertices:
                if point.v not in averaged_normals:
                    averaged_normals[point.v] = average_near_normals(
                        filereader.vn_map[point.v], smooth_rad)
                point.n = averaged_normals[point.v][point.n]

        else:
            for point in filereader.allvertices:
                normals = filereader.vn_map[point.v]
                if not isinstance(normals, Vector3D):
                    normals = average_normals(normals)
                point.n = normals

    with open(outputdir / f"{filename}.smd", 'w') as output:
        logger.info('Writing .smd file')

        output.write('''version 1
nodes
0 "root" -1
end
skeleton
time 0
0 0 0 0 0 0 0
end
triangles
''')

        face: PolyFace
        for face in filereader.allfaces:
            output.write(f"{face.texture}.bmp\n")

            for v in face.vertices:
                line = "0\t"
                if extension == '.obj':
                    line += (
                        "{:.6f} {:.6f} {:.6f}\t".format(v.v.x, -v.v.z, v.v.y))
                    line += (
                        "{:.6f} {:.6f} {:.6f}\t".format(v.n.x, -v.n.z, v.n.y))
                    line += "{:.6f} {:.6f}".format(v.t.x, v.t.y + 1)
                else:
                    line += (
                        "{:.6f} {:.6f} {:.6f}\t".format(v.v.x, v.v.y, v.v.z))
                    line += (
                        "{:.6f} {:.6f} {:.6f}\t".format(v.n.x, v.n.y, v.n.z))
                    line += "{:.6f} {:.6f}".format(v.t.x, v.t.y + 1)
                output.write(line + "\n")

        output.write('end' + "\n")
        logger.info(f"Successfully written to {outputdir / filename}.smd")

    modelname = config.qc_outname if config.qc_outname else filename

    # Create .qc
    with open(outputdir / f"{filename}.qc", 'w') as output:
        logger.info('Writing .qc file')

        rendermodes = ''
        if filereader.maskedtextures:
            for texture in filereader.maskedtextures:
                rendermodes += f"$texrendermode {texture}.bmp masked\n"

        output.write(f"""/*
 Automatically generated by Erty's GoldSrc Map2Prop.
*/

$modelname {modelname}.mdl
$cd "."
$cdtexture "."
$scale {config.qc_scale}
$origin {config.qc_offset} {config.qc_rotate}
{rendermodes}$gamma {config.qc_gamma}
$body studio "{filename}"
$sequence "Generated_with_Erty's_Map2Prop" "{filename}"
""")
        logger.info(f"Successfully written to {outputdir / filename}.qc")

    if config.autocompile:
        if not config.studiomdl or not config.studiomdl.is_file():
            logger.info(
                'Autocompile enabled, but could not proceed. '
                + f"{config.studiomdl} was not found or is not a file.")
        elif filereader.missing_textures:
            logger.info(
                'Autocompile enabled, but could not proceed. '
                + 'Model has missing textures. Check logs for more info.')
        else:
            logger.info('Autocompile enabled, compiling model...')

            os.chdir(outputdir.absolute())

            try:
                completed_process = subprocess.run([
                    config.studiomdl,
                    Path(f"{filename}.qc"),
                ], check=False, timeout=config.timeout, capture_output=True)

                logger.info(completed_process.stdout.decode('ascii'))

                if completed_process.returncode == 0:
                    logger.info(
                        f"{outputdir / modelname}.mdl compiled successfully!")
                else:
                    logger.info(
                        'Something went wrong. Check the compiler output '
                        + 'above for errors.')
            except Exception:
                logger.exception('Model compilation failed with exception')


if __name__ == '__main__':
    logger = get_logger(__name__)
    if config is None:
        logger.error('Could not parse config file, exiting...')
        exit(2)

    try:
        main()
    except Exception as e:
        config.app_exit(1, str(e))
    finally:
        if running_as_exe and not config.autoexit:
            input(enter_to_exit)
        shutdown_logger(logger)
