# -*- coding: utf-8 -*-
"""
Created on Thu May 18 10:38:39 2023

@author: Erty
"""


from vector3d import Vector3D
from math import sqrt, cos, sin, acos
from triangulate.triangulate import triangulate


PI = 3.141592653589793116
DEG2RAD = PI / 180.0
EPSILON = 1e-10


class PolyPoint:
    def __init__(self, v: Vector3D, t: Vector3D, n: Vector3D):
        self.v, self.t, self.n = v, t, n


class PolyFace:
    def __init__(self, polypoints: list, texture: str):
        self.polypoints = polypoints
        self.vertices = [p.v for p in self.polypoints]
        self.texture = texture


class HessianPlane:
    def __init__(self, normal: Vector3D, distance: float):
        self.normal = normal
        self.d = distance
        self.nd = normal, distance

    def distance_to_point(self, point: Vector3D) -> float:
        plane_point = self.normal * self.d
        return self.normal.dot((point - plane_point))

    def point_relation(self, point: Vector3D) -> int:
        """+1 if point is in front, -1 if behind, 0 if on plane"""
        d = self.distance_to_point(point)
        if abs(d) < EPSILON:
            return 0
        return 1 if d > 0 else 0

    def __str__(self):
        return f"{self.normal} + {self.d}"

    def __repr__(self):
        return f"Plane({self.normal} + {self.d})"


class Plane(HessianPlane):
    def __init__(self, plane_points: list, texture: dict = {}):
        plane_points = [Vector3D(*p) for p in plane_points[:3]]
        plane_points.reverse()
        super().__init__(*points_to_plane(*plane_points))
        self.plane_points = plane_points
        self.texture = texture


class InvalidSolidException(Exception):
    def __init__(self, message, vertices):
        self.message = message
        self.vertices = [(p[0], p[1], p[2]) for p in vertices]
        super().__init__(f"{self.message}\nVertices:\n{self.vertices}")


def get_triples(items: list, last_two_and_first: bool = True):
    triples = [items[i:i + 3] for i in range(len(items) - 2)]
    if last_two_and_first:
        triples.append([items[-2], items[-1], items[0]])
    return triples


def direction(angle: float) -> int:
    return 0 if angle < PI else 1


def segments_dot(a: Vector3D, b: Vector3D, c: Vector3D) -> Vector3D:
    return (a - b).dot(b - c)


def segments_cross(a: Vector3D, b: Vector3D, c: Vector3D) -> Vector3D:
    return (c - b).cross(a - b)


def clip(value, minimum, maximum):
    return min(maximum, max(minimum, value))


def vectors_angle(a: Vector3D, b: Vector3D):
    return acos(clip(a.dot(b) / a.mag * b.mag, -1, 1))


def segments_angle(a: Vector3D, b: Vector3D, c: Vector3D):
    vector_ab = [b.x - a.x, b.y - a.y, b.z - a.z]
    vector_bc = [c.x - b.x, c.y - b.y, c.z - b.z]
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


def deg2rad(degrees) -> float:
    return degrees * DEG2RAD


def rotate_2d(vector: tuple, degrees: float) -> tuple:
    x, y = vector
    th = deg2rad(degrees)
    return x * cos(th) - y * sin(th), x * sin(th) + y * cos(th)


def polygon_transpose(polygon, vector):
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


def is_point_on_plane(point: Vector3D, normal, k) -> bool:
    a, b, c = normal
    return abs(
        a * point.x + b * point.y + c * point.z + k) < EPSILON


def plane_normal(plane_points: tuple):
    return segments_cross(*plane_points).normalized


def points_to_plane(a, b, c):
    normal = segments_cross(a, b, c).normalized
    return normal, normal.dot(a)


def polygon_to_plane(polygon: list):
    return points_to_plane(*polygon[:3])


def check_planar(polygon: list) -> bool:
    if len(polygon) < 3:
        return False
    if len(polygon) == 3:
        return True

    normal, k = polygon_to_plane(polygon)

    for point in polygon[3:]:
        if not is_point_on_plane(point, normal, k):
            return False
    return True


def triangulate_face(polygon: list) -> list:
    tris = []
    try:
        for tri in triangulate(polygon):
            tris.append([Vector3D(*p) for p in tri])
    except Exception as e:
        raise InvalidSolidException(e, polygon)
    return tris


def sum_vectors(vectors: list) -> Vector3D:
    return Vector3D(*[sum(v) for v in zip(*vectors)])


def average_normals(normals: list) -> Vector3D:
    return (sum_vectors(normals) / len(normals)).normalized


def average_near_normals(normals: list, threshold: float) -> dict:
    new_normals = {}

    i, c = 0, 0
    while i < len(normals):
        c += 1
        if c > 1000:
            raise Exception('Possible infinite loop encountered')

        a = normals[i]

        near = [a]
        for b in normals:
            if b is a:
                continue
            if vectors_angle(a, b) <= threshold:
                near.append(b)
        if len(near) == 1:
            new_normals[a] = a
            i += 1
            continue

        new_normals[a] = average_normals(near)
        for n in near:
            new_normals[n] = new_normals[a]
            normals.remove(n)

        i = 0

    return new_normals


def intersection_3planes(p1: HessianPlane,
                         p2: HessianPlane,
                         p3: HessianPlane) -> Vector3D:
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


def geometric_center(vertices: list) -> Vector3D:
    center = Vector3D(0, 0, 0)

    for vertex in vertices:
        center += vertex

    return center / len(vertices)


def sort_vertices(vertices: list, normal: Vector3D) -> list:
    center = geometric_center(vertices)
    num_vertices = len(vertices)

    for i in range(num_vertices - 2):
        a = (vertices[i] - center).normalized
        p = Plane([vertices[i], center, center + normal])

        angle_smallest = -1
        smallest = -1

        for j in range(i + 1, num_vertices):
            if p.point_relation(vertices[j]) != -1:
                b = (vertices[j] - center).normalized
                angle = a.dot(b)
                if angle > angle_smallest:
                    angle_smallest = angle
                    smallest = j

        vertices[i+1], vertices[smallest] = vertices[smallest], vertices[i+1]

    sorted_normal = plane_normal(vertices[:3])
    if normal.dot(sorted_normal) < 0:
        vertices = list(reversed(vertices))

    return vertices
