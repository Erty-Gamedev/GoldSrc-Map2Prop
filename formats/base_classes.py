"""
Base classes for map file readers and map objects
"""


from typing import List, Dict, Tuple, Sequence
from abc import ABC, abstractmethod
from pathlib import Path
from geoutil import (Polygon, Vertex, Vector3D, Texture,
                     bounds_from_points, geometric_center)
from formats.wad_handler import WadHandler


class BaseFace(ABC):
    def __init__(self, points: List[Vector3D], texture: Texture, normal: Vector3D):
        self._points = points
        self._vertices: List[Vertex]
        self._polygons: List[Polygon]
        self._texture = texture
        self._normal = normal

    @property
    def points(self) -> List[Vector3D]: return self._points
    @property
    def vertices(self) -> List[Vertex]: return self._vertices
    @property
    def polygons(self) -> List[Polygon]: return self._polygons
    @property
    def texture(self) -> Texture: return self._texture
    # @property
    # @abstractmethod
    # def normal(self) -> Vector3D: pass
    def __repr__(self) -> str: return f"Face({self.texture.name})"


class BaseBrush(ABC):
    def __init__(self, faces: Sequence[BaseFace]):
        self._faces = faces
        self._all_points: List[Vector3D] = []
        self._all_polygons: List[Polygon] = []
        self._maskedtextures: List[str] = []
        for face in faces:
            self._all_points.extend(face.points)
            if face.texture.name.lower() in WadHandler.TOOL_TEXTURES:
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
    def bounds(self) -> Tuple[Vector3D, Vector3D]:
        return bounds_from_points(self.all_points)
    @property
    def center(self) -> Vector3D:
        return geometric_center(self.all_points)
    def __repr__(self) -> str: return f"Brush({len(self.faces)} faces)"


class BaseEntity(ABC):
    def __init__(self, classname: str, properties: Dict[str, str], brushes: Sequence[BaseBrush]):
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


class BaseReader(ABC):
    """Base class for format readers"""
    def __init__(self, filepath: Path, outputdir: Path):
        self.missing_textures: bool
        self.entities: Sequence[BaseEntity]
