import json
import math
from pathlib import Path

from .chords import ROOT_PITCH, TYPES, voicings

SETTINGS_PATH = Path.home() / ".guitar3d" / "last_chord.json"
LAYOUT_PATH = SETTINGS_PATH.with_name("layout.json")


def _read_settings(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def load_layout(path=LAYOUT_PATH):
    data = _read_settings(path)
    layout = {}
    for key in ("window_size", "normal_size"):
        value = data.get(key)
        if _valid_pair(value, 1):
            layout[key] = tuple(value)
    for key in ("maximized", "show_help", "show_fingers", "show_hand"):
        if type(data.get(key)) is bool:
            layout[key] = data[key]
    for key in ("positions", "shown"):
        values = data.get(key)
        if isinstance(values, dict):
            layout[key] = {}
            for name in ("label", "hand", "saved"):
                value = values.get(name)
                if key == "positions" and _valid_pair(value, 0):
                    layout[key][name] = tuple(value)
                elif key == "shown" and type(value) is bool:
                    layout[key][name] = value
    view = data.get("view")
    if isinstance(view, dict):
        layout["view"] = {}
        for key in ("yaw", "pitch", "zoom", "pan_x", "pan_y"):
            value = view.get(key)
            if type(value) in (int, float) and math.isfinite(value):
                if key != "zoom" or value > 0:
                    layout["view"][key] = value
    return layout


def _valid_pair(value, minimum):
    return (isinstance(value, (list, tuple)) and len(value) == 2
            and all(type(number) is int and number >= minimum for number in value))


def save_layout(layout, path=LAYOUT_PATH):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(layout), encoding="utf-8")
        return True
    except OSError:
        return False


def _valid_chord(root, type_index, position):
    return (
        isinstance(root, str) and root in ROOT_PITCH
        and isinstance(type_index, int) and 0 <= type_index < len(TYPES)
        and isinstance(position, int) and 0 <= position < len(voicings(root + TYPES[type_index]))
    )


def load_saved_chords(path=SETTINGS_PATH):
    data = _read_settings(path)
    entries = data.get("chords", [data])
    if not isinstance(entries, list):
        entries = []
    saved = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        chord = (entry.get("root"), entry.get("type"), entry.get("position"))
        if _valid_chord(*chord):
            saved.append(chord)
    return saved


def _valid_accidentals(data):
    return {
        letter: mark for letter, mark in data.items()
        if letter + mark in ROOT_PITCH and mark in ("", "#", "b")
    }


def load_last_chord(path=SETTINGS_PATH):
    try:
        data = _read_settings(path)
        root = data["root"]
        if root is None:
            return None, 0, 0, _valid_accidentals(data.get("accidentals", {}))
        type_index, voicing = data["type"], data["position"]
        if _valid_chord(root, type_index, voicing):
            accidentals = _valid_accidentals(data.get("accidentals", {}))
            accidentals[root[0]] = root[1:]
            return root, type_index, voicing, accidentals
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    return None


def save_last_chord(root, type_index, voicing, accidentals, path=SETTINGS_PATH):
    saved = load_saved_chords(path)
    chord = (root, type_index, voicing)
    if _valid_chord(*chord) and chord not in saved:
        saved.append(chord)
    _write_settings(root, type_index, voicing, accidentals, saved, path)


def replace_saved_chord(previous, replacement, accidentals, path=SETTINGS_PATH, *, index=None):
    saved = load_saved_chords(path)
    if previous not in saved or not _valid_chord(*replacement):
        return None
    if index is None:
        index = saved.index(previous)
    if not 0 <= index < len(saved) or saved[index] != previous:
        return None
    saved[index] = replacement
    if _write_settings(*replacement, accidentals, saved, path):
        return saved
    return None


def delete_saved_chord(chord, path=SETTINGS_PATH, *, index=None):
    saved = load_saved_chords(path)
    if chord not in saved:
        return None
    if index is None:
        index = saved.index(chord)
    if not 0 <= index < len(saved) or saved[index] != chord:
        return None
    del saved[index]
    last = load_last_chord(path) or (None, 0, 0, {})
    if _write_settings(*last, saved, path):
        return saved
    return None


def clear_saved_chords(path=SETTINGS_PATH):
    return _write_settings(None, 0, 0, {}, [], path)


def _write_settings(root, type_index, voicing, accidentals, saved, path):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({
                "root": root, "type": type_index, "position": voicing,
                "accidentals": accidentals,
                "chords": [
                    {"root": saved_root, "type": saved_type, "position": saved_position}
                    for saved_root, saved_type, saved_position in saved
                ],
            }),
            encoding="utf-8",
        )
        return True
    except OSError:
        return False
