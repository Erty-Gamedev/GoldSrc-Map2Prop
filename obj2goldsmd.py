# -*- coding: utf-8 -*-
"""
Created on Wed May 17 12:20:37 2023

@author: Erty
"""

import sys
import logging
from datetime import datetime
from pathlib import Path
from geoutil import (Point, PolyPoint, ObjItem,
                     PolyFace, triangulate_face, InvalidSolidException)


enter_to_exit = 'Press Enter to exit...'


logdir = Path('logs')
if not logdir.is_dir():
    logdir.mkdir()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

now = datetime.now()
filelog = logging.FileHandler(
    logdir / f"error_{now.strftime('%Y-%m-%d')}.log")
filelog.setLevel(logging.WARNING)
filelog.setFormatter(
    logging.Formatter('%(asctime)s | %(levelname)-8s : %(message)s')
)

conlog = logging.StreamHandler()
conlog.setLevel(logging.INFO)
conlog.setFormatter(
    logging.Formatter('%(levelname)-8s : %(message)s')
)

logger.addHandler(filelog)
logger.addHandler(conlog)


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


def parseCoord(coord: str) -> list:
    coord = coord.split(' ')
    return Point(*[float(n) for n in coord])


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
Make sure it exists prior to attempting compiling the model.""")
                materials[current] = texture

    return materials


materials = {}
vertices = []
textures = []
normals = []
objects = {}
allfaces = []
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
                polypoints.append(PolyPoint(
                    ObjItem(i_v, vertices[i_v - 1]),
                    ObjItem(i_t, textures[i_t - 1]),
                    ObjItem(i_n, normals[i_n - 1])
                ))
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
                        if p == polyp.v.v:
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
            line += "{:.6f} {:.6f} {:.6f}\t".format(p.v.v.x, -p.v.v.z, p.v.v.y)
            line += "{:.6f} {:.6f} {:.6f}\t".format(p.n.v.x, -p.n.v.z, p.n.v.y)
            line += "{:.6f} {:.6f}".format(p.t.v.x, p.t.v.y)
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
logging.shutdown()

if running_as_exe:
    input(enter_to_exit)
