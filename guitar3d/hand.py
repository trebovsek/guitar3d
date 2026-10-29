import math

import pygame

SCALE = 4
SIZE = (190, 206)
SKIN_TOP = (249, 219, 194)
SKIN_BOTTOM = (221, 170, 138)
OUTLINE = (118, 78, 58)
CREASE = (205, 156, 126)
NAIL = (254, 238, 232)
NAIL_OUTLINE = (208, 152, 132)
BADGE = (255, 106, 43)
THUMB_BADGE = (95, 100, 120)
FINGER_RADIUS = 11.5
THUMB_RADIUS = 13
OUTLINE_WIDTH = 2.5
FADE_ROWS = 22
PALM = (30, 100, 145, 172)
WRIST = ((38, 150), (137, 150), (116, SIZE[1] + 20), (60, SIZE[1] + 20))
# Back of the left hand, fingers up: little finger on the left, thumb on the right.
# (finger, base, lean in degrees from vertical, length)
FINGERS = (
    (4, (42, 112), -16, 62),
    (3, (66, 106), -5, 82),
    (2, (92, 104), 2, 86),
    (1, (118, 108), 14, 76),
)
THUMB = ((128, 165), (170, 120))


def _tip(base, lean, length):
    angle = math.radians(lean)
    return base[0] + length * math.sin(angle), base[1] - length * math.cos(angle)


def _segments():
    segments = [(str(finger), base, _tip(base, lean, length), FINGER_RADIUS, BADGE)
                for finger, base, lean, length in FINGERS]
    segments.append(("T", THUMB[0], THUMB[1], THUMB_RADIUS, THUMB_BADGE))
    return segments


def _along(base, tip, distance):
    length = math.dist(base, tip)
    return (base[0] + (tip[0] - base[0]) * distance / length,
            base[1] + (tip[1] - base[1]) * distance / length)


def _scaled(*points):
    return [(x * SCALE, y * SCALE) for x, y in points]


def _capsule(surface, color, a, b, radius):
    (ax, ay), (bx, by) = _scaled(a, b)
    radius *= SCALE
    length = math.hypot(bx - ax, by - ay)
    nx, ny = -(by - ay) / length * radius, (bx - ax) / length * radius
    pygame.draw.polygon(surface, color, [(ax + nx, ay + ny), (bx + nx, by + ny),
                                         (bx - nx, by - ny), (ax - nx, ay - ny)])
    pygame.draw.circle(surface, color, (ax, ay), radius)
    pygame.draw.circle(surface, color, (bx, by), radius)


def _line(surface, color, a, b, width):
    _capsule(surface, color, a, b, width / 2)


def _silhouette(surface, color):
    left, top, right, bottom = PALM
    pygame.draw.rect(surface, color,
                     pygame.Rect(left * SCALE, top * SCALE, (right - left) * SCALE, (bottom - top) * SCALE),
                     border_radius=28 * SCALE)
    pygame.draw.polygon(surface, color, _scaled(*WRIST))
    for _, base, tip, radius, _ in _segments():
        _capsule(surface, color, base, tip, radius)


def _outline(big):
    mask = pygame.Surface(big.get_size(), pygame.SRCALPHA)
    _silhouette(mask, OUTLINE)
    reach = OUTLINE_WIDTH * SCALE
    for k in range(24):
        angle = 2 * math.pi * k / 24
        big.blit(mask, (round(reach * math.cos(angle)), round(reach * math.sin(angle))))


def _skin(big):
    width, height = big.get_size()
    fill = pygame.Surface((width, height), pygame.SRCALPHA)
    for y in range(height):
        t = y / (height - 1)
        pygame.draw.line(fill, tuple(round(a + (b - a) * t) for a, b in zip(SKIN_TOP, SKIN_BOTTOM)),
                         (0, y), (width, y))
    mask = pygame.Surface((width, height), pygame.SRCALPHA)
    _silhouette(mask, (255, 255, 255))
    fill.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    big.blit(fill, (0, 0))


def _cross(surface, base, tip, distance, half, width):
    center = _along(base, tip, distance)
    ux, uy = (tip[0] - base[0]) / math.dist(base, tip), (tip[1] - base[1]) / math.dist(base, tip)
    _line(surface, CREASE, (center[0] - uy * half, center[1] + ux * half),
          (center[0] + uy * half, center[1] - ux * half), width)


def _details(big):
    for _, base, tip, radius, _ in _segments()[:4]:
        length = math.dist(base, tip)
        _cross(big, base, tip, 4, 6, 1.6)
        _cross(big, base, tip, 0.42 * length, 6.5, 1.8)
        end = (88 + (base[0] - 88) * 0.35, 168)
        _line(big, CREASE, (base[0], base[1] + 12), end, 1.4)
    for _, base, tip, radius, _ in _segments():
        length = math.dist(base, tip)
        a, b = _along(base, tip, length - 6), _along(base, tip, length + 3)
        _capsule(big, NAIL_OUTLINE, a, b, radius * 0.56 + 0.8)
        _capsule(big, NAIL, a, b, radius * 0.56)


def _badges(big):
    font = pygame.font.Font(None, 15 * SCALE)
    for text, base, tip, _, color in _segments():
        x, y = _scaled(_along(base, tip, math.dist(base, tip) - 24))[0]
        pygame.draw.circle(big, (255, 255, 255), (x, y), 10.5 * SCALE)
        pygame.draw.circle(big, color, (x, y), 9 * SCALE)
        label = font.render(text, True, (255, 255, 255))
        big.blit(label, (x - label.get_width() / 2, y - label.get_height() / 2))


def hand_surface():
    big = pygame.Surface((SIZE[0] * SCALE, SIZE[1] * SCALE), pygame.SRCALPHA)
    _outline(big)
    _skin(big)
    _details(big)
    _badges(big)
    small = pygame.transform.smoothscale(big, SIZE)
    fade = pygame.Surface(SIZE, pygame.SRCALPHA)
    fade.fill((255, 255, 255, 255))
    for row in range(FADE_ROWS):
        alpha = round(255 * (row + 1) / FADE_ROWS)
        pygame.draw.line(fade, (255, 255, 255, 255 - alpha), (0, SIZE[1] - FADE_ROWS + row),
                         (SIZE[0], SIZE[1] - FADE_ROWS + row))
    small.blit(fade, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return small
