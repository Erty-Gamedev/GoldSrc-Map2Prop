# -*- coding: utf-8 -*-

from typing import List, Union, Tuple, Dict, Self
from PIL import Image
from pathlib import Path
from dataclasses import dataclass
from io import BufferedReader
from geoutil import Polygon, Vertex, ImageInfo, Texture, triangulate_face, plane_normal
from vector3d import Vector3D
from formats import (read_bool, read_int, read_float, read_ntstring,
                     read_lpstring, read_colour, read_vector3D,
                     InvalidFormatException, MissingTextureException)
from formats.base_classes import BaseReader, BaseFace, BaseBrush, BaseEntity
from formats.wad_handler import WadHandler


class Face(BaseFace):
    def __init__(self,
                 points: List[Tuple[float, float, float]],
                 plane_points: List[Tuple[float, float, float]],
                 texture: Texture):
        self._points = [Vector3D(*p) for p in points]
        self._plane_points = [Vector3D(*p) for p in plane_points]
        self._polygons: List[Polygon] = []
        self._texture = texture
        self._vertices: List[Vertex] = []
        self._normal: Vector3D = plane_normal(self._plane_points)

        for point in self.points:
            u, v = self.project_uv(Vector3D(*point))
            self._vertices.append(Vertex(
                Vector3D(*point),
                Vector3D(
                    u / self.texture.width,
                    v / self.texture.height,
                    0),
                self._normal
            ))

        for triangle in triangulate_face(self.points):
            polygon = []
            for point in triangle:
                for vertex in self.vertices:
                    if point == vertex.v:
                        polygon.append(vertex)
                        break
            self._polygons.append(Polygon(polygon, self.texture.name))

    @property
    def normal(self): return self._normal

    def project_uv(self, point: Vector3D):
        # Get texture plane normal, not face plane normal
        plane_normal = Vector3D(*self.texture.rightaxis).cross(
            Vector3D(*self.texture.downaxis))

        projected = point - (point.dot(plane_normal) * plane_normal)

        u = self.texture.shiftx * self.texture.scalex
        v = -self.texture.shifty * self.texture.scaley

        u += projected.dot(self.texture.rightaxis)
        v -= projected.dot(self.texture.downaxis)

        # Apply scale:
        u, v = u / self.texture.scalex, v / self.texture.scaley

        return u, v

class Brush(BaseBrush):
    pass

class Entity(BaseEntity):
    def __init__(self, classname: str, properties: Dict[str, str], brushes: List[Brush]):
        self._classname = classname
        self._properties = properties
        self._brushes = brushes
    @property
    def brushes(self): return self._brushes

@dataclass
class Group:
    children: List[Union[Brush, Entity, Self]]


