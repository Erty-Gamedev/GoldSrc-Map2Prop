# -*- coding: utf-8 -*-
"""
Created on Wed May 17 12:20:37 2023

@author: Erty
"""

import re
import os
import sys
import subprocess
import numpy as np
from pathlib import Path
from logutil import get_logger, shutdown_logger
from geoutil import Point, average_normals, average_near_normals
from configutil import config
from formats.obj_reader import ObjReader
from formats.rmf_reader import RmfReader


logger = get_logger(__name__)
enter_to_exit = 'Press Enter to exit...'

running_as_exe = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

try:
    filename = sys.argv[1]
except IndexError:
    if running_as_exe:
        logger.info('Attempted to run without providing file')
        input(enter_to_exit)
        raise Exception('No file provided')
    else:
        filename = r'test/cratetest.obj'

filepath = Path(filename)
extension = filepath.suffix.lower()

if extension == '.obj':
    filereader = ObjReader(filepath)
elif extension == '.rmf':
    filereader = RmfReader(filepath)
elif extension == '.jmf':
    raise Exception('Not yet supported')
else:
    logger.info(
        'Invalid file type. Must be .obj or .rmf, '
        + f"was {filepath.suffix}")
    if running_as_exe:
        input(enter_to_exit)
    raise ('File type must be .obj or .rmf!')


filedir = filepath.parents[0]
filename = filepath.stem
outputdir = filedir


# Create .smd
if not outputdir.is_dir():
    outputdir.mkdir()

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
        smooth_rad = np.deg2rad(smoothing)

        for point in filereader.allpolypoints:
            if point.v not in averaged_normals:
                averaged_normals[point.v] = average_near_normals(
                    filereader.vn_map[point.v], smooth_rad)
            point.n = averaged_normals[point.v][point.n]

    else:
        for point in filereader.allpolypoints:
            normals = filereader.vn_map[point.v]
            if not isinstance(normals, Point):
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
    for face in filereader.allfaces:
        output.write(f"{face.texture}.bmp\n")

        for p in face.polypoints:
            line = "0\t"
            if extension == '.obj':
                line += "{:.6f} {:.6f} {:.6f}\t".format(p.v.x, -p.v.z, p.v.y)
                line += "{:.6f} {:.6f} {:.6f}\t".format(p.n.x, -p.n.z, p.n.y)
                line += "{:.6f} {:.6f}".format(p.t.x, p.t.y + 1)
            else:
                line += "{:.6f} {:.6f} {:.6f}\t".format(p.v.x, p.v.y, p.v.z)
                line += "{:.6f} {:.6f} {:.6f}\t".format(p.n.x, p.n.y, p.n.z)
                line += "{:.6f} {:.6f}".format(p.t.x, p.t.y + 1)
            output.write(line + "\n")

    output.write('end' + "\n")
    logger.info(f"Successfully written to {outputdir / filename}.smd")


# Create .qc
with open(outputdir / f"{filename}.qc", 'w') as output:
    logger.info('Writing .qc file')

    rendermodes = ''
    if filereader.maskedtextures:
        for texture in filereader.maskedtextures:
            rendermodes += f"$texrendermode {texture}.bmp masked\n"

    output.write(f"""/*
 Automatically generated by Erty's Obj2GoldSmd.
*/

$modelname {filename}.mdl
$cd "."
$cdtexture "."
$scale 1.0
$origin 0 0 0 270
{rendermodes}$gamma 1.8
$body studio "{filename}"
$sequence idle "{filename}"
""")
    logger.info(f"Successfully written to {outputdir / filename}.qc")

if config.autocompile and config.studiomdl.is_file():
    if filereader.missing_textures:
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
            ], check=False, timeout=30, capture_output=True)

            logger.info(completed_process.stdout.decode('ascii'))

            if completed_process.returncode == 0:
                logger.info(
                    f"{outputdir / filename}.mdl compiled successfully!")
            else:
                logger.info(
                    'Something went wrong. Check the compiler output '
                    + 'above for errors.')
        except Exception:
            logger.exception('Model compilation failed with exception')


shutdown_logger(logger)

if running_as_exe:
    input(enter_to_exit)
