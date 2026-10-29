OUTLINE_RIGHT = [
    (0, 75), (50, 73), (100, 64), (130, 42), (141, 12), (137, -30), (124, -75),
    (117, -118), (121, -160), (143, -205), (165, -250), (172, -292), (164, -336),
    (135, -374), (82, -394), (0, -400),
]
BODY_CENTER = (0, -160)
SIDE_HALF = 38
ARCH = 3
BACK_ARCH = 3
ARCH_HALF = 180


def _catmull_rom_loop(points, steps):
    count = len(points)
    out = []
    for i in range(count):
        p0, p1 = points[i - 1], points[i]
        p2, p3 = points[(i + 1) % count], points[(i + 2) % count]
        for k in range(steps):
            t = k / steps
            out.append(tuple(
                0.5 * (2 * p1[c] + (p2[c] - p0[c]) * t
                       + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t * t
                       + (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * t ** 3)
                for c in (0, 1)))
    return out


OUTLINE = _catmull_rom_loop(
    OUTLINE_RIGHT + [(-x, y) for x, y in reversed(OUTLINE_RIGHT[1:-1])], 4)


def arch(x):
    return max(0.0, 1 - (x / ARCH_HALF) ** 2)


def inside(x, y):
    hit = False
    count = len(OUTLINE)
    for i in range(count):
        x1, y1 = OUTLINE[i]
        x2, y2 = OUTLINE[(i + 1) % count]
        if (y1 > y) != (y2 > y) and x < x1 + (x2 - x1) * (y - y1) / (y2 - y1):
            hit = not hit
    return hit


def top_z(x, y):
    return SIDE_HALF + ARCH * arch(x) if inside(x, y) else 0.0
