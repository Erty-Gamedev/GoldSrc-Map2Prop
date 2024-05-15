# -*- coding: utf-8 -*-
"""
Created on Fri Jul 21 15:31:22 2023

@author: Erty
"""

from typing import List, Tuple, Dict, Any
from PIL import Image
from pathlib import Path
from geoutil import (Polygon, Vertex, Plane, Vector3D, Texture, ImageInfo,
                     triangulate_face, intersection_3planes, sort_vertices)
from formats import MissingTextureException
from formats.base_classes import BaseReader
from formats.wad_handler import WadHandler


def is_vertex_outside(vertex, planes: list) -> bool:
    for plane in planes:
        if plane.point_relation(vertex) > 0:
            return True
    return False


class Entity:
    def __init__(self, classname: str, properties: dict, brushes: list):
        self.classname = classname
        self.properties = properties
        self.brushes = brushes


class Brush:
    def __init__(self, faces: list):
        self.faces = faces


class Face:
    def __init__(self, points: List[Vector3D], texture: Texture, normal: Vector3D):
        self.points = sort_vertices(points, normal)
        self.texture: Texture = texture

        self.vertices: List[Vertex] = []

        nu, nv = texture.rightaxis, texture.downaxis
        w, h = texture.width, texture.height
        su, sv = texture.scalex, texture.scaley
        ou, ov = texture.shiftx, texture.shifty

        for point in self.points:
            u = (point.dot(nu)/w)/su + ou/w
            v = (point.dot(nv)/h)/sv + ov/h

            self.vertices.append(Vertex(
                point,
                Vector3D(u, -v, 0),
                normal
            ))
        # TODO: normalize UV


class MapReader(BaseReader):
    """Reads a .map format file and parses geometry data."""

    def __init__(self, filepath: Path, outputdir: Path):
        self.filepath = filepath
        self.entities = []
        self.brushes = []
        self.properties = {}

        self.allfaces = []
        self.allvertices = []
        self.vn_map = {}
        self.maskedtextures = []

        self.checked = []
        self.textures: Dict[str, ImageInfo] = {}
        self.missing_textures = False

        self.filedir = self.filepath.parents[0]
        self.wadhandler = WadHandler(self.filedir, outputdir)

        self.parse()

    def parse(self):
        with self.filepath.open('r') as file:
            while line := file.readline().strip():
                if line.startswith('{'):
                    entity = self.readentity(file)

                    if entity.classname == 'worldspawn':
                        self.properties = entity.properties
                        self.brushes = entity.brushes
                    else:
                        self.entities.append(entity)

    def readentity(self, file) -> Entity:
        classname = ''
        properties = {}
        brushes = []
        while line := file.readline().strip():
            if line.startswith('//'):  # skip comments
                continue
            elif line.startswith('"'):  # read keyvalues
                keyvalue = line.split('"')
                if len(keyvalue) > 5:
                    raise Exception(f"Invalid keyvalue: {keyvalue}.")
                key, value = keyvalue[1].strip(), keyvalue[3].strip()

                if key == 'classname':
                    classname = value
                elif key == 'wad' and classname == 'worldspawn':
                    self.wadhandler.set_wadlist(value.split(';'))

                properties[key] = value
            elif line.startswith('{'):
                brush = self.readbrush(file)
                brushes.append(brush)
                self.brushes.append(brush)
            elif line.startswith('}'):
                break
            else:
                raise Exception(f"Unexpected entity data: {line}")
        return Entity(classname, properties, brushes)

    def readbrush(self, file) -> Brush:
        planes: List[Plane] = []

        while line := file.readline().strip():
            if line.startswith('//'):
                continue
            elif line.startswith('('):
                planes.append(self.readplane(line))
            elif line.startswith('}'):
                break
            else:
                raise Exception(f"Unexpected face data: {line}")

        faces = self.faces_from_planes(planes)

        face: Face
        for face in faces:
            if self.wadhandler.skip_face(face.texture.name):
                continue

            self.addpolyface(face)
            for vertex in face.vertices:
                if vertex not in self.allvertices:
                    self.allvertices.append(vertex)
                    if vertex.v not in self.vn_map:
                        self.vn_map[vertex.v] = []
                    self.vn_map[vertex.v].append(vertex.n)

        return Brush(faces)

    def readplane(self, line: str) -> Plane:
        parts = line.split()
        if len(parts) != 31:
            raise Exception(f"Unexpected face data: {line}")

        plane_points: List[Tuple[float, float, float]] = [
            (float(parts[1]), float(parts[2]), float(parts[3])),
            (float(parts[6]), float(parts[7]), float(parts[8])),
            (float(parts[11]), float(parts[12]), float(parts[13]))
        ]

        name = parts[15]

        # Check if texture exists, or try to extract it if not
        if name not in self.checked:
            if not self.wadhandler.check_texture(name):
                self.missing_textures = True

            # Make note of masked textures
            if (name.startswith('{')
                    and name not in self.maskedtextures):
                self.maskedtextures.append(name)
            self.checked.append(name)

        if name.lower() not in self.wadhandler.SKIP_TEXTURES:
            tex_image = self.get_texture(name)
            width = tex_image.width
            height = tex_image.height
        else:
            width = 16
            height = 16

        texture = Texture(
            name,
            (float(parts[17]), float(parts[18]), float(parts[19])),
            float(parts[20]),
            (float(parts[23]), float(parts[24]), float(parts[25])),
            float(parts[26]),
            float(parts[28]),
            float(parts[29]),
            float(parts[30]),
            width, height
        )

        return Plane(plane_points, texture)

    def faces_from_planes(self, planes: List[Plane]) -> list:
        num_planes = len(planes)
        faces: List[Dict[str, Any]] = [{'vertices': []} for _ in range(num_planes)]

        for i in range(num_planes):
            for j in range(i + 1, num_planes):
                for k in range(j + 1, num_planes):
                    if i == j == k:
                        continue

                    vertex = intersection_3planes(
                        planes[i], planes[j], planes[k]
                    )

                    if vertex is False:
                        continue

                    if is_vertex_outside(vertex, planes):
                        continue

                    faces[i]['vertices'].append(vertex)
                    faces[j]['vertices'].append(vertex)
                    faces[k]['vertices'].append(vertex)

                    faces[i]['texture'] = planes[i].texture
                    faces[j]['texture'] = planes[j].texture
                    faces[k]['texture'] = planes[k].texture

                    faces[i]['normal'] = planes[i].normal
                    faces[j]['normal'] = planes[j].normal
                    faces[k]['normal'] = planes[k].normal

        for f in faces:
            if len(f['vertices']) < 3:
                raise Exception('uh oh')

        return [Face(f['vertices'], f['texture'], f['normal']) for f in faces]

    def addpolyface(self, face: Face):
        tris = triangulate_face(face.points)

        for tri in tris:
            tri_face = []
            for p in tri:
                for vertex in face.vertices:
                    if p == vertex.v:
                        tri_face.append(vertex)
                        break

            polyface = Polygon(tri_face, face.texture.name)

            self.allfaces.append(polyface)

    def get_texture(self, texture: str) -> ImageInfo:
        if texture not in self.textures:
            texfile = self.filedir / f"{texture}.bmp"
            if not texfile.exists():
                raise MissingTextureException(
                    f"Could not find texture {texture}")

            with Image.open(texfile, 'r') as imgfile:
                self.textures[texture] = ImageInfo(
                    imgfile.width, imgfile.height
                )
        return self.textures[texture]