class RmfReader(BaseReader):
    """Reads a .rmf format file and parses geometry data."""

    def __init__(self, filepath: Path, outputdir: Path):
        self.filepath = filepath
        self.filedir = self.filepath.parents[0]
        self.outputdir = outputdir
        self.wadhandler = WadHandler(self.filedir, outputdir)
        self.checked: List[str] = []
        self.textures: Dict[str, ImageInfo] = {}
        self.missing_textures: bool = False
        self.entities: List[Entity] = []

        self.parse()

    def parse(self) -> None:
        with self.filepath.open('rb') as file:
            self.version = read_float(file)

            magic = file.read(3)
            if magic != bytes('RMF', 'ascii'):
                raise InvalidFormatException(
                    f"{self.filepath} is not a valid RMF file.")

            visgroups_count = read_int(file)
            for _ in range(visgroups_count):
                self.readvisgroup(file)

            read_lpstring(file)  # "CMapWorld"
            file.read(7)  # Padding bytes?

            objects: List[Union[Brush, Entity, Group]] = []
            objects_count = read_int(file)
            for _ in range(objects_count):
                objects.append(self.readobject(file))

            read_lpstring(file)  # "worldspawn"
            file.read(4)  # Padding?

            spawnflags = read_int(file)

            properties: Dict[str, str] = {}
            properties_count = read_int(file)
            for _ in range(properties_count):
                p_name = read_lpstring(file)
                properties[p_name] = read_lpstring(file)
            file.read(12)  # Padding?

            if 'spawnflags' not in properties:
                properties['spawnflags'] = str(spawnflags)

            self.worldspawn = Entity('worldspawn', properties, [])
            self.entities = [self.worldspawn]

            for obj in objects:
                self.addobject(obj)

            path_count = read_int(file)
            for _ in range(path_count):
                self.readpath(file)

    def readvisgroup(self, file: BufferedReader) -> None:
        read_ntstring(file, 128)  # Name
        read_colour(file)  # Editor colour
        file.read(1)  # Padding byte
        read_int(file)  # Visgroup id
        read_bool(file)  # Editor visibility
        file.read(3)  # Padding bytes

    def readobject(self, file: BufferedReader
        ) -> Union[Brush, Entity, Group]:
        typename = read_lpstring(file)

        if typename == 'CMapSolid':
            return self.readbrush(file)
        elif typename == 'CMapEntity':
            return self.readentity(file)
        elif typename == 'CMapGroup':
            return self.readgroup(file)
        else:
            raise Exception(f"Invalid object type: {typename}")

    def readbrush(self, file: BufferedReader) -> Brush:
        read_int(file)  # Visgroup id
        read_colour(file)  # Editor colour
        file.read(4)  # Padding?

        faces = []
        faces_count = read_int(file)
        for _ in range(faces_count):
            face = self.readface(file)
            if self.wadhandler.skip_face(face.texture.name):
                continue
            faces.append(face)
        return Brush(faces)

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

    def readface(self, file: BufferedReader) -> Face:
        name = read_ntstring(file, 260)

        # Check if texture exists, or try to extract it if not
        if name not in self.checked:
            if not self.wadhandler.check_texture(name):
                self.missing_textures = True
            self.checked.append(name)

        rightaxis = read_vector3D(file)
        shiftx = read_float(file)
        downaxis = read_vector3D(file)
        shifty = read_float(file)
        angle = read_float(file)
        scalex = read_float(file)
        scaley = read_float(file)

        if name.lower() not in self.wadhandler.SKIP_TEXTURES:
            tex_image = self.get_texture(name)
            width = tex_image.width
            height = tex_image.height
        else:
            width = 16
            height = 16

        texture = Texture(
            name,
            rightaxis, shiftx,
            downaxis, shifty,
            angle,
            scalex, scaley,
            width, height
        )

        file.read(16)  # Padding

        points: List[Tuple[float, float, float]] = []
        vertex_count = read_int(file)
        for _ in range(vertex_count):
            points.append(read_vector3D(file))
        points.reverse()

        plane_points = [
            read_vector3D(file),
            read_vector3D(file),
            read_vector3D(file),
        ]
        plane_points.reverse()

        return Face(points, plane_points, texture)

    def readentity(self, file: BufferedReader) -> Entity:
        read_int(file)  # Visgroup id
        read_colour(file)  # Editor colour

        brushes = []
        brush_count = read_int(file)
        for _ in range(brush_count):
            read_lpstring(file)  # "CMapSolid"
            brush = self.readbrush(file)
            brushes.append(brush)

        classname = read_lpstring(file)
        file.read(4)  # Padding?
        spawnflags = read_int(file)

        properties = {}
        property_count = read_int(file)
        for _ in range(property_count):
            prop_n = read_lpstring(file)
            properties[prop_n] = read_lpstring(file)

        file.read(14)  # More padding?

        if 'spawnflags' not in properties:
            properties['spawnflags'] = str(spawnflags)

        read_vector3D(file)  # Origin for point entities

        file.read(4)  # Padding?

        return Entity(classname, properties, brushes)

    def readgroup(self, file: BufferedReader) -> Group:
        read_int(file)  # Visgroup id
        read_colour(file)  # Editor colour

        children: List[Union[Brush, Entity, Group]] = []
        object_count = read_int(file)
        for _ in range(object_count):
            children.append(self.readobject(file))

        return Group(children)

    def addobject(self, obj: Union[Brush, Entity, Group]):
        if isinstance(obj, Entity):
            self.entities.append(obj)
        elif isinstance(obj, Brush):
            self.worldspawn.brushes.append(obj)
        elif isinstance(obj, Group):
            for child in obj.children:
                self.addobject(child)

    def readpath(self, file: BufferedReader) -> None:
        read_ntstring(file, 128)  # Name
        read_ntstring(file, 128)  # Classname
        read_int(file)  # Path type

        node_count = read_int(file)
        for _ in range(node_count):
            self.readpathnode(file)

    def readpathnode(self, file: BufferedReader) -> None:
        read_vector3D(file)  # Position
        read_int(file)  # Index in path
        read_ntstring(file, 128)  # Targetname override

        property_count = read_int(file)
        for _ in range(property_count):
            read_lpstring(file)  # Key
            read_lpstring(file)  # Value
