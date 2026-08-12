"""Verify Blender's polygon tessellator preserves two explicit inner holes."""

import math

from mathutils import Vector
from mathutils.geometry import tessellate_polygon


outer = [
    Vector((math.cos(2 * math.pi * index / 32), math.sin(2 * math.pi * index / 32)))
    for index in range(32)
]
hole_a = [
    Vector(
        (
            -0.25 + 0.14 * math.cos(-2 * math.pi * index / 12),
            0.10 + 0.14 * math.sin(-2 * math.pi * index / 12),
        )
    )
    for index in range(12)
]
hole_b = [
    Vector(
        (
            0.25 + 0.18 * math.cos(-2 * math.pi * index / 16),
            -0.10 + 0.18 * math.sin(-2 * math.pi * index / 16),
        )
    )
    for index in range(16)
]
triangles = tessellate_polygon([outer, hole_a, hole_b])
points = outer + hole_a + hole_b


def triangle_area(triangle):
    if isinstance(triangle[0], int):
        first, second, third = (points[index] for index in triangle)
    else:
        first, second, third = triangle
    return abs(
        (second.x - first.x) * (third.y - first.y)
        - (second.y - first.y) * (third.x - first.x)
    ) * 0.5


area = sum(triangle_area(triangle) for triangle in triangles)
expected = (
    32 * math.sin(2 * math.pi / 32) * 0.5
    - 12 * (0.14**2) * math.sin(2 * math.pi / 12) * 0.5
    - 16 * (0.18**2) * math.sin(2 * math.pi / 16) * 0.5
)
print("triangles", len(triangles))
print("area", area)
print("expected", expected)
print("difference", abs(area - expected))
