# -*- coding: utf-8 -*-

from typing import List, Dict, Tuple
from PIL import Image
from pathlib import Path
from io import BufferedReader
from dataclasses import dataclass
from vector3d import Vector3D
from geoutil import Polygon, Vertex, ImageInfo, Texture, triangulate_face
from formats import (read_bool, read_int, read_short, read_float, read_double,
                     read_ntstring, read_lpstring2, read_colour_rgba,
                     read_vector3D, read_angles,
                     InvalidFormatException, EndOfFileException,
                     MissingTextureException)
from formats.base_classes import BaseReader, BaseEntity, BaseBrush, BaseFace
from formats.wad_handler import WadHandler


@dataclass
class JFaceVertex:
    vertex: Tuple[float, float, float]
    u: float
    v: float

class Face(BaseFace):
    def __init__(
            self,
            face_vertices: List[JFaceVertex],
            texture: Texture,
            normal: Vector3D) -> None:
        self._points: List[Vector3D] = []
        self._polygons: List[Polygon] = []
        self._texture: Texture = texture
        self._normal: Vector3D = normal
        self._vertices: List[Vertex] = []

        for face_vertex in face_vertices:
            self._vertices.append(Vertex(
                Vector3D(*face_vertex.vertex),
                Vector3D(face_vertex.u, -face_vertex.v, 0),
                self._normal
            ))
            self._points.append(Vector3D(*face_vertex.vertex))
        
        for triangle in triangulate_face(self._points):
            polygon = []
            for point in triangle:
                for vertex in self.vertices:
                    if point == vertex.v:
                        polygon.append(vertex)
                        break
            self._polygons.append(Polygon(polygon, self.texture.name))

class Brush(BaseBrush):
    pass

class Entity(BaseEntity):
    def __init__(self, classname: str, properties: Dict[str, str], brushes: List[Brush]):
        self._classname = classname
        self._properties = properties
        self._brushes = brushes
    @property
    def brushes(self): return self._brushes


