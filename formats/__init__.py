# -*- coding: utf-8 -*-
"""
Created on Tue May 30 10:38:33 2023

@author: Erty
"""

import struct
from geoutil import np, Point, PolyPoint, plane_normal


def read_byte(file) -> bytes:
    return struct.unpack('b', file.read(1))[0]


def read_int(file) -> int:
    return struct.unpack('i', file.read(4))[0]


def read_float(file) -> float:
    return struct.unpack('f', file.read(4))[0]


def read_string(file, length: int) -> str:
    return struct.unpack(f"{length}s", file.read(length))[0]


def read_ntstring(file, length: int) -> str:
    """Reads a null-terminated string of a set length."""
    strbytes = struct.unpack(f"{length}s", file.read(length))[0]
    string = ''
    for b in strbytes:
        if b == 0:
            break
        string += chr(b)
    return string


def read_lpstring(file) -> str:
    """Reads a length-prefixed ascii string."""
    strlen = read_byte(file)
    if strlen == 0:
        return ''
    return read_ntstring(file, strlen)


def read_colour(file) -> tuple:
    return (
        struct.unpack('B', file.read(1))[0],
        struct.unpack('B', file.read(1))[0],
        struct.unpack('B', file.read(1))[0]
    )


def read_vector3D(file) -> tuple:
    return (
        read_float(file),
        read_float(file),
        read_float(file),
    )


class InvalidFormatException(Exception):
    pass


class VisGroup:
    def __init__(self, id: int, name: str, colour: tuple, visible: bool):
        self.id = id
        self.name = name
        self.colour = colour
        self.visible = visible


class MapObject:
    def __init__(self, colour: tuple):
        self.colour = colour
        self.visgroup, self.group = None, None


class Brush(MapObject):
    def __init__(self, faces: list, colour: tuple):
        super().__init__(colour)
        self.faces = faces


class Entity(MapObject):
    def __init__(self, brushes: list, colour: tuple, classname: str,
                 flags: int, properties: dict, origin: tuple):
        super().__init__(colour)
        self.brushes = brushes
        self.classname = classname
        self.flags = flags
        self.properties = properties
        if not brushes:
            self.origin = origin


class Group(MapObject):
    def __init__(self, colour: tuple, objects: list):
        super().__init__(colour)
        self.objects = objects


class Plane:
    pass


class Face:
    def __init__(self, vertices: list, plane_points: list, texture: dict):
        self.vertices = vertices
        self.vertices.reverse()
        self.plane_points = [Point(*p) for p in plane_points]
        self.plane_points.reverse()
        self.texture = texture
        self.plane_normal = plane_normal(self.plane_points)

        self.polypoints = []

        for vertex in self.vertices:
            u, v = self.__project_uv(vertex)
            self.polypoints.append(PolyPoint(
                Point(*vertex),
                Point(
                    u / self.texture['width'],
                    v / self.texture['height'],
                    0),
                Point(*self.plane_normal)
            ))

    def __project_uv(self, vertex: tuple):
        vertex = np.array(vertex)

        # Get texture plane normal, not face plane normal
        plane_normal = np.cross(
            self.texture['rightaxis'], self.texture['downaxis'])

        projected = vertex - (np.dot(vertex, plane_normal) * plane_normal)

        u = self.texture['shiftx']
        v = -self.texture['shifty']

        u += np.dot(projected, self.texture['rightaxis'])
        v -= np.dot(projected, self.texture['downaxis'])

        # Apply scale:
        u, v = u / self.texture['scalex'], v / self.texture['scaley']

        return u, v


class EntityPath:
    def __init__(self, name: str, classname: str, pathtype: int, nodes: list):
        self.name = name
        self.classname = classname
        self.pathtype = pathtype
        self.nodes = nodes


class PathNode:
    def __init__(self, position: tuple, index: int,
                 name_override: str, properties: dict):
        self.position = position
        self.index = index
        self.name_override = name_override
        self.properties = properties
