from typing import List, Dict, Final, Literal
from pathlib import Path
import logging
from triangulate.triangulate import triangulate
from geoutil import Vector3D, Vertex, Polygon, Texture, ImageInfo
from formats.base_classes import BaseReader, BaseEntity, BaseFace, BaseBrush
from formats.wad_handler import WadHandler


logger = logging.getLogger(__name__)

mtllib_prefix: Final[Literal['mtllib ']] = 'mtllib '
mtl_prefix: Final[Literal['newmtl ']] = 'newmtl '
mtl_map_prefix: Final[Literal['map_Ka ']] = 'map_Ka '

object_prefix: Final[Literal['o ']] = 'o '
group_prefix: Final[Literal['g ']] = 'g '
smooth_prefix: Final[Literal['s ']] = 's '
usemtl_prefix: Final[Literal['usemtl ']] = 'usemtl '

vertex_prefix: Final[Literal['v ']] = 'v '           # (x y z)
texture_coord_prefix: Final[Literal['vt ']] = 'vt '  # (u v w)
vertex_normal_prefix: Final[Literal['vn ']] = 'vn '  # (x y z)
poly_face_prefix: Final[Literal['f ']] = 'f '        # (vertex_index/texture_index/normal_index)
# Note: The above indices are 1-indexed


class ObjGroup:
    def __init__(self, name: str):
        self.name: str = name
        self.faces: List[Face] = []

class ObjObject:
    def __init__(self, name: str, smooth: str = 'off'):
        self.name: str = name
        self.smooth: str = smooth
        self.groups: Dict[str, ObjGroup] = {}


class Face(BaseFace):
    def __init__(self, points: List[Vector3D], vertices: List[Vertex], texture: str):
        self._points = points
        self._vertices = vertices
        self._polygons: List[Polygon] = []
        self._texture = Texture(texture)

        for triangle in triangulate(self._points):
            polygon = []
            for point in triangle:
                for vertex in self._vertices:
                    if point == vertex.v:
                        polygon.append(vertex)
                        break
            self._polygons.append(Polygon(polygon, texture))
    @property
    def points(self): return self._points
    @property
    def vertices(self): return self._vertices
    @property
    def polygons(self): return self._polygons
    @property
    def texture(self): return self._texture


class Brush(BaseBrush):
    pass
class Entity(BaseEntity):
    pass


def parseCoord(coord: str) -> Vector3D:
    coords: List[str] = coord.split(' ')
    return Vector3D(*[float(n) for n in coords])


class ObjReader(BaseReader):
    """Reads an .obj format file and parses geometry data."""

    def __init__(self, filepath: Path, outputdir: Path):
        self.filepath = filepath
        self.filedir = self.filepath.parent
        self.outputdir = outputdir
        self.wadhandler = WadHandler(self.filedir, outputdir)
        self.checked: List[str] = []
        self.textures: Dict[str, ImageInfo] = {}
        self.missing_textures = False
        self.entities: List[BaseEntity] = []

        self.vertexcoords: List[Vector3D] = []
        self.texturecoords: List[Vector3D] = []
        self.normalcoords: List[Vector3D] = []

        self.objects: Dict[str, ObjObject] = {}

        self.parse()

    def parse(self) -> None:
        objects: Dict[str, ObjObject] = {}

        with self.filepath.open('r') as objfile:
            current_obj = ''

            for line in objfile:
                # Skip comments
                if line.startswith('#'):
                    continue

                # Get rid of trailing linebreaks and such
                line = line.rstrip()

                # Parse coordinates:
                if line.startswith(vertex_prefix):
                    coord = line[len(vertex_prefix):]
                    self.vertexcoords.append(parseCoord(coord))
                elif line.startswith(texture_coord_prefix):
                    coord = line[len(texture_coord_prefix):]
                    self.texturecoords.append(parseCoord(coord))
                elif line.startswith(vertex_normal_prefix):
                    coord = line[len(vertex_normal_prefix):]
                    self.normalcoords.append(parseCoord(coord))

                # Parse objects and brushes:
                elif line.startswith(object_prefix):
                    current_obj = line[len(object_prefix):]
                    objects[current_obj] = ObjObject(current_obj)
                elif line.startswith(smooth_prefix):
                    objects[current_obj].smooth = (
                        line[len(smooth_prefix):])
                elif line.startswith(group_prefix):
                    group = line[len(group_prefix):]
                    objects[current_obj].groups[group] = ObjGroup(group)

                # Parse textures:
                elif line.startswith(usemtl_prefix):
                    tex = line[len(usemtl_prefix):]

                    # Check if texture exists, or try to extract it if not
                    if tex not in self.checked:
                        if not self.wadhandler.check_texture(tex):
                            self.missing_textures = True
                        self.checked.append(tex)

                # Parse faces:
                elif line.startswith(poly_face_prefix):
                    if tex.lower() in self.wadhandler.SKIP_TEXTURES:
                        continue

                    facepoints = line[len(poly_face_prefix):].split(' ')

                    points: List[Vector3D] = []
                    vertices: List[Vertex] = []
                    for facepoint in facepoints:
                        i_v, i_t, i_n = [int(n) for n in facepoint.split('/')]
                        vertex = Vertex(
                            self.vertexcoords[i_v - 1],
                            self.texturecoords[i_t - 1],
                            self.normalcoords[i_n - 1]
                        )
                        vertices.append(vertex)
                        points.append(self.vertexcoords[i_v - 1])
                    
                    objects[current_obj].groups[group].faces.append(
                        Face(points, vertices, tex))

        self.process_objects(objects)

    def process_objects(self, objects: Dict[str, ObjObject]) -> None:
        for object in objects.values():
            name = object.name.lower()
            if 'entity' in name:
                classname = name[name.find('(') + 1 : name.find(')')]
                brushes: List[Brush] = []
                for group in object.groups.values():
                    brushes.append(Brush(group.faces))
                self.entities.append(Entity(classname, {}, brushes))
