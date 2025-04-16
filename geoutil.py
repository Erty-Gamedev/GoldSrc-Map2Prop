"""
Geometric functions and classes
"""

from typing import List, Tuple, Union, Literal, Dict, TypeAlias, Final, Any
from dataclasses import dataclass
from vector3d import Vector3D, EPSILON
from math import sqrt, cos, sin, acos


PI: Final[float] = 3.141592653589793116
DEG2RAD: Final[float] = PI / 180.0
RAD2DEG: Final[float] = 180.0 / PI
Bounds: TypeAlias = Tuple[Vector3D, Vector3D]


@dataclass
class Vertex:
    v: Vector3D
    t: Vector3D
    n: Vector3D
    flipped: bool = False


@dataclass
class Polygon:
    vertices: List[Vertex]
    texture: str
    flipped: bool = False

    @property
    def normal(self) -> Vector3D:
        return plane_normal([v.v for v in self.vertices])


@dataclass
class ImageInfo:
    width: int
    height: int


@dataclass
class Texture:
    name: str
    rightaxis: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    shiftx: float = 0.0
    downaxis: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    shifty: float = 0.0
    angle: float = 0.0
    scalex: float = 1.0
    scaley: float = 1.0
    width: int = 16
    height: int = 16


class HessianPlane:
    def __init__(self, normal: Vector3D, distance: float):
        self.normal = normal
        self.d = distance
        self.nd = normal, distance

    def distance_to_point(self, point: Vector3D) -> float:
        plane_point = self.normal * self.d
        return self.normal.dot((point - plane_point))

    def point_relation(self, point: Vector3D) -> Literal[-1, 0, 1]:
        """+1 if point is in front, -1 if behind, 0 if on plane"""
        d = self.distance_to_point(point)
        if abs(d) < EPSILON:
            return 0
        return 1 if d > 0 else -1

    def __str__(self):
        return f"{self.normal} + {self.d}"

    def __repr__(self):
        return f"Plane({self.normal} + {self.d})"


class Plane(HessianPlane):
    def __init__(
            self,
            plane_points: Union[List[Tuple[float, float, float]], List[Vector3D]],
            texture: Texture):
        plane_vectors: List[Vector3D] = [Vector3D(*p) for p in plane_points[:3]]
        plane_vectors.reverse()
        super().__init__(*points_to_plane(*plane_vectors))
        self.plane_points = plane_vectors
        self.texture: Texture = texture


def get_triples(items: list, last_two_and_first: bool = True):
    triples = [items[i:i + 3] for i in range(len(items) - 2)]
    if last_two_and_first:
        triples.append([items[-2], items[-1], items[0]])
    return triples


def direction(angle: float) -> int:
    return 0 if angle < PI else 1


def segments_dot(a: Vector3D, b: Vector3D, c: Vector3D) -> Vector3D:
    """Finds the dot product between the segments AB and BC"""
    return (a - b).dot(b - c)


def segments_cross(a: Vector3D, b: Vector3D, c: Vector3D) -> Vector3D:
    """Finds the cross product between the segments AB and BC"""
    return (c - b).cross(a - b)


def clip(value, minimum, maximum):
    """Limit the value between the minimum and maximum"""
    return min(maximum, max(minimum, value))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def vectors_angle(a: Vector3D, b: Vector3D) -> float:
    """Returns the angle between two vectors"""
    a, b = a.normalized, b.normalized
    return acos(clip(a.dot(b) / a.mag * b.mag, -1, 1))


def segments_angle(a: Vector3D, b: Vector3D, c: Vector3D) -> float:
    """Returns the angle between the segments ab and bc in radians"""
    vector_ab = Vector3D(b.x - a.x, b.y - a.y, b.z - a.z)
    vector_bc = Vector3D(c.x - b.x, c.y - b.y, c.z - b.z)
    return vectors_angle(vector_ab, vector_bc)


def plane_rotation(normal, d):
    a, b, c = normal

    squaresum = sum(a ** 2, b ** 2, c ** 2)
    rootsquaresum = sqrt(squaresum)
    costh = c / rootsquaresum
    sinth = sqrt(
        (a ** 2 + b ** 2) / squaresum
    )
    k = 1 - costh
    u1 = b / rootsquaresum
    u2 = a / rootsquaresum
    u1u2k = u1 * u2 * k

    return [
        [costh + u1 ** 2 * k, u1u2k, u2 * sinth],
        [u1u2k, costh + u2 ** 2 * k, -u1 * sinth],
        [-u2 * sinth, u1 * sinth, costh]
    ]


def deg2rad(degrees: float) -> float:
    """Convert degrees to radians"""
    return (degrees * DEG2RAD) % (2 * PI)

def rad2deg(radians: float) -> float:
    """Converts radians to degrees"""
    return (radians * RAD2DEG) % 360.0


def rotate_2d(vector: tuple, degrees: float) -> tuple:
    """Rotate the 2D vector by the given angle in degrees"""
    x, y = vector
    th = deg2rad(degrees)
    return x * cos(th) - y * sin(th), x * sin(th) + y * cos(th)


def polygon_transpose(polygon: list, vector: Vector3D) -> list:
    """Transpose all points in the polygon by the given vector"""
    new_poly = []
    for point in polygon:
        new_poly.append(Vector3D(
            point.x + vector[0],
            point.y + vector[1],
            point.z + vector[2]
        ))
    return new_poly


