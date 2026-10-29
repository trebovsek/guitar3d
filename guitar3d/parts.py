from .mesh import box, prism, surface_ring
from .outline import ARCH, SIDE_HALF
from .palette import (
    BRIDGE, FINGERBOARD, FRET, HEADSTOCK, IVORY, NECK, ROSETTE, ROSETTE_INNER,
    SLOT, SOUNDHOLE, STRING_BASS, STRING_TREBLE, TUNER,
)

NUT_Y = 400
BRIDGE_Y = -250
SCALE_LENGTH = NUT_Y - BRIDGE_Y
FRET_COUNT = 19
TOP_Z = SIDE_HALF + ARCH
NECK_THICKNESS = 14
NECK_TOP = TOP_Z - 1
BOARD_TOP = NECK_TOP + 2
FRET_TOP = BOARD_TOP + 1.5
HEAD_THICKNESS = 12
HEAD_TILT = 0.25
NECK_TAPER = 5 / 325
STRING_NUT_X = [-25 + 10 * i for i in range(6)]
STRING_BRIDGE_X = [-30 + 12 * i for i in range(6)]
STRING_WIDTHS = [2.6, 2.2, 1.8, 1.5, 1.2, 1.0]
STRING_NUT_Z = BOARD_TOP + 3
SADDLE_Y = BRIDGE_Y + 3
SADDLE_TOP = TOP_Z + 12
SOUNDHOLE_Y = -77
HEADSTOCK_OUTLINE = [
    (-26, NUT_Y), (26, NUT_Y), (30, 430), (35, 490), (36, 525), (26, 547),
    (0, 552), (-26, 547), (-36, 525), (-35, 490), (-30, 430),
]
TUNERS = [(440, 32), (480, 35), (520, 36)]
SLOTS = [(-18, -6), (6, 18)]


def fret_y(n):
    return NUT_Y - SCALE_LENGTH * (1 - 2 ** (-n / 12))


def neck_half_width(y):
    return 26 + (NUT_Y - y) * NECK_TAPER


def neck_faces():
    end_y = fret_y(FRET_COUNT) - 8
    end_w = neck_half_width(end_y)
    plan = [(-26, NUT_Y), (26, NUT_Y), (end_w, end_y), (-end_w, end_y)]
    faces = prism(plan, NECK_TOP - NECK_THICKNESS, NECK_TOP, NECK)
    faces += prism(plan, NECK_TOP, BOARD_TOP, FINGERBOARD)
    for n in range(1, FRET_COUNT + 1):
        y = fret_y(n)
        h = neck_half_width(y)
        faces += box(-h, h, y - 0.9, y + 0.9, BOARD_TOP, FRET_TOP, FRET)
    faces += box(-27, 27, NUT_Y - 4, NUT_Y, NECK_TOP, BOARD_TOP + 3.5, IVORY)
    return faces


def _tilt(faces):
    return [
        ([(x, y, z - max(0.0, y - NUT_Y) * HEAD_TILT) for x, y, z in points], color)
        for points, color in faces
    ]


def headstock_faces():
    z0, z1 = BOARD_TOP - HEAD_THICKNESS, BOARD_TOP
    mid = (z0 + z1) / 2
    faces = prism(HEADSTOCK_OUTLINE, z0, z1, HEADSTOCK)
    for x0, x1 in SLOTS:
        faces += box(x0, x1, 438, 520, z1, z1 + 0.4, SLOT)
    for side in (-1, 1):
        for y, edge in TUNERS:
            a, b = sorted((side * (edge - 1), side * (edge + 12)))
            faces += box(a, b, y - 1.5, y + 1.5, mid - 1.5, mid + 1.5, TUNER)
            c, d = sorted((side * (edge + 12), side * (edge + 19)))
            faces += box(c, d, y - 6, y + 6, mid - 4, mid + 4, TUNER)
    return _tilt(faces)


def bridge_faces():
    faces = box(-85, 85, BRIDGE_Y - 11, BRIDGE_Y + 11, TOP_Z - 1, TOP_Z + 8, BRIDGE)
    faces += box(-36, 36, SADDLE_Y - 1.5, SADDLE_Y + 1.5, TOP_Z + 8, SADDLE_TOP, IVORY)
    return faces


def body_decal_faces():
    faces = surface_ring(0, SOUNDHOLE_Y, 54, 58, ROSETTE_INNER)
    faces += surface_ring(0, SOUNDHOLE_Y, 44, 54, ROSETTE)
    faces += surface_ring(0, SOUNDHOLE_Y, 40, 44, ROSETTE_INNER)
    faces += surface_ring(0, SOUNDHOLE_Y, 0, 40, SOUNDHOLE)
    return faces


def string_lines():
    return [
        (
            (STRING_NUT_X[i], NUT_Y, STRING_NUT_Z),
            (STRING_BRIDGE_X[i], SADDLE_Y, SADDLE_TOP),
            STRING_TREBLE if i >= 3 else STRING_BASS,
            STRING_WIDTHS[i],
        )
        for i in range(6)
    ]
