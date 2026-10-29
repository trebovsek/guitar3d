import itertools
import math

from .mesh import box, prism
from .palette import CHORD_DOT
from .parts import (
    BOARD_TOP, NUT_Y, SADDLE_TOP, SADDLE_Y, STRING_BRIDGE_X, STRING_NUT_X,
    STRING_NUT_Z, fret_y,
)

TYPES = ("", "7", "m", "m7", "6", "m6", "maj7", "sus4", "+", "dim")

# Six characters per chord, low E string first: x is muted, 0 is open, digits are frets.
FINGERINGS = {
    "A": ("x02220", "x02020", "x02210", "x02010", "x02222",
          "x02212", "x02120", "x02230", "x03221", "x01212"),
    "B": ("x24442", "x21202", "x24432", "x24232", "x24444",
          "x20102", "x24342", "x24452", "x21003", "x2313x"),
    "C": ("x32010", "x32310", "x35543", "x35343", "x32210",
          "x31213", "x32000", "x33011", "x32110", "x3424x"),
    "D": ("xx0232", "xx0212", "xx0231", "xx0211", "xx0202",
          "xx0201", "xx0222", "xx0233", "xx0332", "xx0101"),
    "E": ("022100", "020100", "022000", "022030", "022120",
          "022020", "021100", "022200", "032110", "xx2323"),
    "F": ("133211", "131211", "133111", "131111", "xx3231",
          "xx3131", "xx3210", "113311", "xx3221", "xx3434"),
    "G": ("320033", "320001", "355333", "353333", "320000",
          "3x2330", "320002", "330013", "321003", "3x232x"),
}
# Sharps and flats: an open shape moved up the neck as a barre chord.
BARRE_FORMS = {"C#": ("A", 4), "D#": ("D", 1), "F#": ("E", 2), "G#": ("E", 4), "A#": ("A", 1)}
FLAT_NAMES = {"C#": "Db", "D#": "Eb", "F#": "Gb", "G#": "Ab", "A#": "Bb"}


def _shift(shape, frets):
    return "".join(c if c == "x" else str(int(c) + frets) for c in shape)


for _sharp, (_form, _frets) in BARRE_FORMS.items():
    _shapes = tuple(_shift(s, _frets) for s in FINGERINGS[_form])
    FINGERINGS[_sharp] = _shapes
    FINGERINGS[FLAT_NAMES[_sharp]] = _shapes

OPEN_PITCH = (4, 9, 2, 7, 11, 4)
ROOT_PITCH = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5,
    "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
}
INTERVALS = {
    "": {0, 4, 7}, "7": {0, 4, 7, 10}, "m": {0, 3, 7}, "m7": {0, 3, 7, 10},
    "6": {0, 4, 7, 9}, "m6": {0, 3, 7, 9}, "maj7": {0, 4, 7, 11},
    "sus4": {0, 5, 7}, "+": {0, 4, 8}, "dim": {0, 3, 6, 9},
}
MAX_FRET = 12
MAX_SPAN = 3
OPEN_WINDOW = 1
MAX_FINGERS = 4
MIN_STRINGS = 4
DOT_RADIUS = 4.6
DOT_POSITION = 0.65
DOT_SIDES = 16


def _parse(shape):
    return tuple(None if c == "x" else int(c) for c in shape)


def _barre(frets, level):
    at_level = [i for i, f in enumerate(frets) if f == level]
    if len(at_level) > 1 and all(frets[i] != 0 for i in range(min(at_level), max(at_level) + 1)):
        return at_level
    return []


def _fingers(frets):
    count = sum(1 for f in frets if f)
    barre = _barre(frets, min(f for f in frets if f))
    return count - len(barre) + (1 if barre else 0)


def fingering(frets):
    fretted = sorted((f, i) for i, f in enumerate(frets) if f)
    if not fretted:
        return None
    levels = [None] if len(fretted) <= MAX_FINGERS else sorted({f for f, _ in fretted})
    for share in (False, True):
        for level in levels:
            barre = set(_barre(frets, level)) if level else set()
            fingers, number, barre_finger = {}, 0, None
            previous = None
            for fret, i in fretted:
                if i in barre:
                    if barre_finger is None:
                        number += 1
                        barre_finger = number
                    fingers[i] = barre_finger
                elif share and previous and previous[0] == fret and previous[1] + 1 == i:
                    fingers[i] = fingers[previous[1]]
                else:
                    number += 1
                    fingers[i] = number
                previous = (fret, i)
            if number <= MAX_FINGERS:
                return tuple(fingers.get(i) for i in range(len(frets)))
    return None


