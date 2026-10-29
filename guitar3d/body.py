import math

from .outline import OUTLINE, BODY_CENTER, SIDE_HALF, ARCH, BACK_ARCH, arch
from .palette import BODY, BINDING

EDGE = 3
INNER_SCALE = 0.7
FILLET_STEPS = 2
INTERIOR_STEPS = 5


def _inset(p, d):
    rx, ry = p[0] - BODY_CENTER[0], p[1] - BODY_CENTER[1]
    length = math.hypot(rx, ry)
    return (p[0] - rx / length * d, p[1] - ry / length * d)


def _rings(sign, amp):
    rings = []
    for k in range(FILLET_STEPS + 1):
        phi = (math.pi / 2) * k / FILLET_STEPS
        ring = []
        for p in OUTLINE:
            x, y = _inset(p, EDGE * (1 - math.cos(phi)))
            h = SIDE_HALF + amp * arch(p[0]) - EDGE + EDGE * math.sin(phi)
            ring.append((x, y, sign * h))
        rings.append(ring)
    for m in range(1, INTERIOR_STEPS + 1):
        u = m / INTERIOR_STEPS
        ring = []
        for p in OUTLINE:
            rx, ry = p[0] - BODY_CENTER[0], p[1] - BODY_CENTER[1]
            rho = math.hypot(rx, ry)
            x, y = _inset(p, EDGE + (rho * (1 - INNER_SCALE) - EDGE) * u)
            ring.append((x, y, sign * (SIDE_HALF + amp * arch(x))))
        rings.append(ring)
    return rings


def body_faces():
    faces = []
    count = len(OUTLINE)
    for sign, amp in ((1, ARCH), (-1, BACK_ARCH)):
        rings = _rings(sign, amp)
        wood = BODY if sign > 0 else BINDING
        for k in range(len(rings) - 1):
            color = BINDING if k < FILLET_STEPS else wood
            for j in range(count):
                n = (j + 1) % count
                faces.append(([rings[k][j], rings[k][n], rings[k + 1][n], rings[k + 1][j]], color))
        apex = (BODY_CENTER[0], BODY_CENTER[1], sign * (SIDE_HALF + amp))
        inner = rings[-1]
        for j in range(count):
            n = (j + 1) % count
            faces.append(([apex, inner[j], inner[n]], wood))
    top = _rings(1, ARCH)[0]
    back = _rings(-1, BACK_ARCH)[0]
    for j in range(count):
        n = (j + 1) % count
        faces.append(([top[j], top[n], back[n], back[j]], BINDING))
    return faces
