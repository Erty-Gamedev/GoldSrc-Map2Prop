# -*- coding: utf-8 -*-
"""
Created on Fri Jun  9 09:14:51 2023

@author: Erty
"""

from typing import List, Union, Tuple, Dict
from PIL import Image
from pathlib import Path
from geoutil import PolyFace, Vertex, ImageInfo, Texture, triangulate_face
from vector3d import Vector3D
from formats import (read_bool, read_int, read_float, read_ntstring,
                     read_lpstring, read_colour, read_vector3D,
                     InvalidFormatException, MissingTextureException,
                     Face, VisGroup, Brush, Entity, Group,
                     EntityPath, PathNode)
from formats.base_reader import BaseReader
from formats.wad_handler import WadHandler


class RmfReader(BaseReader):
    """Reads a .rmf format file and parses geometry data."""

    def __init__(self, filepath: Path, outputdir: Path):
        self.filepath: Path = filepath
        self.visgroups: Dict[str, str] = {}
        self.entities: List[Entity] = []
        self.brushes: List[Brush] = []
        self.groups: List[Group] = []
        self.properties: Dict[str, str] = {}
        self.entity_paths: List[EntityPath] = []

        self.allfaces: List[PolyFace] = []
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
            self.version = read_float(mapfile)

            magic = mapfile.read(3)
            if magic != bytes('RMF', 'ascii'):
                raise InvalidFormatException(
                    f"{self.filepath} is not a valid RMF file.")

            visgroups_count = read_int(mapfile)

            for i in range(visgroups_count):
                visgroup = self.readvisgroup(mapfile)
                self.visgroups[visgroup.id] = visgroup

            read_lpstring(mapfile)  # "CMapWorld"
            mapfile.read(7)  # Padding bytes?

            objects_count = read_int(mapfile)
            for i in range(objects_count):
                obj, vis_id = self.readobject(mapfile)
                if vis_id > 0 and vis_id in self.visgroups:
                    obj.visgroup = self.visgroups[vis_id]
                self.addobject(obj)

            read_lpstring(mapfile)  # "worldspawn"
            mapfile.read(4)  # Padding?
            self.properties['spawnflags'] = read_int(mapfile)

            worldspawn_properties_count = read_int(mapfile)
            for i in range(worldspawn_properties_count):
                p_name = read_lpstring(mapfile)
                self.properties[p_name] = read_lpstring(mapfile)
            mapfile.read(12)  # Padding?

            path_count = read_int(mapfile)
            for i in range(path_count):
                self.entity_paths.append(self.readpath(mapfile))

    def readvisgroup(self, file) -> VisGroup:
        name = read_ntstring(file, 128)
        colour = read_colour(file)
        file.read(1)  # Padding byte
        visgroup_id = read_int(file)
        visible = read_bool(file)
        file.read(3)  # Padding bytes
        return VisGroup(visgroup_id, name, colour, bool(visible))

    def readobject(
            self, file
        ) -> Union[Tuple[Brush, int], Tuple[Entity, int], Tuple[Group, int]]:
        typename = read_lpstring(file)

        if typename == 'CMapSolid':
            return self.readbrush(file)
        elif typename == 'CMapEntity':
            return self.readentity(file)
        elif typename == 'CMapGroup':
            return self.readgroup(file)
        else:
            raise Exception(f"Invalid object type: {typename}")

    def readbrush(self, file) -> Tuple[Brush, int]:
        visgroup_id = read_int(file)
        colour = read_colour(file)
        file.read(4)  # Padding?

        faces = []
        faces_count = read_int(file)
        for _ in range(faces_count):
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
        return Brush(faces, colour), visgroup_id

    def addpolyface(self, face: Face):
        tris = triangulate_face(face.points)

        for tri in tris:
            tri_face = []
            for p in tri:
                for vertex in face.vertices:
                    if p == vertex.v:
                        tri_face.append(vertex)
                        break

            polyface = PolyFace(tri_face, face.texture.name)

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

    def readface(self, file) -> Face:
        name = read_ntstring(file, 260)

        # Check if texture exists, or try to extract it if not
        if name not in self.checked:
            if not self.wadhandler.check_texture(name):
                self.missing_textures = True

            # Make note of masked textures
            if (name.startswith('{')
                    and name not in self.maskedtextures):
                self.maskedtextures.append(name)
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

        vertices: List[Tuple[float, float, float]] = []
        vertex_count = read_int(file)
        for _ in range(vertex_count):
            vertices.append(read_vector3D(file))
        vertices.reverse()

        plane_points = [
            read_vector3D(file),
            read_vector3D(file),
            read_vector3D(file),
        ]
        plane_points.reverse()

        return Face(vertices, plane_points, texture)

    def readentity(self, file) -> Tuple[Entity, int]:
        visgroup_id = read_int(file)
        colour = read_colour(file)

        brushes = []
        brush_count = read_int(file)
        for i in range(brush_count):
            read_lpstring(file)  # "CMapSolid"
            brush, _ = self.readbrush(file)
            brushes.append(brush)

        classname = read_lpstring(file)
        file.read(4)  # Padding?
        flags = read_int(file)

        properties = {}
        property_count = read_int(file)
        for i in range(property_count):
            prop_n = read_lpstring(file)
            properties[prop_n] = read_lpstring(file)

        file.read(14)  # More padding?

        origin = read_vector3D(file)

        file.read(4)  # Padding?

        return Entity(brushes, colour, classname, flags,
                      properties, origin), visgroup_id

    def readgroup(self, file) -> Tuple[Group, int]:
        visgroup_id = read_int(file)
        colour = read_colour(file)
        group = Group(colour, [])

        object_count = read_int(file)
        for _ in range(object_count):
            obj: Union[Brush, Entity, Group]
            obj, _ = self.readobject(file)
            obj.group = group
            group.objects.append(obj)

        return group, visgroup_id

    def addobject(self, obj: Union[Brush, Entity, Group]):
        if isinstance(obj, Entity):
            self.entities.append(obj)
        elif isinstance(obj, Brush):
            self.brushes.append(obj)
        elif isinstance(obj, Group):
            self.groups.append(obj)
            for child in obj.objects:
                self.addobject(child)

    def readpath(self, file) -> EntityPath:
        name = read_ntstring(file, 128)
        classname = read_ntstring(file, 128)
        pathtype = read_int(file)

        nodes = []
        node_count = read_int(file)
        for i in range(node_count):
            nodes.append(self.readpathnode(file))

        return EntityPath(name, classname, pathtype, nodes)

    def readpathnode(self, file) -> PathNode:
        position = read_vector3D(file)
        index = read_int(file)
        name_override = read_ntstring(file, 128)

        properties = {}
        property_count = read_int(file)
        for i in range(property_count):
            p_name = read_lpstring(file)
            properties[p_name] = read_lpstring(file)

        return PathNode(position, index, name_override, properties)
