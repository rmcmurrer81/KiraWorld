"""List main-component boundary loops and bounds for V23 diagnosis."""

from __future__ import annotations

import sys
from pathlib import Path

import bpy


source = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
bpy.ops.wm.open_mainfile(filepath=str(source))
body = next(
    obj
    for obj in bpy.context.scene.objects
    if obj.type == "MESH"
    and obj.name.startswith("BIOLOGICAL_ROBERT_STATIC_LIKENESS_")
)
mesh = body.data
adjacency = [set() for _ in mesh.vertices]
edge_use = {}
for polygon in mesh.polygons:
    ids = list(polygon.vertices)
    for index, first in enumerate(ids):
        second = ids[(index + 1) % len(ids)]
        key = tuple(sorted((first, second)))
        edge_use[key] = edge_use.get(key, 0) + 1
        adjacency[first].add(second)
        adjacency[second].add(first)

remaining = set(range(len(mesh.vertices)))
components = []
component_of = {}
while remaining:
    seed = remaining.pop()
    members = {seed}
    stack = [seed]
    while stack:
        current = stack.pop()
        for neighbor in adjacency[current]:
            if neighbor in remaining:
                remaining.remove(neighbor)
                members.add(neighbor)
                stack.append(neighbor)
    identifier = len(components)
    components.append(members)
    for member in members:
        component_of[member] = identifier
largest = max(range(len(components)), key=lambda index: len(components[index]))

boundary = [
    edge
    for edge, count in edge_use.items()
    if count == 1
    and component_of.get(edge[0]) == largest
    and component_of.get(edge[1]) == largest
]
boundary_adjacency = {}
for first, second in boundary:
    boundary_adjacency.setdefault(first, set()).add(second)
    boundary_adjacency.setdefault(second, set()).add(first)
unseen = set(boundary_adjacency)
loops = []
while unseen:
    seed = unseen.pop()
    members = {seed}
    stack = [seed]
    while stack:
        current = stack.pop()
        for neighbor in boundary_adjacency[current]:
            if neighbor in unseen:
                unseen.remove(neighbor)
                members.add(neighbor)
                stack.append(neighbor)
    loops.append(members)

for number, members in enumerate(sorted(loops, key=len, reverse=True)):
    points = [mesh.vertices[index].co for index in members]
    print(
        number,
        "vertices",
        len(members),
        "degree_set",
        sorted({len(boundary_adjacency[index]) for index in members}),
        "bounds",
        (
            min(point.x for point in points),
            min(point.y for point in points),
            min(point.z for point in points),
        ),
        (
            max(point.x for point in points),
            max(point.y for point in points),
            max(point.z for point in points),
        ),
    )
