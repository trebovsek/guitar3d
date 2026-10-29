import math

from .outline import top_z

SURFACE_LIFT = 0.8
SEGMENTS = 28


def box(x0, x1, y0, y1, z0, z1, color):
    corners = {
        (0, 0, 0): (x0, y0, z0), (1, 0, 0): (x1, y0, z0),
        (1, 1, 0): (x1, y1, z0), (0, 1, 0): (x0, y1, z0),
        (0, 0, 1): (x0, y0, z1), (1, 0, 1): (x1, y0, z1),
        (1, 1, 1): (x1, y1, z1), (0, 1, 1): (x0, y1, z1),
    }
    c = corners
    sides = [
        [c[0, 0, 0], c[1, 0, 0], c[1, 1, 0], c[0, 1, 0]],
        [c[0, 0, 1], c[0, 1, 1], c[1, 1, 1], c[1, 0, 1]],
        [c[0, 0, 0], c[0, 0, 1], c[1, 0, 1], c[1, 0, 0]],
        [c[1, 0, 0], c[1, 0, 1], c[1, 1, 1], c[1, 1, 0]],
        [c[1, 1, 0], c[1, 1, 1], c[0, 1, 1], c[0, 1, 0]],
        [c[0, 1, 0], c[0, 1, 1], c[0, 0, 1], c[0, 0, 0]],
    ]
    return [(points, color) for points in sides]


def prism(outline, z0, z1, color):
    count = len(outline)
    top = [(x, y, z1) for x, y in outline]
    bottom = [(x, y, z0) for x, y in outline]
    faces = [(top, color), (bottom, color)]
    for i in range(count):
        j = (i + 1) % count
        faces.append(([top[i], top[j], bottom[j], bottom[i]], color))
    return faces


def surface_ring(cx, cy, r_in, r_out, color):
    def ring(r):
        points = []
        for j in range(SEGMENTS):
            a = 2 * math.pi * j / SEGMENTS
            x, y = cx + r * math.cos(a), cy + r * math.sin(a)
            points.append((x, y, top_z(x, y) + SURFACE_LIFT))
        return points

    outer = ring(r_out)
    if r_in <= 0:
        center = (cx, cy, top_z(cx, cy) + SURFACE_LIFT)
        return [([center, outer[j], outer[(j + 1) % SEGMENTS]], color) for j in range(SEGMENTS)]
    inner = ring(r_in)
    return [
        ([inner[j], inner[(j + 1) % SEGMENTS], outer[(j + 1) % SEGMENTS], outer[j]], color)
        for j in range(SEGMENTS)
    ]
