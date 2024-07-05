from typing import List, Dict, Tuple, Any
from PIL import Image
from pathlib import Path
from io import TextIOWrapper
from formats.base_classes import BaseReader, BaseEntity, BaseBrush, BaseFace
from geoutil import (Polygon, Vertex, Plane, Vector3D, Texture, ImageInfo,
                     triangulate_face, intersection_3planes, sort_vertices,
                     is_vertex_outside_planes)
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
    pass

class Entity(BaseEntity):
    def __init__(self, classname: str, properties: Dict[str, str], brushes: List[Brush], raw: str):
        super().__init__(classname, properties, brushes)
        self._raw = raw
    @property
    def raw(self) -> str: return self._raw


class MapReader(BaseReader):
    """Reads a .map format file and parses geometry data."""

    def __init__(self, filepath: Path, outputdir: Path):
        self.filepath = filepath
        self.filedir = self.filepath.parent
        self.outputdir = outputdir
        self.wadhandler = WadHandler(self.filedir, outputdir)
        self.checked: List[str] = []
        self.textures: Dict[str, ImageInfo] = {}
        self.missing_textures = False
        self.entities: List[Entity] = []

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
        raw = "{\n"

        while line := file.readline():
            raw += line
            line = line.strip()

            if line.startswith('//'):  # skip comments
                continue
            elif line.startswith('"'):  # read keyvalues
                keyvalue = line.split('"')
                if len(keyvalue) > 5:
                    raise Exception(f"Invalid keyvalue: {keyvalue}.")
                key, value = keyvalue[1].strip(), keyvalue[3].strip()

                if key == 'classname':
                    classname = value.lower()
                elif key == 'wad' and classname == 'worldspawn':
                    self.wadhandler.set_wadlist(value.split(';'))

                properties[key] = value
            elif line.startswith('{'):
                brush, rawbrush = self.readbrush(file)
                brushes.append(brush)
                raw += rawbrush
            elif line.startswith('}'):
                break
            else:
                raise Exception(f"Unexpected entity data: {line}")
        return Entity(classname, properties, brushes, raw)

    def readbrush(self, file: TextIOWrapper) -> Tuple[Brush, str]:
        planes: List[Plane] = []
        raw = ''

        while line := file.readline():
            raw += line
            line = line.strip()

            if line.startswith('//'):
                continue
            elif line.startswith('('):
                planes.append(self.readplane(line))
            elif line.startswith('}'):
                break
            else:
                raise Exception(f"Unexpected face data: {line}")

        faces = self.faces_from_planes(planes)

        return Brush(faces), raw
    
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
            self.checked.append(name)

        if name.lower() not in self.wadhandler.SKIP_TEXTURES\
            and name.lower() not in self.wadhandler.TOOL_TEXTURES:
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
            texfile = self.outputdir / f"{texture}.bmp"
            if not texfile.exists():
                raise MissingTextureException(
                    f"Could not find texture {texture}")

            with Image.open(texfile, 'r') as imgfile:
                self.textures[texture] = ImageInfo(
                    imgfile.width, imgfile.height
                )
        return self.textures[texture]
