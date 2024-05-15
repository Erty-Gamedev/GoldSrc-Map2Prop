# -*- coding: utf-8 -*-
"""
Base classes for map file readers and map objects

@author: Erty
"""


from typing import List, Dict, Tuple, Sequence
from abc import ABC, abstractmethod
from pathlib import Path
from geoutil import (Polygon, Vertex, Vector3D, Texture)


class BaseFace(ABC):
    def __init__(self, points: List[Vector3D], texture: Texture, normal: Vector3D):
        self._points = points
        self._vertices: List[Vertex]
        self._polygons: List[Polygon]
        self._texture = texture
        self._normal = normal

    @property
    @abstractmethod
    def points(self) -> List[Vector3D]: pass
    @property
    @abstractmethod
    def vertices(self) -> List[Vertex]: pass
    @property
    @abstractmethod
    def polygons(self) -> List[Polygon]: pass
    @property
    @abstractmethod
    def texture(self) -> Texture: pass
    @property
    @abstractmethod
    def normal(self) -> Vector3D: pass
    def __repr__(self) -> str: return f"Face({self.texture.name})"


class BaseBrush(ABC):
    def __init__(self, faces: Sequence[BaseFace]):
        self._faces = faces
        self._all_points: List[Vector3D]
        self._all_polygons: List[Polygon]
    @property
    @abstractmethod
    def faces(self) -> Sequence[BaseFace]: pass
    @property
    @abstractmethod
    def all_points(self) -> List[Vector3D]: pass
    @property
    @abstractmethod
    def all_polygons(self) -> List[Polygon]: pass
    @property
    @abstractmethod
    def is_origin(self) -> bool: pass
    @property
    @abstractmethod
    def bounds(self) -> Tuple[Vector3D, Vector3D]: pass
    @property
    @abstractmethod
    def center(self) -> Vector3D: pass
    def __repr__(self) -> str: return f"Brush({len(self.faces)} faces)"


class BaseEntity(ABC):
    def __init__(self, classname: str, properties: Dict[str, str], brushes: Sequence[BaseBrush]):
        self._classname = classname
        self._properties = properties
        self._brushes = brushes
    @property
    @abstractmethod
    def classname(self) -> str: pass
    @property
    @abstractmethod
    def brushes(self) -> Sequence[BaseBrush]: pass
    @property
    @abstractmethod
    def properties(self) -> Dict[str, str]: pass
    def __repr__(self) -> str: return f"Entity({self.classname})"


class BaseReader(ABC):
    """Base class for format readers"""

    def __init__(self, filepath: Path, outputdir: Path):
        self.allfaces: Sequence[BaseFace]
        self.allvertices: List[Vertex]
        self.vn_map: Dict[Vector3D, List[Vector3D]]
        self.maskedtextures: List[str]
        self.missing_textures: bool
        self.entities: Sequence[BaseEntity]
