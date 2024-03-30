# -*- coding: utf-8 -*-
"""
Created on Tue May 30 10:38:33 2023

@author: Erty
"""

from typing import Tuple, List, Union, Optional, Self
from struct import unpack
from vector3d import Vector3D
from geoutil import Vertex, Texture, plane_normal


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
    strlen = int(read_byte(file))
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


def read_colour(file) -> Tuple[int, int, int]:
    return (
        unpack('<B', file.read(1))[0],
        unpack('<B', file.read(1))[0],
        unpack('<B', file.read(1))[0]
    )


def read_colour_rgba(file) -> Tuple[int, int, int, int]:
    return (
        unpack('<B', file.read(1))[0],
        unpack('<B', file.read(1))[0],
        unpack('<B', file.read(1))[0],
        unpack('<B', file.read(1))[0],
    )


def read_vector3D(file) -> Tuple[float, float, float]:
    return (
        read_float(file),
        read_float(file),
        read_float(file),
    )


def read_angles(file) -> Tuple[float, float, float]:
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
        self.visgroup: Optional[VisGroup] = None
        self.group: Optional[Group] = None


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
    def __init__(self, colour: tuple, objects: List[Union[Brush, Entity, Self]]):
        super().__init__(colour)
        self.objects = objects


class Plane:
    pass


class Face:
    def __init__(
            self,
            points: List[Tuple[float, float, float]],
            plane_points: list,
            texture: Texture):
        self.points: List[Tuple[float, float, float]] = points
        self.plane_points = [Vector3D(*p) for p in plane_points]
        self.texture: Texture = texture
        self.plane_normal: Vector3D = plane_normal(self.plane_points)

        self.vertices: List[Vertex] = []

        for point in self.points:
            u, v = self.__project_uv(point)
            self.vertices.append(Vertex(
                Vector3D(*point),
                Vector3D(
                    u / self.texture.width,
                    v / self.texture.height,
                    0),
                self.plane_normal
            ))

    def __project_uv(self, point: Tuple[float, float, float]):
        vector = Vector3D(*point)

        # Get texture plane normal, not face plane normal
        plane_normal = Vector3D(*self.texture.rightaxis).cross(
            Vector3D(*self.texture.downaxis))

        projected = vector - (vector.dot(plane_normal) * plane_normal)

        u = self.texture.shiftx * self.texture.scalex
        v = -self.texture.shifty * self.texture.scaley

        u += projected.dot(self.texture.rightaxis)
        v -= projected.dot(self.texture.downaxis)

        # Apply scale:
        u, v = u / self.texture.scalex, v / self.texture.scaley

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


class EntityBase:
    def __init__(self, classname: str,
                 properties: dict = {}, brushes: list = []):
        self.classname: str = classname
        self.properties: dict = properties
        self.brushes: list = brushes


class BrushBase:
    def __init__(self, faces: list = []):
        self.faces: list = faces


class FaceBase:
    def __init__(self):
        pass