def flatten_plane(polygon: list):
    normal, k = polygon_to_plane(polygon)
    transposed = polygon_transpose(polygon, normal * k)

    new_poly = []
    rotation = plane_rotation(normal, k)
    for point in transposed:
        new_point = Vector3D(
            point.dot(rotation[0]),
            point.dot(rotation[1]),
            point.dot(rotation[2]),
        )
        new_poly.append(new_point)
    return new_poly


def plane_normal(plane_points: Union[tuple, list]) -> Vector3D:
    """Returns the normalized normal vector of the plane"""
    return segments_cross(*plane_points).normalized


def points_to_plane(a, b, c) -> tuple:
    """Return the plane's normal vector and distance by three points"""
    normal = segments_cross(a, b, c).normalized
    return normal, normal.dot(a)


def polygon_to_plane(polygon: list) -> tuple:
    return points_to_plane(*polygon[:3])


def sum_vectors(vectors: List[Vector3D]) -> Vector3D:
    return Vector3D(*[sum(v) for v in zip(*vectors)])


def average_vectors(vectors: List[Vector3D]) -> Vector3D:
    return (sum_vectors(vectors) / len(vectors)).normalized


def average_near_normals(vertices: List[Vertex], threshold: float) -> None:
    remaining = vertices

    c, limit = 0, len(vertices) + 1000
    while remaining:
        c += 1
        if c > limit:
            raise ValueError('Possible infinite loop detected')
        
        a = remaining[0]
        near = [a]
        for b in remaining:
            if b is a:
                continue
            if vectors_angle(a.n, b.n) <= threshold:
                near.append(b)
        
        average_normal = average_vectors(list({v.n: v.n for v in near}.values()))
        for point in near:
            point.n = average_normal
            remaining.remove(point)
    return None


def smooth_near_normals(points: Dict[Vector3D, List[Vertex]], threshold: float) -> None:
    for vertices in points.values():
        average_near_normals(vertices, threshold)


def smooth_all_normals(points: Dict[Vector3D, List[Vertex]]) -> None:
    for vertices in points.values():
        normals = {v.n: v.n for v in vertices}
        average_normal = average_vectors(list(normals))
        for vertex in vertices:
            vertex.n = average_normal


def intersection_3planes(p1: HessianPlane,
                         p2: HessianPlane,
                         p3: HessianPlane) -> Union[Vector3D, Literal[False]]:
    """Returns the intersection of the three planes,
    or false if there is no interesection
    """
    n1, d1 = p1.nd
    n2, d2 = p2.nd
    n3, d3 = p3.nd

    denominator = n1.dot(n2.cross(n3))
    if abs(denominator) < EPSILON:
        return False

    return -(
        -d1 * n2.cross(n3)
        - d2 * n3.cross(n1)
        - d3 * n1.cross(n2)
    ) / denominator


def geometric_center(vectors: List[Vector3D]) -> Vector3D:
    """Returns the geometric center of the given vertices"""
    return sum_vectors(vectors) / len(vectors)


def bounds_from_points(points: List[Vector3D]) -> Bounds:
    bmin = Vector3D(*points[0])
    bmax = Vector3D(*points[0])

    for point in points:
        if point.x < bmin.x: bmin.x = point.x
        if point.y < bmin.y: bmin.y = point.y
        if point.z < bmin.z: bmin.z = point.z
        
        if point.x > bmax.x: bmax.x = point.x
        if point.y > bmax.y: bmax.y = point.y
        if point.z > bmax.z: bmax.z = point.z
    
    return bmin, bmax


def unique_vectors(vectors: List[Vector3D]) -> List[Vector3D]:
    unique: List[Vector3D] = []
    for vector in vectors:
        is_unique = True
        for u in unique:
            if vector == u:
                is_unique = False
                break
        if is_unique:
            unique.append(vector)

    return unique


def sort_vertices(vertices: List[Vector3D], normal: Vector3D) -> List[Vector3D]:
    """Returns a sorted list of vertices from an unsorted list"""
    num_vertices = len(vertices)
    center = geometric_center(vertices)
    sorted = [vertices[0]]
    rest = vertices[1:]

    while len(sorted) < num_vertices:
        a = sorted[-1]
        p = HessianPlane(*points_to_plane(*[a, center, center + normal]))

        smallest_angle = -1
        smallest = -1
        for n in range(0, len(rest)):
            b = rest[n]
            dot_normal = (a-center).normalized.dot((b-center).normalized)
            
            if p.point_relation(b) > 0 and dot_normal > smallest_angle:
                smallest_angle = dot_normal
                smallest = n

        sorted.append(rest[smallest])
        rest.pop(smallest)

    sorted_normal = plane_normal(sorted[:3])
    if normal.dot(sorted_normal) < 0:
        sorted = list(reversed(sorted))

    return sorted


def faces_from_planes(planes: List[Plane]) -> List[Dict[str, Any]]:
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

    return faces


def is_vertex_outside_planes(vertex, planes: List[Plane]) -> bool:
    for plane in planes:
        if plane.point_relation(vertex) > 0:
            return True
    return False


def flip_faces(polygons: List[Polygon]) -> List[Polygon]:
    flipped = []
    for polygon in polygons:
        vertices = [Vertex(vertex.v, vertex.t, -vertex.n, True) for vertex in reversed(polygon.vertices)]
        flipped.append(Polygon(vertices, polygon.texture, True))
    return flipped


def point_in_bounds(point: Vector3D, bounds: Bounds) -> bool:
    bmin, bmax = bounds
    
    return point.x > bmin.x and point.x < bmax.x\
        and point.y > bmin.y and point.y < bmax.y\
        and point.z > bmin.z and point.z < bmax.z