class JmfReader(BaseReader):
    """Reads a .jmf format file and parses geometry data."""

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

    def parse(self):
        with self.filepath.open('rb') as file:
            magic = file.read(4)
            if magic != bytes('JHMF', 'ascii'):
                raise InvalidFormatException(
                    f"{self.filepath} is not a valid JMF file.")

            # JMF format version.
            # Was 121 before december 2023 update, became 122 after.
            jmf_version = read_int(file)

            export_path_count = read_int(file)
            for _ in range(export_path_count):
                read_lpstring2(file)

            if jmf_version >= 122:
                for _ in range(3):
                    self.readbgimage(file)

            group_count = read_int(file)
            for _ in range(group_count):
                self.readgroup(file)

            visgroups_count = read_int(file)
            for _ in range(visgroups_count):
                self.readvisgroup(file)

            read_vector3D(file)  # Cordon minimum
            read_vector3D(file)  # Cordon maximum

            camera_count = read_int(file)
            for _ in range(camera_count):
                self.readcamera(file)

            path_count = read_int(file)
            for _ in range(path_count):
                self.readpath(file)

            try:
                while True:
                    self.entities.append(self.readentity(file))
            except EndOfFileException:
                pass

    def readbgimage(self, file: BufferedReader) -> None:
        read_lpstring2(file)  # Image path
        read_double(file)  # Scale
        read_int(file)  # Luminance
        read_int(file)  # Filtering (0=near/1=lin)
        read_int(file)  # Invert colours
        read_int(file)  # X offset
        read_int(file)  # Y offset
        read_int(file)  # Padding?

    def readgroup(self, file: BufferedReader) -> None:
        read_int(file)  # Group id
        read_int(file)  # Group parent id
        read_int(file)  # flags
        read_int(file)  # count
        read_colour_rgba(file)  # Editor colour

    def readvisgroup(self, file: BufferedReader) -> None:
        read_lpstring2(file)  # Name
        read_int(file)  # Visgroup id
        read_colour_rgba(file)  # Editor colour
        read_bool(file)  # Editor visibility

    def readcamera(self, file: BufferedReader) -> None:
        read_vector3D(file)  # Eye position
        read_vector3D(file)  # Look target
        read_int(file)  # Editor flags (bit 0x02 for is selected)
        read_colour_rgba(file)  # Editor colour

    def readpath(self, file: BufferedReader) -> None:
        read_lpstring2(file)  # Classname
        read_lpstring2(file)  # Name
        read_int(file)  # Path type
        file.read(4)  # padding?
        read_colour_rgba(file)  # Editor colour

        node_count = read_int(file)
        for _ in range(node_count):
            self.readpathnode(file)

    def readpathnode(self, file: BufferedReader) -> None:
        read_lpstring2(file)  # Name override
        read_lpstring2(file)  # Fire on target
        read_vector3D(file)  # Position

        read_angles(file)  # Angles
        read_int(file)  # Editor flags
        read_colour_rgba(file)  # Editor colour

        property_count = read_int(file)
        for _ in range(property_count):
            read_lpstring2(file)  # Key
            read_lpstring2(file)  # Value

    def readentity(self, file: BufferedReader) -> Entity:
        classname = read_lpstring2(file)
        read_vector3D(file)  # Origin for point entities
        read_int(file)  # Jack editor state
        read_int(file)  # Group id
        read_int(file)  # root group id
        read_colour_rgba(file)  # Editor colour

        # Special attributes, irrelevant for us
        for _ in range(13):
            read_lpstring2(file)

        spawnflags = read_int(file)

        read_angles(file)  # angles
        read_int(file)  # rendering
        file.read(4)  # FX Color
        read_int(file)  # Render Mode
        read_int(file)  # Render FX
        read_short(file)  # body
        read_short(file)  # skin
        read_int(file)  # sequence
        read_float(file)  # framerate
        read_float(file)  # scale
        read_float(file)  # radius

        file.read(28)  # padding?

        properties = {}
        property_count = read_int(file)
        for _ in range(property_count):
            p_name = read_lpstring2(file)
            properties[p_name] = read_lpstring2(file)

        if 'spawnflags' not in properties:
            properties['spawnflags'] = str(spawnflags)

        visgroup_count = read_int(file)
        for _ in range(visgroup_count):
            read_int(file)

        brushes = []
        brush_count = read_int(file)
        for _ in range(brush_count):
            brushes.append(self.readbrush(file))

        return Entity(classname, properties, brushes)

    def readbrush(self, file: BufferedReader) -> Brush:
        curves_count = read_int(file)
        read_int(file)  # Jack editor state
        read_int(file)  # Group id
        read_int(file)  # root group id
        read_colour_rgba(file)  # Editor colour

        visgroup_count = read_int(file)
        for _ in range(visgroup_count):
            read_int(file)

        faces = []
        faces_count = read_int(file)
        for _ in range(faces_count):
            face = self.readface(file)

            if self.wadhandler.skip_face(face.texture.name):
                continue

            faces.append(face)

        for _ in range(curves_count):
            self.readcurve(file)

        return Brush(faces)

    def readcurve(self, file: BufferedReader) -> None:
        read_int(file)  # Width
        read_int(file)  # Height

        # surface properties
        read_vector3D(file)      # rightaxis
        read_float(file)         # shiftx
        read_vector3D(file)      # texture['downaxis']
        read_float(file)         # texture['shifty']
        read_float(file)         # texture['scalex']
        read_float(file)         # texture['scaley']
        read_float(file)         # texture['angle']
        file.read(16)
        read_int(file)           # contents flags
        read_ntstring(file, 64)  # texture name

        file.read(4)  # unknown

        for _ in range(1024):
            self.readcurvepoint(file)

    def readcurvepoint(self, file: BufferedReader) -> None:
        read_vector3D(file)  # Position
        read_vector3D(file)  # Normal
        read_vector3D(file)  # Texture UV

    def readface(self, file: BufferedReader) -> Face:
        read_int(file)  # Render flags
        vertex_count = read_int(file)

        rightaxis= read_vector3D(file)
        shiftx = read_float(file)
        downaxis = read_vector3D(file)
        shifty = read_float(file)
        scalex = read_float(file)
        scaley = read_float(file)
        angle = read_float(file)

        read_int(file)  # Texture alignment flag (0x01=world, 0x02=face)
        file.read(12)  # Padding?
        read_int(file)  # Content flags for Quake 2 maps

        name = read_ntstring(file, 64)

        normal = Vector3D(*read_vector3D(file))

        read_float(file)  # Face distance from origin
        read_int(file)  # Aligned axis (0=X, 1=Y, 2=Z, 3=Unaligned)

        # Check if texture exists, or try to extract it if not
        if name not in self.checked:
            if not self.wadhandler.check_texture(name):
                self.missing_textures = True
            self.checked.append(name)

        if name.lower() not in self.wadhandler.SKIP_TEXTURES:
            tex_image: ImageInfo = self.get_texture(name)
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

        points: List[JFaceVertex] = []
        for _ in range(vertex_count):
            vertex = read_vector3D(file)
            u = read_float(file)
            v = read_float(file)
            points.append(JFaceVertex(vertex, u, v))

            read_float(file)  # Selection state

        return Face(points, texture, normal)

    def get_texture(self, texture: str) -> ImageInfo:
        if texture not in self.textures:
            texfile = self.outputdir / f"{texture}.bmp"
            if not texfile.exists():
                raise MissingTextureException(
                    f"Could not find texture {texture}")

            with Image.open(texfile, 'r') as imgfile:
                self.textures[texture] = ImageInfo(
                    imgfile.width, imgfile.height
                )
        return self.textures[texture]
