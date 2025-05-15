"""
Base classes for map file readers and map objects
"""


from typing import Sequence, Final
from abc import ABC
from pathlib import Path
from geoutil import (Polygon, Vertex, Vector3D, Texture,
                     bounds_from_points, geometric_center, sort_vertices)
from formats.wad_handler import WadHandler


MAP_NDIGITS: Final[int] = 6


class BaseFace(ABC):
    def __init__(self, points: list[Vector3D], texture: Texture, normal: Vector3D):
        self._points = points
        self._plane_points: tuple[Vector3D, Vector3D, Vector3D]
        self._vertices: list[Vertex] = []
        self._polygons: list[Polygon] = []
        self._texture = texture
        self._normal = normal

    @property
    def points(self) -> list[Vector3D]: return self._points
    @property
    def vertices(self) -> list[Vertex]: return self._vertices
    @property
    def polygons(self) -> list[Polygon]: return self._polygons
    @property
    def texture(self) -> Texture: return self._texture
    @property
    def normal(self) -> Vector3D: return self._normal
    @property
    def plane_points(self) -> tuple[Vector3D, Vector3D, Vector3D]: return self._plane_points
    def __repr__(self) -> str: return f"Face({self.texture.name})"
    
    def project_uv(self, point: Vector3D):
        nu, nv = self.texture.rightaxis, self.texture.downaxis
        w, h = self.texture.width, self.texture.height
        su, sv = self.texture.scalex, self.texture.scaley
        ou, ov = self.texture.shiftx, self.texture.shifty

        return (point.dot(nu)/w)/su + ou/w, (point.dot(nv)/h)/sv + ov/h


class BaseBrush(ABC):
    def __init__(self, faces: Sequence[BaseFace]):
        self._faces = faces
        self._all_points: list[Vector3D] = []
        self._all_polygons: list[Polygon] = []
        self._maskedtextures: list[str] = []
        for face in faces:
            self._all_points.extend(face.points)
            if (face.texture.name.lower() in WadHandler.TOOL_TEXTURES
                or face.texture.name.lower() in WadHandler.SKIP_TEXTURES):
                continue
            self._all_polygons.extend(face.polygons)
            if face.texture.name.startswith('{') \
                and face.texture.name not in self._maskedtextures:
                self._maskedtextures.append(face.texture.name)
    @property
    def faces(self): return self._faces
    @property
    def all_points(self): return self._all_points
    @property
    def all_polygons(self): return self._all_polygons
    @property
    def maskedtextures(self): return self._maskedtextures
    def is_tool_brush(self, tool_texture: str) -> bool:
        for face in self.faces:
            if face.texture.name.lower() != tool_texture:
                return False
        return True
    @property
    def has_contentwater(self) -> bool:
        for face in self.faces:
            if face.texture.name.lower() == 'contentwater':
                return True
        return False
    @property
    def bounds(self) -> tuple[Vector3D, Vector3D]:
        return bounds_from_points(self.all_points)
    @property
    def center(self) -> Vector3D:
        return geometric_center(self.all_points)
    def __repr__(self) -> str: return f"Brush({len(self.faces)} faces)"

    def raw(self) -> str:
        raw = "{\n"
        # ( x1 y1 z1 ) ( x2 y2 z2 ) ( x3 y3 z3 ) TEXTURENAME [ Ux Uy Uz Uoffset ] [ Vx Vy Vz Voffset ] rotation Uscale Vscale
        
        # ( 1 2 3 ) ( 1 2 3 ) ( 1 -2 3 ) C1A0_LABW4 [ 1 0 0 0 ] [ 0 -1 0 0 ] 0 1 1 

        f = f".{MAP_NDIGITS}g"
        for face in self.faces:
            x, y, z = face.plane_points
            ux, uy, uz = face.texture.rightaxis
            vx, vy, vz = face.texture.downaxis
            shiftx, shifty = face.texture.shiftx, face.texture.shifty
            r, scalex, scaley = face.texture.angle, face.texture.scalex, face.texture.scaley

            raw += f"( {x.x:{f}} {x.y:{f}} {x.z:{f}} ) "\
                    f"( {y.x:{f}} {y.y:{f}} {y.z:{f}} ) "\
                    f"( {z.x:{f}} {z.y:{f}} {z.z:{f}} ) "\
                    f"{face.texture.name} "\
                    f"[ {ux:{f}} {uy:{f}} {uz:{f}} {shiftx:{f}} ] "\
                    f"[ {vx:{f}} {vy:{f}} {vz:{f}} {shifty:{f}} ] "\
                    f"{r:{f}} {scalex:{f}} {scaley:{f}}\n"
        raw += "}\n"
        return raw


class BaseEntity(ABC):
    def __init__(self, classname: str, properties: dict[str, str], brushes: Sequence[BaseBrush]):
        self._classname = classname
        self._properties = properties
        self._brushes = brushes
    @property
    def classname(self): return self._classname
    @property
    def properties(self): return self._properties
    @property
    def brushes(self): return self._brushes
    def __repr__(self) -> str: return f"Entity({self.classname})"

    # @property
    def raw(self) -> str:
        is_worldspawn = self.classname.lower() == 'worldspawn'
        kvs = "{\n" f"\"classname\" \"{self.classname}\"\n"

        for key, value in self.properties.items():
            if is_worldspawn and key.lower() == 'spawnflags':
                kvs += "\"mapversion\" \"220\"\n"
                continue
            kvs += f"\"{key}\" \"{value}\"\n"

        for brush in self.brushes:
            kvs += brush.raw()
        
        kvs += "}\n"
        return kvs


class BaseReader(ABC):
    """Base class for format readers"""
    def __init__(self, filepath: Path, outputdir: Path):
        self.missing_textures: bool
        self.entities: Sequence[BaseEntity]
        self.wadhandler = WadHandler(filepath.parent, outputdir)
