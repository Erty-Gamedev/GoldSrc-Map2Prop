# -*- coding: utf-8 -*-
"""
Created on Fri Jul  7 20:01:25 2023

@author: Erty
"""

from typing import Union, List, Dict, Tuple, Optional
from PIL import Image
from pathlib import Path
from vector3d import Vector3D
from geoutil import Polygon, Vertex, ImageInfo, Texture, triangulate_face
from formats import (read_bool, read_int, read_short, read_float, read_double,
                     read_ntstring, read_lpstring2, read_colour_rgba,
                     read_vector3D, read_angles,
                     InvalidFormatException, EndOfFileException,
                     MissingTextureException)
from formats.base_reader import BaseReader
from formats.wad_handler import WadHandler


class JFace:
    def __init__(
            self,
            points: List[Tuple[float, float, float, float, float]],
            texture: Texture,
            normal: Vector3D):
        self.points: List[Tuple[float, float, float]] = []
        self.texture: Texture = texture
        self.plane_normal: Vector3D = normal

        self.vertices = []

        for vertex in points:
            u, v = vertex[3:]
            vector = vertex[:3]
            self.vertices.append(Vertex(
                Vector3D(*vector),
                Vector3D(u, -v, 0),
                self.plane_normal
            ))
            self.points.append(vector)


class MapObject:
    def __init__(self, colour: tuple):
        self.colour = colour
        self.visgroup: Optional[VisGroup] = None
        self.group: Optional[Group] = None


class VisGroup:
    def __init__(self, id: int, name: str, colour: tuple, visible: bool):
        self.id = id
        self.name = name
        self.colour = colour
        self.visible = visible


class Brush(MapObject):
    def __init__(self, faces: list, colour: tuple):
        super().__init__(colour)
        self.faces = faces


class Group(MapObject):
    def __init__(self, colour: tuple, id: int):
        super().__init__(colour)
        self.id = id


class Entity:
    def __init__(self, brushes: list, colour: tuple, classname: str,
                 flags: int, properties: dict, origin: tuple) -> None:
        self.colour = colour
        self.visgroup: Optional[VisGroup] = None
        self.group: Optional[Group] = None
        self.brushes = brushes
        self.classname = classname
        self.flags = flags
        self.properties = properties
        if not brushes:
            self.origin = origin