def _playable(frets, required, root_pitch):
    sounding = [i for i, f in enumerate(frets) if f is not None]
    if len(sounding) < MIN_STRINGS or sounding[-1] - sounding[0] + 1 != len(sounding):
        return False
    if not any(frets[i] for i in sounding):
        return False
    pitches = [(OPEN_PITCH[i] + frets[i]) % 12 for i in sounding]
    if pitches[0] != root_pitch or not required <= set(pitches):
        return False
    return _fingers(frets) <= MAX_FINGERS


def _generate(root, suffix):
    root_pitch = ROOT_PITCH[root]
    intervals = INTERVALS[suffix]
    tones = {(root_pitch + t) % 12 for t in intervals}
    required = tones
    if len(intervals) == 4 and 7 in intervals:
        required = tones - {(root_pitch + 7) % 12}
    found = set()
    for low in range(1, MAX_FRET - MAX_SPAN + 1):
        options = []
        for pitch in OPEN_PITCH:
            choices = [None]
            if low <= OPEN_WINDOW and pitch in tones:
                choices.append(0)
            choices += [f for f in range(low, low + MAX_SPAN + 1) if (pitch + f) % 12 in tones]
            options.append(choices)
        for frets in itertools.product(*options):
            if _playable(frets, required, root_pitch):
                found.add(frets)
    return found


def _position(frets):
    return (min(f for f in frets if f), tuple(-1 if f is None else f for f in frets))


def _without_subsets(shapes):
    def covers(big, small):
        return big != small and all(s is None or s == b for s, b in zip(small, big))
    return {s for s in shapes if not any(covers(other, s) for other in shapes)}


_VOICINGS = {}


def voicings(name):
    if name not in _VOICINGS:
        root = name[:2] if len(name) > 1 and name[1] in "#b" else name[:1]
        suffix = name[len(root):]
        standard = _parse(FINGERINGS[root][TYPES.index(suffix)])
        found = _without_subsets(_generate(root, suffix) | {standard})
        _VOICINGS[name] = [standard] + sorted(found - {standard}, key=_position)
    return _VOICINGS[name]


def _dot_position(string, fret):
    i = 6 - string
    y_near, y_far = fret_y(fret - 1), fret_y(fret)
    y = y_near + (y_far - y_near) * DOT_POSITION
    s = (NUT_Y - y) / (NUT_Y - SADDLE_Y)
    x = STRING_NUT_X[i] + (STRING_BRIDGE_X[i] - STRING_NUT_X[i]) * s
    z = STRING_NUT_Z + (SADDLE_TOP - STRING_NUT_Z) * s
    return x, y, z


def _dot_faces(string, fret):
    x, y, z = _dot_position(string, fret)
    outline = [
        (x + DOT_RADIUS * math.cos(2 * math.pi * k / DOT_SIDES),
         y + DOT_RADIUS * math.sin(2 * math.pi * k / DOT_SIDES))
        for k in range(DOT_SIDES)
    ]
    faces = prism(outline, z - 1, z + 1, CHORD_DOT)
    faces += box(x - 1, x + 1, y - 1, y + 1, BOARD_TOP, z - 1, CHORD_DOT)
    return faces


def chord_faces(name, index=0):
    faces = []
    for i, fret in enumerate(voicings(name)[index]):
        if fret:
            faces += _dot_faces(6 - i, fret)
    return faces


def finger_marks(name, index=0):
    frets = voicings(name)[index]
    fingers = fingering(frets)
    if not fingers:
        return []
    marks = []
    for i, (fret, finger) in enumerate(zip(frets, fingers)):
        if fret and finger:
            x, y, z = _dot_position(6 - i, fret)
            marks.append((x, y, z + 1, finger))
    return marks
