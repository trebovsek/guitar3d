import math

from .chords import _dot_position, fingering, voicings
from .palette import HAND_NAIL, HAND_SKIN, HAND_SLEEVE
from .parts import NECK_THICKNESS, NECK_TOP

SIDES = 14
BALL_RINGS = 7
NECK_BOTTOM = NECK_TOP - NECK_THICKNESS
BODY_TOP_Y = 75
# finger: (offset across the palm, offset along it, bone lengths, radii at base/PIP/DIP/tip)
FINGER_SPECS = {
    1: (30, 0, (44, 25, 21), (9.2, 8.3, 7.7, 7.3)),
    2: (10, 2, (48, 28, 22), (9.4, 8.5, 7.8, 7.4)),
    3: (-10, 0, (45, 26, 21), (9.0, 8.1, 7.5, 7.1)),
    4: (-29, -5, (36, 20, 19), (8.0, 7.3, 6.7, 6.3)),
}
TIP_DIRECTION = (-0.3, 0.0, -1.0)
IDLE_LIFT = 16
IDLE_SPACING = 26
SAME_FRET_GAP = 9
KNUCKLE_X_RANGE = range(28, 112, 4)
KNUCKLE_X_PREFERRED = 62
ROW_SLIDE = (50, 30)
HEIGHT_DROPS = range(0, 41, 10)
HAND_YAWS = range(0, -36, -7)
THUMB_BASE_OFFSET = (55, 34, 8)
THUMB_JOINT = (58, 20)
THUMB_TIP_X = 14
THUMB_BONES = (32, 27)
THUMB_RADII = (11, 9.5, 8.5, 7.8)
# (distance back from the knuckles, half width across, half thickness, color)
ARM = (
    (-8, 33, 10, HAND_SKIN), (0, 40, 14, HAND_SKIN), (22, 41, 15, HAND_SKIN),
    (52, 38, 16, HAND_SKIN), (82, 29, 18, HAND_SKIN), (112, 31, 22, HAND_SKIN),
    (160, 36, 26, HAND_SKIN), (192, 37, 27, HAND_SKIN),
    (194, 45, 35, HAND_SLEEVE), (270, 47, 37, HAND_SLEEVE),
)


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _mul(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _length(a):
    return math.sqrt(_dot(a, a))


def _unit(a):
    return _mul(a, 1 / _length(a))


def _perpendicular(vector, axis):
    return _unit(_sub(vector, _mul(axis, _dot(vector, axis))))


def _basis(axis):
    axis = _unit(axis)
    helper = (1.0, 0.0, 0.0) if abs(axis[0]) < 0.9 else (0.0, 1.0, 0.0)
    u = _unit(_cross(axis, helper))
    return u, _cross(axis, u)


def _ring(center, u, v, ru, rv):
    return [
        _add(center, _add(_mul(u, ru * math.cos(2 * math.pi * k / SIDES)),
                          _mul(v, rv * math.sin(2 * math.pi * k / SIDES))))
        for k in range(SIDES)
    ]


def _skin_between(rings, color):
    faces = []
    for a, b in zip(rings, rings[1:]):
        for k in range(SIDES):
            j = (k + 1) % SIDES
            faces.append(([a[k], a[j], b[j], b[k]], color))
    return faces


def _tube(a, b, ra, rb, color):
    u, v = _basis(_sub(b, a))
    return _skin_between([_ring(a, u, v, ra, ra), _ring(b, u, v, rb, rb)], color)


def _ball(center, radius, color):
    rings = []
    for i in range(BALL_RINGS + 1):
        phi = math.pi * i / BALL_RINGS
        rings.append([
            (center[0] + radius * math.sin(phi) * math.cos(2 * math.pi * k / SIDES),
             center[1] + radius * math.sin(phi) * math.sin(2 * math.pi * k / SIDES),
             center[2] + radius * math.cos(phi))
            for k in range(SIDES)
        ])
    return _skin_between(rings, color)


def _two_bones(base, end, first, second, pole):
    reach = _length(_sub(end, base))
    reach = min(max(reach, abs(first - second) + 0.01), first + second - 0.01)
    axis = _unit(_sub(end, base))
    along = (first ** 2 - second ** 2 + reach ** 2) / (2 * reach)
    lift = math.sqrt(max(first ** 2 - along ** 2, 0.0))
    return _add(_add(base, _mul(axis, along)), _mul(_perpendicular(pole, axis), lift))


def _limb(points, radii, color):
    faces = []
    for (a, b), (ra, rb) in zip(zip(points, points[1:]), zip(radii, radii[1:])):
        faces += _tube(a, b, ra, rb, color)
    for point, radius in zip(points, radii):
        faces += _ball(point, radius, color)
    return faces


def _arm(knuckles, along, across, thickness):
    rings, colors = [], []
    for back, half_width, half_thick, color in ARM:
        center = _sub(knuckles, _mul(along, back))
        rings.append(_ring(center, across, thickness, half_width, half_thick))
        colors.append(color)
    faces = []
    for k in range(len(rings) - 1):
        faces += _skin_between(rings[k:k + 2], colors[k + 1])
    faces.append((rings[0], HAND_SKIN))
    faces.append((rings[-1], HAND_SLEEVE))
    return faces


def is_major(name):
    root = name[:2] if len(name) > 1 and name[1] in "#b" else name[:1]
    return len(name) == len(root)


def has_hand(name, index=0):
    return is_major(name) and 0 <= index < len(voicings(name))


def _reaches(name, index):
    frets = voicings(name)[index]
    strings = {}
    for i, (fret, finger) in enumerate(zip(frets, fingering(frets))):
        if fret:
            strings.setdefault(finger, []).append(i)
    reaches = {}
    by_fret = {}
    for finger, found in strings.items():
        by_fret.setdefault(frets[found[0]], []).append(finger)
    for finger, found in strings.items():
        lowest = min(found)
        x, y, z = _dot_position(6 - lowest, frets[lowest])
        mates = sorted(by_fret[frets[lowest]])
        y += (len(mates) - 1) / 2 * SAME_FRET_GAP - mates.index(finger) * SAME_FRET_GAP
        reaches[finger] = ((x, y, z + FINGER_SPECS[finger][3][3] * 0.85), len(found) > 1)
    last = max(reaches)
    lx, ly, lz = reaches[last][0]
    for finger in range(last + 1, 5):
        steps = finger - last
        reaches[finger] = ((lx, ly - IDLE_SPACING * steps, lz + IDLE_LIFT + 4 * steps), False)
    return reaches


def _frame(angle, yaw=0.0):
    along = (-math.cos(angle), 0.0, math.sin(angle))
    across = (0.0, 1.0, 0.0)
    cos, sin = math.cos(yaw), math.sin(yaw)
    along = (along[0] * cos - along[1] * sin, along[0] * sin + along[1] * cos, along[2])
    across = (across[0] * cos - across[1] * sin, across[0] * sin + across[1] * cos, across[2])
    return along, across, _cross(along, across)


def _base(knuckles, frame, finger):
    along, across, _ = frame
    spread, forward = FINGER_SPECS[finger][:2]
    return _add(_add(knuckles, _mul(across, spread)), _mul(along, forward))


def _reach_cost(base, finger, tip, straight):
    _, _, bones, _ = FINGER_SPECS[finger]
    if straight:
        total = sum(bones)
        dist = _length(_sub(tip, base))
        low, high, ideal = 0.9 * total, 1.04 * total, total
    else:
        end = _sub(tip, _mul(_unit(TIP_DIRECTION), bones[2]))
        dist = _length(_sub(end, base))
        low, high = abs(bones[0] - bones[1]) + 12, bones[0] + bones[1] - 4
        ideal = 0.75 * (bones[0] + bones[1])
    return 10 * max(low - dist, 0) + 10 * max(dist - high, 0) + 0.1 * abs(dist - ideal)


def _setup(row, barre, yaw):
    flat = min(max((row - 20) / 130, 0.0), 1.0)
    height = 92 - 14 * flat
    if barre and row > 100:
        height -= 16
    return _frame(math.radians(3 + 37 * flat), math.radians(yaw)), height


def _fit_knuckles(first_row, barre, reaches):
    def cost(candidate):
        x, row, drop, yaw = candidate
        frame, height = _setup(row, barre, yaw)
        knuckles = (x, row, height - drop)
        total = (0.05 * abs(x - KNUCKLE_X_PREFERRED) + 0.08 * abs(row - first_row)
                 + 0.1 * drop + 0.3 * abs(yaw))
        for finger, (tip, straight) in reaches.items():
            total += _reach_cost(_base(knuckles, frame, finger), finger, tip, straight)
        return total
    rows = range(first_row - ROW_SLIDE[0], first_row + ROW_SLIDE[1] + 1, 6)
    candidates = ((x, row, drop, yaw) for x in KNUCKLE_X_RANGE for row in rows
                  for drop in HEIGHT_DROPS for yaw in HAND_YAWS)
    x, row, drop, yaw = min(candidates, key=cost)
    frame, height = _setup(row, barre, yaw)
    return (x, row, height - drop), frame


def _finger_points(base, tip, finger, straight, dorsal):
    bones = FINGER_SPECS[finger][2]
    if straight:
        total = sum(bones)
        first = _add(base, _mul(_sub(tip, base), bones[0] / total))
        second = _add(base, _mul(_sub(tip, base), (bones[0] + bones[1]) / total))
        return [base, first, second, tip], _unit(_sub(tip, base))
    direction = _unit(TIP_DIRECTION)
    last = _sub(tip, _mul(direction, bones[2]))
    return [base, _two_bones(base, last, bones[0], bones[1], dorsal), last, tip], direction


def pose(name, index=0):
    reaches = _reaches(name, index)
    straight = any(flag for _, flag in reaches.values())
    first_row = round(reaches[1][0][1] - (36 if reaches[1][1] else 44))
    knuckles, frame = _fit_knuckles(first_row, straight, reaches)
    row = knuckles[1]
    dorsal = _mul(frame[2], -1)
    fingers = {}
    for finger, (tip, flag) in reaches.items():
        points, direction = _finger_points(_base(knuckles, frame, finger), tip, finger, flag, dorsal)
        fingers[finger] = (points, FINGER_SPECS[finger][3], direction)

    root = _add(_add(_sub(knuckles, _mul(frame[0], THUMB_BASE_OFFSET[0])),
                     _mul(frame[1], THUMB_BASE_OFFSET[1])), _mul(frame[2], THUMB_BASE_OFFSET[2]))
    joint = (THUMB_JOINT[0], max(row + 22, BODY_TOP_Y + 25), THUMB_JOINT[1])
    tip = (THUMB_TIP_X, max(row + 20, BODY_TOP_Y + 22), NECK_BOTTOM - THUMB_RADII[3] + 1)
    middle = _two_bones(joint, tip, THUMB_BONES[0], THUMB_BONES[1], (0.0, 0.0, -1.0))
    return {"fingers": fingers, "thumb": ([root, joint, middle, tip], THUMB_RADII),
            "arm": (knuckles, *frame), "dorsal": dorsal}


def hand_faces(name, index=0):
    if not has_hand(name, index):
        return []
    plan = pose(name, index)
    faces = _arm(*plan["arm"])
    for points, radii, direction in plan["fingers"].values():
        faces += _limb(points, radii, HAND_SKIN)
        tip = points[3]
        dorsal = _perpendicular(plan["dorsal"], direction)
        back = _add(_sub(tip, _mul(direction, 13)), _mul(dorsal, radii[3] * 0.62))
        front = _add(_sub(tip, _mul(direction, 2)), _mul(dorsal, radii[3] * 0.52))
        faces += _tube(back, front, 3.9, 3.6, HAND_NAIL)
    faces += _limb(*plan["thumb"], HAND_SKIN)
    return faces
