from vector3d import Vector3D


IS_EAGER: bool = False


class InvalidSolidException(Exception):
    def __init__(self, message: str, vertices: list[Vector3D]):
        self.message = message
        self.vertices = [(p[0], p[1], p[2]) for p in vertices]
        super().__init__(f"{self.message}\nVertices:\n{self.vertices}")


def point_inside_triangle(point: Vector3D, triangle: tuple[Vector3D, Vector3D, Vector3D]) -> bool:
    # Move point to origin
    a = triangle[0] - point
    b = triangle[1] - point
    c = triangle[2] - point

    # Cross products to get normal vectors
    u, v, w = b.cross(c), c.cross(a), a.cross(b)

    # Point is inside triangle if the normal vectors are pointing in the same direction
    if u.dot(v) < 0 or u.dot(w) < 0:
        return False
    
    return True

def any_point_inside_triangle(points: list[Vector3D], triangle: tuple[Vector3D, Vector3D, Vector3D]) -> bool:
    for point in points:
        if point in triangle:
            continue
        if point_inside_triangle(point, triangle):
            return True
    return False

def find_ears(polygon: list[Vector3D], normal: Vector3D) -> list[Vector3D]:
    max_index = len(polygon)

    ears: list[Vector3D] = []
    for i, point in enumerate(polygon):
        p_prev = polygon[(i - 1) % max_index]
        p_next = polygon[(i + 1) % max_index]

        cross = (p_prev - point).normalized.cross((p_next - point).normalized)
        normal_dot = -normal.dot(cross)

        if (normal_dot > 0):
            if any_point_inside_triangle(polygon, (p_prev, point, p_next)):
                continue
            ears.append(point)

    return ears

def find_optimal_ear(polygon: list[Vector3D], full_polygon: list[Vector3D], normal: Vector3D) -> int:
    """Find the ear that is closest to a 60° angle.
    Should discourage squished triangles."""

    max_index = len(polygon)

    optimal_index: int = -1
    current_optimal: float = 0
    optimal_dot = .5
    for i, point in enumerate(polygon):
        p_prev = polygon[(i - 1) % max_index]
        p_next = polygon[(i + 1) % max_index]

        cross = (p_prev - point).normalized.cross((p_next - point).normalized)
        normal_dot = -normal.dot(cross)

        if normal_dot > 0:
            if any_point_inside_triangle(full_polygon, (p_prev, point, p_next)):
                continue

            if IS_EAGER: return i  # If eager, just return first found ear index

            delta = abs(optimal_dot - normal_dot)
            if optimal_index == -1 or delta < current_optimal:
                optimal_index = i
                current_optimal = delta
                continue

    return optimal_index


def ear_clip(_polygon: list[Vector3D], normal: Vector3D) -> list[tuple[Vector3D, Vector3D, Vector3D]]:
    """Triangulates a simple (either convex or concave) polygon without holes
    using ear clipping algorithm."""

    num_vertices = len(_polygon)
    if num_vertices == 3:
        return [(_polygon[0], _polygon[1], _polygon[2])]
    if num_vertices < 3:
        raise InvalidSolidException("Polygon with less than 3 sides", _polygon)
    
    polygon = _polygon.copy()  # Make a copy we can modify (consecutively remove ears)

    triangles: list[tuple[Vector3D, Vector3D, Vector3D]] = []
    while len(polygon) > 3:
        max_index = len(polygon)
        i = find_optimal_ear(polygon, _polygon, normal)
        triangles.append((
            polygon[(i - 1) % max_index],
            polygon[i],
            polygon[(i + 1) % max_index],
        ))
        polygon.pop(i)  # Remove current ear
    triangles.append((polygon[0], polygon[1], polygon[2]))

    return triangles
