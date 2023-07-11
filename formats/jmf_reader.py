# -*- coding: utf-8 -*-
"""
Created on Fri Jul  7 20:01:25 2023

@author: Erty
"""

from PIL import Image
from pathlib import Path
from geoutil import (PolyFace, InvalidSolidException, triangulate_face)
from formats import (read_byte, read_int, read_short, read_float,
                     read_ntstring, read_lpstring2, read_colour_rgba,
                     read_vector3D, read_angles,
                     InvalidFormatException, EndOfFileException,
                     MissingTextureException,
                     Face, VisGroup, Brush, Entity, JGroup)
from formats.wad_handler import WadHandler


class JmfReader:
    """Reads a .jmf format file and parses geometry data."""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.visgroups = {}
        self.entities = []
        self.brushes = []
        self.groups = []
        self.group_parents = {}
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
        self.wadhandler = WadHandler(self.__filedir)

        self.__parse()

    def __parse(self):
        with self.filepath.open('rb') as mapfile:
            magic = mapfile.read(4)
            if magic != bytes('JHMF', 'ascii'):
                raise InvalidFormatException(
                    f"{self.filepath} is not a valid JMF file.")

            mapfile.read(4)  # Padding? Read 121 as int during an early test

            export_path_count = read_int(mapfile)
            for i in range(export_path_count):
                read_lpstring2(mapfile)

            group_count = read_int(mapfile)
            for i in range(group_count):
                group, group_parent_id = self.__readgroup(mapfile)
                if group_parent_id != 0:
                    self.group_parents[group.id] = group_parent_id
                self.groups.append(group)

            visgroups_count = read_int(mapfile)
            for i in range(visgroups_count):
                self.__readvisgroup(mapfile)

            read_vector3D(mapfile)  # Cordon minimum
            read_vector3D(mapfile)  # Cordon maximum

            camera_count = read_int(mapfile)
            for i in range(camera_count):
                self.__readcamera(mapfile)

            path_count = read_int(mapfile)
            for i in range(path_count):
                self.__readpath(mapfile)

            try:
                while True:
                    entity = self.__readentity(mapfile)
                    if entity.classname == 'worldspawn':
                        self.brushes.extend(entity.brushes)

                        self.properties = entity.properties
                    else:
                        self.entities.append(entity)
            except EndOfFileException:
                pass

    def __readgroup(self, file) -> tuple:
        group_id = read_int(file)
        group_parent_id = read_int(file)
        read_int(file)  # flags
        read_int(file)  # count
        colour = read_colour_rgba(file)
        group = JGroup(colour, group_id)

        return group, group_parent_id

    def __getgroup(self, id: int) -> JGroup:
        for group in self.groups:
            if group.id == id:
                return group
        return None

    def __readvisgroup(self, file) -> VisGroup:
        name = read_lpstring2(file)
        visgroup_id = read_int(file)
        colour = read_colour_rgba(file)
        visible = bool(read_byte(file))
        return VisGroup(visgroup_id, name, colour, visible)

    def __readcamera(self, file):
        read_vector3D(file)  # eye position
        read_vector3D(file)  # look target
        read_int(file)  # flags (bit 0x02 for is selected)
        read_colour_rgba(file)

    def __readpath(self, file):
        read_lpstring2(file)  # classname
        read_lpstring2(file)  # name
        read_int(file)  # path type
        file.read(4)  # padding?
        read_colour_rgba(file)  # colour

        node_count = read_int(file)
        for i in range(node_count):
            self.__readpathnode(file)

    def __readpathnode(self, file):
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

    def __readentity(self, file) -> Entity:
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
            brushes.append(self.__readbrush(file))

        entity = Entity(brushes, colour, classname, spawnflags,
                        properties, origin)
        entity.group = self.__getgroup(group_id)

        return entity

    def __readbrush(self, file) -> Brush:
        read_int(file)  # curves count
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
            face = self.__readface(file)

            if self.wadhandler.skip_face(face):
                continue

            self.__addpolyface(face)
            for polypoint in face.polypoints:
                if polypoint not in self.allpolypoints:
                    self.allpolypoints.append(polypoint)
                    if polypoint.v not in self.vn_map:
                        self.vn_map[polypoint.v] = []
                    self.vn_map[polypoint.v].append(polypoint.n)
            faces.append(face)
        brush = Brush(faces, colour)
        brush.group = self.__getgroup(group_id)

        return Brush(faces, colour)

    def __readface(self, file) -> Face:
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

        # more padding?
        read_float(file)
        read_float(file)
        read_float(file)
        read_float(file)
        read_int(file)

        # Check if texture exists, or try to extract it if not
        if texture['name'] not in self.__checked:
            if not self.wadhandler.check_texture(texture['name']):
                self.missing_textures = True

            # Make note of masked textures
            if (texture['name'].startswith('{')
                    and texture['name'] not in self.maskedtextures):
                self.maskedtextures.append(texture['name'])
            self.__checked.append(texture['name'])

        if texture['name'].lower() not in self.wadhandler.SKIP_TEXTURES:
            tex_image = self.__gettexture(texture['name'])
            texture['width'] = tex_image['width']
            texture['height'] = tex_image['height']
        else:
            texture['width'] = 16
            texture['height'] = 16

        vertices = []
        for i in range(vertex_count):
            vertices.append(read_vector3D(file))

            # MESS speculates this is normal vector?
            read_float(file)
            read_float(file)
            read_float(file)

        plane_points = vertices[:3]

        return Face(vertices, plane_points, texture)

    def __addpolyface(self, face: Face):
        try:
            tris = triangulate_face(face.vertices)
        except Exception:
            self.__logger.exception('Face triangulation failed')
            raise

        for tri in tris:
            tri_face = []
            for p in tri:
                for polyp in face.polypoints:
                    if p == polyp.v:
                        tri_face.append(polyp)
                        break

            try:
                polyface = PolyFace(tri_face, face.texture['name'])
            except InvalidSolidException as ise:
                self.__logger.error(
                    "Object had one or more invalid faces: " +
                    f"{ise.message}")
                raise

            self.allfaces.append(polyface)

    def __gettexture(self, texture: str) -> Image:
        if texture not in self.__textures:
            texfile = self.__filedir / f"{texture}.bmp"
            if not texfile.exists():
                raise MissingTextureException(
                    f"Could not find texture {texture}")

            with Image.open(texfile, 'r') as imgfile:
                self.__textures[texture] = {
                    'width': imgfile.width,
                    'height': imgfile.height
                }
        return self.__textures[texture]
