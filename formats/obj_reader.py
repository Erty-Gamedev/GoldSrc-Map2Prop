# -*- coding: utf-8 -*-
"""
Created on Tue May 30 10:40:33 2023

@author: Erty
"""

from pathlib import Path
from logutil import get_logger, shutdown_logger
from geoutil import (Point, PolyPoint, PolyFace,
                     InvalidSolidException, triangulate_face)
from formats.wad3_reader import Wad3Reader
from configutil import config


WAD_SKIP_LIST = [
    'cached',
    'decals',
    'fonts',
    'gfx',
    'spraypaint',
    'tempdecal',
]
SKIP_TEXTURES = [
    'aaatrigger', 'bevel', 'black_hidden',
    'clip', 'clipbevel', 'clipbevelbrush',
    'cliphull1', 'cliphull2', 'cliphull3',
    'contentempty', 'hint', 'noclip', 'null',
    'skip', 'sky', 'solidhint'
]


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


def parseCoord(coord: str) -> list:
    coord = coord.split(' ')
    return Point(*[float(n) for n in coord])


class ObjReader:
    __wads = None

    def __init__(self, filepath: Path):
        self.filepath = filepath

        self.vertexcoords = []
        self.texturecoords = []
        self.normalcoords = []

        self.textures = []
        self.objects = {}
        self.maskedtextures = []
        self.allfaces = []
        self.allpolypoints = []
        self.vn_map = {}

        self.__logger = get_logger(__name__)
        self.__filedir = self.filepath.parents[0]

        self.__readfile()

        shutdown_logger(self.__logger)

    @classmethod
    def __get_wads(cls, filedir: Path) -> list:
        if cls.__wads is None:
            cls.__wads = []

            if config.wad_list:
                for wad in config.wad_list:
                    cls.__wads.append(Wad3Reader(wad))
                return cls.__wads

            checked_wads = []

            if config.mod_path:
                globs = config.mod_path.glob('*.wad')
                for glob in globs:
                    if glob.stem.lower() in WAD_SKIP_LIST:
                        continue
                    cls.__wads.append(Wad3Reader(glob))
                    checked_wads.append(glob.stem)

            globs = filedir.glob('*.wad')
            for glob in globs:
                if glob.stem.lower() in WAD_SKIP_LIST or (
                        glob.stem in checked_wads):
                    continue
                cls.__wads.append(Wad3Reader(glob))
        return cls.__wads

    def __check_texture(self, texture: str) -> str:
        texfile = f"{texture}.bmp"
        if not (self.__filedir / texfile).exists():
            self.__logger.info(f"""\
Texture {texture}.bmp not found in .obj file's directory. \
Searching directory for .wad packages...""")
            found = False
            for wad in self.__class__.__get_wads(self.__filedir):
                if texture in wad:
                    self.__logger.info(f"""\
Extracting {texture} from {wad.file}.""")
                    wad[texture].save(self.__filedir / texfile)
                    found = True

            if found is False:
                self.__logger.info(f"""\
Texture {texture} not found in neither .obj file's directory \
or any .wad packages within that directory. Please place the .wad package \
containing the texture in the .obj file's directory and re-run the \
application or extract the textures manually prior to compilation.""")

    def __readfile(self):
        with self.filepath.open('r') as objfile:
            current_obj = ''

            for line in objfile:
                if line.startswith('#'):
                    continue

                # Get rid of trailing linebreaks and such
                line = line.rstrip()

                # Parse coordinates:
                if line.startswith(vertex_prefix):
                    coord = line[len(vertex_prefix):]
                    self.vertexcoords.append(parseCoord(coord))
                elif line.startswith(texture_coord_prefix):
                    coord = line[len(texture_coord_prefix):]
                    self.texturecoords.append(parseCoord(coord))
                elif line.startswith(vertex_normal_prefix):
                    coord = line[len(vertex_normal_prefix):]
                    self.normalcoords.append(parseCoord(coord))

                # Parse objects and brushes:
                elif line.startswith(object_prefix):
                    current_obj = line[len(object_prefix):]
                    self.objects[current_obj] = {
                        'smooth': 'off',
                        'groups': {},
                    }
                elif line.startswith(smooth_prefix):
                    self.objects[current_obj]['smooth'] = (
                        line[len(smooth_prefix):])
                elif line.startswith(group_prefix):
                    group = line[len(group_prefix):]
                    self.objects[current_obj]['groups'][group] = {
                        'faces': []
                    }

                # Parse textures:
                elif line.startswith(usemtl_prefix):
                    tex = line[len(usemtl_prefix):]

                    if tex.lower() in SKIP_TEXTURES:
                        continue

                    self.__check_texture(tex)

                    if tex.startswith('{') and tex not in self.maskedtextures:
                        self.maskedtextures.append(tex)

                # Parse faces:
                elif line.startswith(poly_face_prefix):
                    if tex.lower() in SKIP_TEXTURES:
                        continue

                    points = line[len(poly_face_prefix):].split(' ')

                    verts = []
                    polypoints = []
                    for point in points:
                        i_v, i_t, i_n = [int(n) for n in point.split('/')]
                        polypoint = PolyPoint(
                            self.vertexcoords[i_v - 1],
                            self.texturecoords[i_t - 1],
                            self.normalcoords[i_n - 1]
                        )

                        if polypoint.v not in self.vn_map:
                            self.vn_map[polypoint.v] = []
                        self.vn_map[polypoint.v].append(polypoint.n)

                        polypoints.append(polypoint)
                        self.allpolypoints.append(polypoint)
                        verts.append(self.vertexcoords[i_v - 1])

                    try:
                        tris = triangulate_face(verts)
                    except Exception:
                        self.__logger.exception('Face triangulation failed')
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
                            self.__logger.error(
                                "Object had one or more invalid faces: " +
                                f"{ise.message}")
                            raise

                        self.allfaces.append(polyface)
                        (self.objects[current_obj]['groups'][group]['faces']
                         .append(PolyFace(face, tex)))
