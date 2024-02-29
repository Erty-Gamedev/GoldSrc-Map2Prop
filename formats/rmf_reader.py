# -*- coding: utf-8 -*-
"""
Created on Fri Jun  9 09:14:51 2023

@author: Erty
"""

from PIL import Image
from pathlib import Path
from geoutil import PolyFace, triangulate_face
from formats import (read_bool, read_int, read_float, read_ntstring,
                     read_lpstring, read_colour, read_vector3D,
                     InvalidFormatException, MissingTextureException,
                     Face, VisGroup, MapObject, Brush, Entity, Group,
                     EntityPath, PathNode)
from formats.base_reader import BaseReader
from formats.wad_handler import WadHandler


class RmfReader(BaseReader):
    """Reads a .rmf format file and parses geometry data."""

    def __init__(self, filepath: Path, outputdir: Path):
        self.filepath = filepath
        self.visgroups = {}
        self.entities = []
        self.brushes = []
        self.groups = []
        self.properties = {}
        self.entity_paths = []

        self.allfaces = []
        self.allvertices = []
        self.vn_map = {}
        self.maskedtextures = []

        self.checked = []
        self.textures = {}
        self.missing_textures = False

        self.filedir = self.filepath.parents[0]
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
        return VisGroup(visgroup_id, name, colour, visible)

    def readobject(self, file) -> tuple:
        typename = read_lpstring(file)

        if typename == 'CMapSolid':
            return self.readbrush(file)
        elif typename == 'CMapEntity':
            return self.readentity(file)
        elif typename == 'CMapGroup':
            return self.readgroup(file)
        else:
            raise Exception(f"Invalid object type: {typename}")

    def readbrush(self, file) -> Brush:
        visgroup_id = read_int(file)
        colour = read_colour(file)
        file.read(4)  # Padding?

        faces = []
        faces_count = read_int(file)
        for i in range(faces_count):
            face = self.readface(file)

            if self.wadhandler.skip_face(face):
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

            polyface = PolyFace(tri_face, face.texture['name'])

            self.allfaces.append(polyface)

    def get_texture(self, texture: str) -> Image:
        if texture not in self.textures:
            texfile = self.filedir / f"{texture}.bmp"
            if not texfile.exists():
                raise MissingTextureException(
                    f"Could not find texture {texture}")

            with Image.open(texfile, 'r') as imgfile:
                self.textures[texture] = {
                    'width': imgfile.width,
                    'height': imgfile.height
                }
        return self.textures[texture]

    def readface(self, file) -> Face:
        texture = {'name': read_ntstring(file, 256)}

        # Check if texture exists, or try to extract it if not
        if texture['name'] not in self.checked:
            if not self.wadhandler.check_texture(texture['name']):
                self.missing_textures = True

            # Make note of masked textures
            if (texture['name'].startswith('{')
                    and texture['name'] not in self.maskedtextures):
                self.maskedtextures.append(texture['name'])
            self.checked.append(texture['name'])

        file.read(4)  # Padding? Note: MESS reads these 4 as a float

        texture['rightaxis'] = read_vector3D(file)
        texture['shiftx'] = read_float(file)
        texture['downaxis'] = read_vector3D(file)
        texture['shifty'] = read_float(file)
        texture['angle'] = read_float(file)
        texture['scalex'] = read_float(file)
        texture['scaley'] = read_float(file)

        if texture['name'].lower() not in self.wadhandler.SKIP_TEXTURES:
            tex_image = self.get_texture(texture['name'])
            texture['width'] = tex_image['width']
            texture['height'] = tex_image['height']
        else:
            texture['width'] = 16
            texture['height'] = 16

        file.read(16)  # Padding

        vertices = []
        vertex_count = read_int(file)
        for i in range(vertex_count):
            vertices.append(read_vector3D(file))
        vertices.reverse()

        plane_points = [
            read_vector3D(file),
            read_vector3D(file),
            read_vector3D(file),
        ]
        plane_points.reverse()

        return Face(vertices, plane_points, texture)

    def readentity(self, file) -> Entity:
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

    def readgroup(self, file) -> tuple:
        visgroup_id = read_int(file)
        colour = read_colour(file)
        group = Group(colour, [])

        object_count = read_int(file)
        for i in range(object_count):
            obj, _ = self.readobject(file)
            obj.group = group
            group.objects.append(obj)

        return group, visgroup_id

    def addobject(self, obj: MapObject):
        if isinstance(obj, Entity):
            self.entities.append(obj)
        elif isinstance(obj, Brush):
            self.brushes.append(obj)
        elif isinstance(obj, Group):
            obj.id = len(self.groups)
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
            properties[p_name] = read_lpstring()

        return PathNode(position, index, name_override, properties)
