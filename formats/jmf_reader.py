# -*- coding: utf-8 -*-
"""
Created on Fri Jul  7 20:01:25 2023

@author: Erty
"""

from PIL import Image
from pathlib import Path
from geoutil import PolyFace, triangulate_face
from formats import (read_bool, read_int, read_short, read_float, read_double,
                     read_ntstring, read_lpstring2, read_colour_rgba,
                     read_vector3D, read_angles,
                     InvalidFormatException, EndOfFileException,
                     MissingTextureException,
                     JFace, VisGroup, Brush, Entity, JGroup)
from formats.wad_handler import WadHandler


class JmfReader:
    """Reads a .jmf format file and parses geometry data."""

    def __init__(self, filepath: Path, outputdir: Path):
        self.filepath = filepath
        self.visgroups = {}
        self.entities = []
        self.brushes = []
        self.groups = []
        self.group_parents = {}
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
        group = JGroup(colour, group_id)

        return group, group_parent_id

    def getgroup(self, id: int) -> JGroup:
        for group in self.groups:
            if group.id == id:
                return group
        return None

    def readvisgroup(self, file) -> VisGroup:
        name = read_lpstring2(file)
        visgroup_id = read_int(file)
        colour = read_colour_rgba(file)
        visible = read_bool(file)
        return VisGroup(visgroup_id, name, colour, visible)

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
        for i in range(property_count):
            prop_n = read_lpstring2(file)
            properties[prop_n] = read_lpstring2(file)

        visgroup_ids = []
        visgroup_count = read_int(file)
        for i in range(visgroup_count):
            visgroup_ids.append(read_int(file))

        brushes = []
        brush_count = read_int(file)
        for i in range(brush_count):
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
        texture = {}

        read_int(file)  # render flags
        vertex_count = read_int(file)

        texture['rightaxis'] = read_vector3D(file)
        texture['shiftx'] = read_float(file)
        texture['downaxis'] = read_vector3D(file)
        texture['shifty'] = read_float(file)
        texture['scalex'] = read_float(file)
        texture['scaley'] = read_float(file)
        texture['angle'] = read_float(file)

        # padding?
        read_int(file)
        file.read(16)

        texture['name'] = read_ntstring(file, 64)

        normal = read_vector3D(file)

        read_float(file)
        read_int(file)

        # Check if texture exists, or try to extract it if not
        if texture['name'] not in self.checked:
            if not self.wadhandler.check_texture(texture['name']):
                self.missing_textures = True

            # Make note of masked textures
            if (texture['name'].startswith('{')
                    and texture['name'] not in self.maskedtextures):
                self.maskedtextures.append(texture['name'])
            self.checked.append(texture['name'])

        if texture['name'].lower() not in self.wadhandler.SKIP_TEXTURES:
            tex_image = self.get_texture(texture['name'])
            texture['width'] = tex_image['width']
            texture['height'] = tex_image['height']
        else:
            texture['width'] = 16
            texture['height'] = 16

        vertices = []
        for i in range(vertex_count):
            vertex = read_vector3D(file)
            vertex += (read_float(file), read_float(file))
            vertices.append(vertex)

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
