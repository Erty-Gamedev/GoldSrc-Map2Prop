# -*- coding: utf-8 -*-
"""
Created on Tue May 30 10:40:33 2023

@author: Erty
"""

from typing import List, Dict
from pathlib import Path
from logutil import get_logger, shutdown_logger
from geoutil import (Vector3D, Vertex, PolyFace, ImageInfo,
                     InvalidSolidException, triangulate_face)
from formats.base_reader import BaseReader
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


def parseCoord(coord: str) -> Vector3D:
    coords: List[str] = coord.split(' ')
    return Vector3D(*[float(n) for n in coords])


class ObjReader(BaseReader):
    """Reads an .obj format file and parses geometry data."""

    def __init__(self, filepath: Path, outputdir: Path):
        self.filepath = filepath

        self.vertexcoords: List[Vector3D] = []
        self.texturecoords: List[Vector3D] = []
        self.normalcoords: List[Vector3D] = []

        self.textures: Dict[str, ImageInfo] = {}
        self.objects: Dict[str, dict] = {}
        self.maskedtextures = []
        self.allfaces = []
        self.allvertices = []
        self.vn_map = {}
        self.checked = []
        self.missing_textures = False

        self.logger = get_logger(__name__)
        self.filedir = self.filepath.parents[0]
        self.wadhandler = WadHandler(self.filedir, outputdir)

        self.readfile()

        shutdown_logger(self.logger)

    def __del__(self):
        shutdown_logger(self.logger)

    def readfile(self):
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
                    if tex not in self.checked:
                        if not self.wadhandler.check_texture(tex):
                            self.missing_textures = True

                        # Make note of masked textures
                        if (tex.startswith('{')
                                and tex not in self.maskedtextures):
                            self.maskedtextures.append(tex)
                        self.checked.append(tex)

                # Parse faces:
                elif line.startswith(poly_face_prefix):
                    if tex.lower() in self.wadhandler.SKIP_TEXTURES:
                        continue

                    facepoints = line[len(poly_face_prefix):].split(' ')

                    points = []
                    vertices = []
                    for facepoint in facepoints:
                        i_v, i_t, i_n = [int(n) for n in facepoint.split('/')]
                        vertex = Vertex(
                            self.vertexcoords[i_v - 1],
                            self.texturecoords[i_t - 1],
                            self.normalcoords[i_n - 1]
                        )

                        if vertex.v not in self.vn_map:
                            self.vn_map[vertex.v] = []
                        self.vn_map[vertex.v].append(vertex.n)

                        vertices.append(vertex)
                        self.allvertices.append(vertex)
                        points.append(self.vertexcoords[i_v - 1])

                    try:
                        tris = triangulate_face(points)
                    except Exception:
                        self.logger.exception('Face triangulation failed')
                        raise

                    for tri in tris:
                        face = []
                        for p in tri:
                            for vertex in vertices:
                                if p == vertex.v:
                                    face.append(vertex)
                                    break

                        try:
                            polyface = PolyFace(face, tex)
                        except InvalidSolidException as ise:
                            self.logger.error(
                                "Object had one or more invalid faces: " +
                                f"{ise.message}")
                            raise

                        self.allfaces.append(polyface)
                        (self.objects[current_obj]['groups'][group]['faces']
                         .append(PolyFace(face, tex)))
