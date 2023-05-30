# -*- coding: utf-8 -*-
"""
Created on Wed May 17 12:20:37 2023

@author: Erty
"""

import re
import sys
from logutil import get_logger, shutdown_logger
from pathlib import Path
import numpy as np
from geoutil import (Point, PolyPoint, PolyFace,
                     triangulate_face, average_normals, average_near_normals,
                     InvalidSolidException)
from wad3_reader import Wad3Reader


logger = get_logger(__name__)
enter_to_exit = 'Press Enter to exit...'


running_as_exe = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

try:
    filename = sys.argv[1]
except IndexError:
    if running_as_exe:
        logger.info('Attempted to run without providing file')
        input(enter_to_exit)
        raise RuntimeError('No file provided')
    else:
        filename = r'test/cratetest.obj'
filepath = Path(filename)

if filepath.suffix.lower() != '.obj':
    logger.info(f"Invalid file type. Must be .obj, was {filepath.suffix}")
    if running_as_exe:
        input(enter_to_exit)
    raise RuntimeError('File type must be .obj!')

filedir = filepath.parents[0]
filename = filepath.stem
outputdir = filedir

mtllib_prefix = 'mtllib '
mtl_prefix = 'newmtl '
mtl_map_prefix = 'map_Ka '

object_prefix = 'o '
group_prefix = 'g '
smooth_prefix = 's '
usemtl_prefix = 'usemtl '

vertex_prefix = 'v '            # (x y z)
texture_coord_prefix = 'vt '    # (u v w)
vertex_normal_prefix = 'vn '    # (x y z)
poly_face_prefix = 'f '         # (vertex_index/texture_index/normal_index)
# Note: The above indices are 1-indexed

coord_prefixes = [vertex_prefix, texture_coord_prefix, vertex_normal_prefix]

wads = None


def parseCoord(coord: str) -> list:
    coord = coord.split(' ')
    return Point(*[float(n) for n in coord])


def get_wads() -> list:
    global wads
    if wads is None:
        readers = []
        globs = filedir.glob('*.wad')
        for glob in globs:
            readers.append(Wad3Reader(glob))
        wads = readers
    return wads


def readMtlFile(filename: str) -> dict:
    materials = {}

    with open(filedir / filename) as mtlfile:
        current = ''
        for line in mtlfile:
            line = line.rstrip()

            if line.startswith('#'):
                continue
            elif line.startswith(mtl_prefix):
                current = line[len(mtl_prefix):]
            elif line.startswith(mtl_map_prefix):
                texture = line[len(mtl_map_prefix):].replace('.tga', '.bmp')
                if not (filedir / texture).exists():
                    logger.info(f"""\
Texture {texture} not found in .obj file's directory. \
Searching directory for .wad packages...""")
                    found = False
                    for wad in get_wads():
                        if current in wad:
                            logger.info(f"""\
Extracting {texture} from {wad.file}.""")
                            wad[current].save(filedir / texture)
                            found = True

                    if found is False:
                        logger.info(f"""\
Texture {texture} not found in neither .obj file's directory \
or any .wad packages within that directory. Please place the .wad package \
containing the texture in the .obj file's directory and re-run the \
application or extract the textures manually prior to compilation.""")
                materials[current] = texture

    return materials


