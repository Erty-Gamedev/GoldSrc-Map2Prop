# -*- coding: utf-8 -*-
"""
Created on Tue May 30 10:38:33 2023

@author: Erty
"""

from struct import unpack
from geoutil import Vector3D, Vertex, plane_normal


def read_byte(file) -> bytes:
    return unpack('<b', file.read(1))[0]


def read_bool(file) -> bytes:
    return unpack('<?', file.read(1))[0]


def read_short(file) -> bytes:
    return unpack('<h', file.read(2))[0]


def read_int(file) -> int:
    return unpack('<i', file.read(4))[0]


def read_float(file) -> float:
    return unpack('<f', file.read(4))[0]


def read_double(file) -> float:
    return unpack('<d', file.read(8))[0]


def read_string(file, length: int) -> str:
    return unpack(f"<{length}s", file.read(length))[0]


def read_ntstring(file, length: int) -> str:
    """Reads a null-terminated string of a set length."""
    strbytes = unpack(f"<{length}s", file.read(length))[0]
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
    if strlen < 0:
        strlen = 256 + strlen
    return read_ntstring(file, strlen)


def read_lpstring2(file) -> str:
    """Reads a 4-byte length-prefixed ascii string."""
    buffer = file.read(4)
    if len(buffer) < 4:
        raise EndOfFileException()
    strlen = unpack('<i', buffer)[0]
    if strlen == -1:
        return ''
    return read_ntstring(file, strlen)


def read_colour(file) -> tuple:
    return (
        unpack('<B', file.read(1))[0],
        unpack('<B', file.read(1))[0],
        unpack('<B', file.read(1))[0]
    )


def read_colour_rgba(file) -> tuple:
    return (
        unpack('<B', file.read(1))[0],
        unpack('<B', file.read(1))[0],
        unpack('<B', file.read(1))[0],
        unpack('<B', file.read(1))[0],
    )


def read_vector3D(file) -> tuple:
    return (
        read_float(file),
        read_float(file),
        read_float(file),
    )


def read_angles(file):
    return read_vector3D(file)


class InvalidFormatException(Exception):
    pass


class EndOfFileException(Exception):
    pass


class MissingTextureException(Exception):
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


class JGroup:
    def __init__(self, colour: tuple, id: int):
        self.colour = colour
        self.id = id


class Plane:
    pass


class Face:
    def __init__(self, points: list, plane_points: list, texture: dict):
        self.points = points
        self.plane_points = [Vector3D(*p) for p in plane_points]
        self.texture = texture
        self.plane_normal = plane_normal(self.plane_points)

        self.vertices = []

        for vertex in self.points:
            u, v = self.__project_uv(vertex)
            self.vertices.append(Vertex(
                Vector3D(*vertex),
                Vector3D(
                    u / self.texture['width'],
                    v / self.texture['height'],
                    0),
                Vector3D(*self.plane_normal)
            ))

    def __project_uv(self, vertex: tuple):
        vertex = Vector3D(*vertex)

        # Get texture plane normal, not face plane normal
        plane_normal = Vector3D(*self.texture['rightaxis']).cross(
            Vector3D(*self.texture['downaxis']))

        projected = vertex - (vertex.dot(plane_normal) * plane_normal)

        u = self.texture['shiftx'] * self.texture['scalex']
        v = -self.texture['shifty'] * self.texture['scaley']

        u += projected.dot(self.texture['rightaxis'])
        v -= projected.dot(self.texture['downaxis'])

        # Apply scale:
        u, v = u / self.texture['scalex'], v / self.texture['scaley']

        return u, v


class JFace:
    def __init__(self, points: list, texture: dict, normal: tuple = None):
        self.points = points
        self.texture = texture
        self.plane_normal = normal

        self.vertices = []

        for i, vertex in enumerate(self.points):
            u, v = vertex[3:]
            vertex = vertex[:3]
            self.vertices.append(Vertex(
                Vector3D(*vertex),
                Vector3D(u, -v, 0),
                Vector3D(*self.plane_normal)
            ))
            self.points[i] = vertex


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
