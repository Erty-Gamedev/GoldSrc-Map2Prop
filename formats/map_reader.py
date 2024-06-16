# -*- coding: utf-8 -*-

from typing import List, Dict, Tuple, Any
from PIL import Image
from pathlib import Path
from io import TextIOWrapper
from formats.base_classes import BaseReader, BaseEntity, BaseBrush, BaseFace
from geoutil import (Polygon, Vertex, Plane, Vector3D, Texture, ImageInfo,
                     triangulate_face, intersection_3planes, sort_vertices,
                     is_vertex_outside_planes, geometric_center, bounds_from_points)
from formats import MissingTextureException
from formats.wad_handler import WadHandler


class Face(BaseFace):
    def __init__(self, points: List[Vector3D], texture: Texture, normal: Vector3D):
        self._points = sort_vertices(points, normal)
        self._vertices = []
        self._polygons = []
        self._texture = texture
        self._normal = normal

        nu, nv = texture.rightaxis, texture.downaxis
        w, h = texture.width, texture.height
        su, sv = texture.scalex, texture.scaley
        ou, ov = texture.shiftx, texture.shifty

        for point in self._points:
            u = (point.dot(nu)/w)/su + ou/w
            v = (point.dot(nv)/h)/sv + ov/h

            self._vertices.append(Vertex(
                point,
                Vector3D(u, -v, 0),
                normal
            ))
        
        for triangle in triangulate_face(self._points):
            polygon = []
            for point in triangle:
                for vertex in self._vertices:
                    if point == vertex.v:
                        polygon.append(vertex)
                        break
            self._polygons.append(Polygon(polygon, texture.name))
        # TODO: normalize UV

    @property
    def points(self): return self._points
    @property
    def vertices(self): return self._vertices
    @property
    def polygons(self): return self._polygons
    @property
    def texture(self): return self._texture
    @property
    def normal(self): return self._normal


class Brush(BaseBrush):
    def __init__(self, faces: List[Face]):
        self._faces: List[Face] = faces
        self._all_points: List[Vector3D] = []
        for face in faces:
            self._all_points.extend(face.points)
        self._all_polygons: List[Polygon] = []
        for face in faces:
            if face.texture.name.lower() in WadHandler.TOOL_TEXTURES:
                continue
            self._all_polygons.extend(face.polygons)
    @property
    def faces(self) -> List[Face]: return self._faces
    @property
    def all_points(self) -> List[Vector3D]: return self._all_points
    @property
    def all_polygons(self) -> List[Vertex]: return self._all_polygons

    @property
    def is_origin(self) -> bool:
        for face in self.faces:
            if face.texture.name.lower() != 'origin':
                return False
        return True
    
    @property
    def has_contentwater(self) -> bool:
        for face in self.faces:
            if face.texture.name.lower() == 'contentwater':
                return True
        return False
    
    def bounds(self) -> Tuple[Vector3D, Vector3D]:
        return bounds_from_points(self.all_points)
    
    @property
    def center(self) -> Vector3D:
        return geometric_center(self.all_points)


class Entity(BaseEntity):
    def __init__(self, classname: str, properties: Dict[str, str], brushes: List[Brush]):
        self._classname = classname
        self._properties = properties
        self._brushes = brushes
    
    @property
    def classname(self):
        return self._classname
    @property
    def properties(self):
        return self._properties
    @property
    def brushes(self):
        return self._brushes


class MapReader(BaseReader):
    """Reads a .map format file and parses geometry data."""

    def __init__(self, filepath: Path, outputdir: Path):
        self.filepath = filepath
        self.filedir = self.filepath.parents[0]
        self.outputdir = outputdir
        self.wadhandler = WadHandler(self.filedir, outputdir)
        self.checked: List[str] = []
        self.textures: Dict[str, ImageInfo] = {}
        
        self.allfaces = []
        self.allvertices = []
        self.vn_map = {}
        self.maskedtextures = []
        self.missing_textures = False
        self.entities = []

        self.parse()

    def parse(self):
        with self.filepath.open('r') as file:
            while line := file.readline().strip():
                if line.startswith('{'):
                    entity = self.readentity(file)
                    self.entities.append(entity)

    def readentity(self, file: TextIOWrapper) -> Entity:
        classname = ''
        properties: Dict[str, str] = {}
        brushes: List[Brush] = []

        while line := file.readline().strip():
            if line.startswith('//'):  # skip comments
                continue
            elif line.startswith('"'):  # read keyvalues
                keyvalue = line.split('"')
                if len(keyvalue) > 5:
                    raise Exception(f"Invalid keyvalue: {keyvalue}.")
                key, value = keyvalue[1].strip(), keyvalue[3].strip()

                if key == 'classname':
                    classname = value
                elif key == 'wad' and classname == 'worldspawn':
                    self.wadhandler.set_wadlist(value.split(';'))

                properties[key] = value
            elif line.startswith('{'):
                brush = self.readbrush(file)
                brushes.append(brush)
            elif line.startswith('}'):
                break
            else:
                raise Exception(f"Unexpected entity data: {line}")
        return Entity(classname, properties, brushes)

    def readbrush(self, file: TextIOWrapper) -> Brush:
        planes: List[Plane] = []

        while line := file.readline().strip():
            if line.startswith('//'):
                continue
            elif line.startswith('('):
                planes.append(self.readplane(line))
            elif line.startswith('}'):
                break
            else:
                raise Exception(f"Unexpected face data: {line}")

        faces = self.faces_from_planes(planes)

        return Brush(faces)
    
    def readplane(self, line: str) -> Plane:
        parts = line.split()
        if len(parts) != 31:
            raise Exception(f"Unexpected face data: {line}")

        plane_points: List[Tuple[float, float, float]] = [
            (float(parts[1]), float(parts[2]), float(parts[3])),
            (float(parts[6]), float(parts[7]), float(parts[8])),
            (float(parts[11]), float(parts[12]), float(parts[13]))
        ]

        name = parts[15]

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
            tex_image = self.get_texture(name)
            width = tex_image.width
            height = tex_image.height
        else:
            width = 16
            height = 16

        texture = Texture(
            name,
            (float(parts[17]), float(parts[18]), float(parts[19])),
            float(parts[20]),
            (float(parts[23]), float(parts[24]), float(parts[25])),
            float(parts[26]),
            float(parts[28]),
            float(parts[29]),
            float(parts[30]),
            width, height
        )

        return Plane(plane_points, texture)

    def faces_from_planes(self, planes: List[Plane]) -> List[Face]:
        num_planes = len(planes)
        faces: List[Dict[str, Any]] = [{'vertices': []} for _ in range(num_planes)]

        for i in range(num_planes):
            for j in range(i + 1, num_planes):
                for k in range(j + 1, num_planes):
                    if i == j == k:
                        continue

                    vertex = intersection_3planes(
                        planes[i], planes[j], planes[k]
                    )

                    if vertex is False:
                        continue

                    if is_vertex_outside_planes(vertex, planes):
                        continue

                    faces[i]['vertices'].append(vertex)
                    faces[j]['vertices'].append(vertex)
                    faces[k]['vertices'].append(vertex)

                    faces[i]['texture'] = planes[i].texture
                    faces[j]['texture'] = planes[j].texture
                    faces[k]['texture'] = planes[k].texture

                    faces[i]['normal'] = planes[i].normal
                    faces[j]['normal'] = planes[j].normal
                    faces[k]['normal'] = planes[k].normal

        return [Face(f['vertices'], f['texture'], f['normal'])
                for f in faces if not self.wadhandler.skip_face(f['texture'].name)]

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