materials = {}
vertices = []
textures = []
normals = []
objects = {}
allfaces = []
vn_map = {}
allpolypoints = []
maskedtextures = []
with filepath.open('r') as obj:
    current_obj = ''
    group = ''
    tex = ''
    logger.info(f"Opened {filepath}")

    for line in obj:
        line = line.rstrip()

        if line.startswith(mtllib_prefix):
            materials = readMtlFile(line[len(mtllib_prefix):])

        elif line.startswith(object_prefix):
            current_obj = line[len(object_prefix):]
            objects[current_obj] = {
                'smooth': 'off',
                'groups': {},
            }
        elif line.startswith(smooth_prefix):
            objects[current_obj]['smooth'] = line[len(smooth_prefix):]
        elif line.startswith(group_prefix):
            group = line[len(group_prefix):]
            objects[current_obj]['groups'][group] = {
                'faces': []
            }
        elif line.startswith(usemtl_prefix):
            tex = materials[line[len(usemtl_prefix):]]
            if tex.lower() == 'null.bmp':
                continue
            elif tex.startswith('{') and tex not in maskedtextures:
                maskedtextures.append(tex)
        elif line.startswith(poly_face_prefix):
            if tex.lower() == 'null.bmp':
                continue

            points = line[len(poly_face_prefix):].split(' ')

            verts = []
            polypoints = []
            for point in points:
                i_v, i_t, i_n = [int(n) for n in point.split('/')]
                polypoint = PolyPoint(
                    vertices[i_v - 1],
                    textures[i_t - 1],
                    normals[i_n - 1]
                )

                if polypoint.v not in vn_map:
                    vn_map[polypoint.v] = []
                vn_map[polypoint.v].append(polypoint.n)

                polypoints.append(polypoint)
                allpolypoints.append(polypoint)
                verts.append(vertices[i_v - 1])

            try:
                tris = triangulate_face(verts)
            except Exception:
                logger.exception('Face triangulation failed')
                raise

            for tri in tris:
                face = []
                for p in tri:
                    for polyp in polypoints:
                        if p == polyp.v:
                            face.append(polyp)
                            break

                try:
                    polyface = PolyFace(face, tex)
                except InvalidSolidException as ise:
                    logger.error(
                        f"Object had one or more invalid faces: {ise.message}"
                    )
                    raise

                allfaces.append(polyface)
                objects[current_obj]['groups'][group]['faces'].append(
                    PolyFace(face, tex)
                )

        elif line.startswith(vertex_prefix):
            coord = line[len(vertex_prefix):]
            vertices.append(parseCoord(coord))
        elif line.startswith(texture_coord_prefix):
            coord = line[len(texture_coord_prefix):]
            textures.append(parseCoord(coord))
        elif line.startswith(vertex_normal_prefix):
            coord = line[len(vertex_normal_prefix):]
            normals.append(parseCoord(coord))


# Create .smd
if not outputdir.is_dir():
    outputdir.mkdir()


if match := re.search(r'_smooth\d{0,3}$', filename, re.I):
    smoothing = match.group(0)[len('_smooth'):]
    if smoothing == '':
        smoothing = 0
    else:
        smoothing = int(smoothing)

    if smoothing > 0:
        averaged_normals = {}
        smooth_rad = np.deg2rad(smoothing)

        for point in allpolypoints:
            if point.v not in averaged_normals:
                averaged_normals[point.v] = average_near_normals(
                    vn_map[point.v], smooth_rad)
            point.n = averaged_normals[point.v][point.n]

    else:
        for point in allpolypoints:
            normals = vn_map[point.v]
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
    for face in allfaces:
        output.write(face.texture + "\n")

        for p in face.polypoints:
            line = "0\t"
            line += "{:.6f} {:.6f} {:.6f}\t".format(p.v.x, -p.v.z, p.v.y)
            line += "{:.6f} {:.6f} {:.6f}\t".format(p.n.x, -p.n.z, p.n.y)
            line += "{:.6f} {:.6f}".format(p.t.x, p.t.y + 1)
            output.write(line + "\n")

    output.write('end' + "\n")
    logger.info(f"Successfully written to {outputdir / filename}.smd")


# Create .qc
with open(outputdir / f"{filename}.qc", 'w') as output:
    logger.info('Writing .qc file')

    rendermodes = ''
    if maskedtextures:
        for texture in maskedtextures:
            rendermodes += f"$texrendermode {texture} masked\n"

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

logger.info('Finished!')

shutdown_logger(logger)

if running_as_exe:
    input(enter_to_exit)
