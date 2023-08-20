# -*- coding: utf-8 -*-
"""
Created on Fri Jul 21 15:31:22 2023

@author: Erty
"""

from PIL import Image
from pathlib import Path
from geoutil import PolyFace, triangulate_face, Vector3D, plane_intersection
from formats import Face
# from formats.wad_handler import WadHandler


class Entity:
    def __init__(self, classname: str, properties: dict, brushes: list):
        self.classname = classname
        self.properties = properties
        self.brushes = brushes


class Brush:
    def __init__(self, faces: list):
        self.faces = faces


class Plane:
    def __init__(self, plane_points: list, texture: dict):
        self.plane_points = plane_points
        self.texture = texture


class MapReader:
    """Reads a .map format file and parses geometry data."""

    def __init__(self, filepath: Path, outputdir: Path):
        self.filepath = filepath
        self.entities = []
        self.brushes = []
        self.properties = {}
        self.entity_paths = []

        self.allfaces = []
        self.allpolypoints = []
        self.vn_map = {}
        self.maskedtextures = []

        self.__checked = []
        self.__textures = {}
        self.missing_textures = False

        self.__filedir = self.filepath.parents[0]
        # self.wadhandler = WadHandler(self.__filedir, outputdir)

        self.__parse()

    def __parse(self):
        with self.filepath.open('r') as file:
            while line := file.readline().strip():
                if line.startswith('{'):
                    entity = self.__readentity(file)

                    if entity.classname == 'worldspawn':
                        self.properties = entity.properties
                        self.brushes = entity.brushes
                    else:
                        self.entities.append(entity)

    def __readentity(self, file) -> Entity:
        classname = ''
        properties = {}
        brushes = []
        while line := file.readline().strip():
            if line.startswith('//'):
                continue
            elif line.startswith('"'):
                keyvalue = line.split('"')
                if len(keyvalue) > 5:
                    raise Exception(f"Invalid keyvalue: {keyvalue}.")
                key, value = keyvalue[1].strip(), keyvalue[3].strip()

                if key == 'classname':
                    classname = value
                if key == 'wad' and classname == 'worldspawn':
                    self.__handlewadlist(value)

                properties[key] = value
            elif line.startswith('{'):
                brush = self.__readbrush(file)
                brushes.append(brush)
            elif line.startswith('}'):
                break
            else:
                raise Exception(f"Unexpected entity data: {line}")
        return Entity(classname, properties, brushes)

    def __handlewadlist(self, wadlist: str):
        pass

    def __readbrush(self, file) -> Brush:
        faces = []
        protofaces = []
        planes = []
        while line := file.readline().strip():
            if line.startswith('//'):
                continue
            elif line.startswith('('):
                protoface = self.__readface(line)
                protofaces.append(protoface)
                planes.extend(protoface.plane_points)
            elif line.startswith('}'):
                break
            else:
                raise Exception(f"Unexpected face data: {line}")
        for protoface in protofaces:
            vertices = self.__intersections(protoface.plane_points, planes)
            faces.append(Face(
                vertices, protoface.plane_points, protoface.texture))
        return Brush(faces)

    def __readplane(self, line: str) -> Plane:
        parts = line.split()
        if len(parts) != 31:
            raise Exception(f"Unexpected face data: {line}")

        plane_points = [
            (float(parts[1]), float(parts[2]), float(parts[3])),
            (float(parts[6]), float(parts[7]), float(parts[8])),
            (float(parts[11]), float(parts[12]), float(parts[13]))
        ]

        texture = {
            'name': parts[15],
            'rightaxis': (
                float(parts[17]), float(parts[18]), float(parts[19])),
            'shiftx': float(parts[20]),
            'downaxis': (
                float(parts[23]), float(parts[24]), float(parts[25])),
            'shifty': float(parts[26]),
            'angle': float(parts[28]),
            'scalex': float(parts[29]),
            'scaley': float(parts[30]),
            'width': 16,
            'height': 16,
        }

        return Plane(plane_points, texture)

    def __faces_from_planes(self, planes: list) -> dict:
        vertices = []
        faces = {}
        edges = []
        edge_face_map = {}

        for plane in planes:
            for plane2 in planes:
                if plane == plane2:
                    continue
                if (edge := plane_intersection(plane, plane2)) is not None:
                    edges.append(edge)
                    if edge not in edge_face_map:
                        edge_face_map[edge] = []
                    if plane not in edge_face_map[edge]:
                        edge_face_map[edge].append(plane)
                    if plane2 not in edge_face_map[edge]:
                        edge_face_map[edge].append(plane2)

        for edge in edges:
            for edge2 in edges:
                if edge == edge2:
                    continue
                if (vertex := line_intersection(edge, edge2)) is not None:
                    vertices.append(vertex)

        return faces

    # def __intersections(self, plane: list, neighbours: list):
    #     vertices = []

    #     for n in neighbours:
    #         if n == plane:
    #             continue

    #         vertices.append((0, 0, 0))

    #     return vertices