class JmfReader(BaseReader):
    """Reads a .jmf format file and parses geometry data."""

    def __init__(self, filepath: Path, outputdir: Path):
        self.filepath: Path = filepath
        self.visgroups: Dict[str, str] = {}
        self.entities: List[Entity] = []
        self.brushes: List[Brush] = []
        self.groups: List[Group] = []
        self.group_parents: Dict[str, Group] = {}
        self.properties: Dict[str, str] = {}

        self.allfaces: List[Polygon] = []
        self.allvertices: List[Vertex] = []
        self.vn_map: Dict[Vector3D, List[Vector3D]] = {}
        self.maskedtextures: List[str] = []

        self.checked: List[str] = []
        self.textures: Dict[str, ImageInfo] = {}
        self.missing_textures: bool = False

        self.filedir: Path = self.filepath.parents[0]
        self.wadhandler = WadHandler(self.filedir, outputdir)

        self.parse()

    def parse(self):
        with self.filepath.open('rb') as mapfile:
            magic = mapfile.read(4)
            if magic != bytes('JHMF', 'ascii'):
                raise InvalidFormatException(
                    f"{self.filepath} is not a valid JMF file.")

            # JMF format version.
            # Was 121 before december 2023 update, became 122 after.
            jmf_version = read_int(mapfile)

            export_path_count = read_int(mapfile)
            for i in range(export_path_count):
                read_lpstring2(mapfile)

            if jmf_version >= 122:
                for i in range(3):
                    self.readbgimage(mapfile)

            group_count = read_int(mapfile)
            for i in range(group_count):
                group, group_parent_id = self.readgroup(mapfile)
                if group_parent_id != 0:
                    self.group_parents[group.id] = group_parent_id
                self.groups.append(group)

            visgroups_count = read_int(mapfile)
            for i in range(visgroups_count):
                self.readvisgroup(mapfile)

            read_vector3D(mapfile)  # Cordon minimum
            read_vector3D(mapfile)  # Cordon maximum

            camera_count = read_int(mapfile)
            for i in range(camera_count):
                self.readcamera(mapfile)

            path_count = read_int(mapfile)
            for i in range(path_count):
                self.readpath(mapfile)

            try:
                while True:
                    entity = self.readentity(mapfile)
                    if entity.classname == 'worldspawn':
                        self.brushes.extend(entity.brushes)

                        self.properties = entity.properties
                    else:
                        self.entities.append(entity)
            except EndOfFileException:
                pass

    def readbgimage(self, file):
        read_lpstring2(file)  # Image path
        read_double(file)  # Scale
        read_int(file)  # Luminance
        read_int(file)  # Filtering (0=near/1=lin)
        read_int(file)  # Invert colours
        read_int(file)  # X offset
        read_int(file)  # Y offset
        read_int(file)  # Padding?

    def readgroup(self, file) -> tuple:
        group_id = read_int(file)
        group_parent_id = read_int(file)
        read_int(file)  # flags
        read_int(file)  # count
        colour = read_colour_rgba(file)
        group = Group(colour, group_id)

        return group, group_parent_id

    def getgroup(self, id: int) -> Union[Group, None]:
        for group in self.groups:
            if group.id == id:
                return group
        return None

    def readvisgroup(self, file) -> VisGroup:
        name = read_lpstring2(file)
        visgroup_id = read_int(file)
        colour = read_colour_rgba(file)
        visible = read_bool(file)
        return VisGroup(visgroup_id, name, colour, bool(visible))

    def readcamera(self, file):
        read_vector3D(file)  # eye position
        read_vector3D(file)  # look target
        read_int(file)  # flags (bit 0x02 for is selected)
        read_colour_rgba(file)

    def readpath(self, file):
        read_lpstring2(file)  # classname
        read_lpstring2(file)  # name
        read_int(file)  # path type
        file.read(4)  # padding?
        read_colour_rgba(file)  # colour

        node_count = read_int(file)
        for i in range(node_count):
            self.readpathnode(file)

    def readpathnode(self, file):
        read_lpstring2(file)  # name override
        read_lpstring2(file)  # fire on target
        read_vector3D(file)  # position

        read_angles(file)  # angles
        read_int(file)  # flags
        read_colour_rgba(file)  # colour

        property_count = read_int(file)
        for i in range(property_count):
            read_lpstring2(file)  # key
            read_lpstring2(file)  # value

    def readentity(self, file) -> Entity:
        classname = read_lpstring2(file)
        origin = read_vector3D(file)
        read_int(file)  # Jack editor state
        group_id = read_int(file)
        read_int(file)  # root group id
        colour = read_colour_rgba(file)

        # special attributes, irrelevant for us
        for i in range(13):
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
            prop_n = read_lpstring2(file)
            properties[prop_n] = read_lpstring2(file)

        visgroup_ids = []
        visgroup_count = read_int(file)
        for _ in range(visgroup_count):
            visgroup_ids.append(read_int(file))

        brushes = []
        brush_count = read_int(file)
        for _ in range(brush_count):
            brushes.append(self.readbrush(file))

        entity = Entity(brushes, colour, classname, spawnflags,
                        properties, origin)
        entity.group = self.getgroup(group_id)

        return entity

    def readbrush(self, file) -> Brush:
        curves_count = read_int(file)
        read_int(file)  # Jack editor state
        group_id = read_int(file)
        read_int(file)  # root group id
        colour = read_colour_rgba(file)

        visgroup_count = read_int(file)
        for i in range(visgroup_count):
            read_int(file)

        faces = []
        faces_count = read_int(file)
        for i in range(faces_count):
            face = self.readface(file)

            if self.wadhandler.skip_face(face.texture.name):
                continue

            self.addpolyface(face)
            for vertex in face.vertices:
                if vertex not in self.allvertices:
                    self.allvertices.append(vertex)
                    if vertex.v not in self.vn_map:
                        self.vn_map[vertex.v] = []
                    self.vn_map[vertex.v].append(vertex.n)
            faces.append(face)

        for i in range(curves_count):
            self.readcurve(file)

        brush = Brush(faces, colour)
        brush.group = self.getgroup(group_id)

        return Brush(faces, colour)

    def readcurve(self, file) -> None:
        read_int(file)  # width
        read_int(file)  # height

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

        for i in range(1024):
            self.readcurvepoint(file)

    def readcurvepoint(self, file) -> None:
        read_vector3D(file)  # position
        read_vector3D(file)  # normal
        read_vector3D(file)  # texture_uv

    def readface(self, file) -> JFace:
        read_int(file)  # render flags
        vertex_count = read_int(file)

        rightaxis= read_vector3D(file)
        shiftx = read_float(file)
        downaxis = read_vector3D(file)
        shifty = read_float(file)
        scalex = read_float(file)
        scaley = read_float(file)
        angle = read_float(file)

        # padding?
        read_int(file)
        file.read(16)

        name = read_ntstring(file, 64)

        normal = Vector3D(*read_vector3D(file))

        read_float(file)
        read_int(file)

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

        vertices: List[Tuple[float, float, float, float, float]] = []
        for _ in range(vertex_count):
            vertex = read_vector3D(file)
            vertices.append(vertex + (read_float(file), read_float(file)))

            read_float(file)  # Selection state

        return JFace(vertices, texture, normal)

    def addpolyface(self, face: JFace):
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
