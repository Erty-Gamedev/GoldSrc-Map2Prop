# -*- coding: utf-8 -*-
"""
Created on Tue May 30 10:40:33 2023

@author: Erty
"""

from pathlib import Path
from logutil import get_logger, shutdown_logger
from geoutil import (Vector3D, PolyPoint, PolyFace,
                     InvalidSolidException, triangulate_face)
from formats.wad_handler import WadHandler


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
    return Vector3D(*[float(n) for n in coord])


class ObjReader:
    """Reads an .obj format file and parses geometry data."""

    def __init__(self, filepath: Path, outputdir: Path):
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
        self.__checked = []
        self.missing_textures = False

        self.__logger = get_logger(__name__)
        self.__filedir = self.filepath.parents[0]
        self.wadhandler = WadHandler(self.__filedir, outputdir)

        self.__readfile()

        shutdown_logger(self.__logger)

    def __del__(self):
        shutdown_logger(self.__logger)

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

                    # Check if texture exists, or try to extract it if not
                    if tex not in self.__checked:
                        if not self.wadhandler.check_texture(tex):
                            self.missing_textures = True

                        # Make note of masked textures
                        if (tex.startswith('{')
                                and tex not in self.maskedtextures):
                            self.maskedtextures.append(tex)
                        self.__checked.append(tex)

                # Parse faces:
                elif line.startswith(poly_face_prefix):
                    if tex.lower() in self.wadhandler.SKIP_TEXTURES:
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
