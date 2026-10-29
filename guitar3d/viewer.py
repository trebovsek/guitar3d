import math

import pygame
from OpenGL import GL, GLU
from pygame._sdl2.video import Window

from .chords import DOT_RADIUS, TYPES, chord_faces, finger_marks, voicings
from .hand import hand_surface
from .hand3d import hand_faces
from .model import build_model
from .palette import BG_BOTTOM, BG_TOP
from .settings import (
    clear_saved_chords, delete_saved_chord, load_last_chord, load_layout, load_saved_chords,
    replace_saved_chord, save_last_chord, save_layout,
)

WIDTH, HEIGHT = 900, 900
BASE_FOV = 34.0
CAMERA_DISTANCE = 2000
LIGHT = (0.352, 0.554, 0.755)
AMBIENT = 0.35
MIN_ZOOM = 0.3
MAX_ZOOM = 6.0
ZOOM_STEP = 1.15
START_VIEW = (-0.5, -0.9, 1.0)
CAPTION = "Classical Guitar 3D"
PANEL_MARGIN = 16
HELP_HINT = "F1 - help"
HELP_SECTIONS = (
    ("Choose a chord", (
        ("A B C D E F G", "Choose a root. Repeat its letter for the next position."),
        ("Shift + C D F G A", "Sharp root: C#, D#, F#, G#, A#. Accidentals are remembered."),
        ("Ctrl + D E G A B", "Flat root: Db, Eb, Gb, Ab, Bb. Accidentals are remembered."),
        ("N, then a letter", "Use a natural root instead of its remembered sharp or flat."),
        ("F3", "Make the current root natural and return to position 1."),
        ("Example: B, then 4", "Bm7. Chord dots mark fretted strings, not open or muted strings."),
    )),
    ("Chord types", (
        ("1", "Major"), ("2", "7 - dominant seventh"),
        ("3", "m - minor"), ("4", "m7 - minor seventh"),
        ("5", "6 - sixth"), ("6", "m6 - minor sixth"),
        ("7", "maj7 - major seventh"), ("8", "sus4 - suspended fourth"),
        ("9", "+ - augmented"), ("0", "dim - diminished"),
    )),
    ("Saved chords", (
        ("Enter", "Save the current draft or confirm an edited row."),
        ("Click a saved row", "Edit that row. Chord changes remain unsaved until Enter."),
        ("Up / Down", "Browse saved chords without editing. Finish any draft first."),
        ("Wheel over the list", "Scroll the saved-chord list."),
        ("Backspace", "Delete the selected row, or clear a new unsaved chord."),
        ("Esc", "Cancel a selected-row edit. Does not close the app."),
    )),
    ("Guitar and panels", (
        ("Left-drag", "Rotate the guitar."),
        ("Right-drag / Shift+left-drag", "Pan the guitar."),
        ("Mouse wheel", "Zoom the guitar."),
        ("Drag a panel heading", "Move that panel."),
        ("R", "Reset guitar rotation, pan and zoom."),
        ("F2", "Show or hide the chord label."),
        ("F4", "Show or hide the finger guide."),
        ("F5", "Show or hide finger numbers on the dots."),
        ("F6", "Show or hide the 3D hand for major chords."),
        ("F7", "Show or hide saved chords."),
        ("F12", "Reset window size, panel layout and guitar view. Delete all saved chords and drafts."),
    )),
    ("This help", (
        ("Wheel / Up / Down", "Scroll help."),
        ("Page Up / Page Down", "Scroll one page."),
        ("Home / End", "Jump to the beginning or end."),
        ("F1 / Esc", "Close help."),
    )),
)
ROOT_KEYS = {getattr(pygame, f"K_{n.lower()}"): n for n in "ABCDEFG"}
SHARPABLE = "CDFGA"
FLATTABLE = "DEGAB"
TYPE_KEYS = {
    getattr(pygame, f"K_{d}"): i
    for i, d in enumerate("1234567890")
}


def root_name(key, mods, accidentals, natural):
    letter = ROOT_KEYS[key]
    if mods & pygame.KMOD_SHIFT:
        mark = "#" if letter in SHARPABLE else None
    elif mods & pygame.KMOD_CTRL:
        mark = "b" if letter in FLATTABLE else None
    elif natural:
        mark = ""
    else:
        mark = accidentals.get(letter, "")
    if mark is None:
        return None
    accidentals[letter] = mark
    return letter + mark


def caption(chord, voicing=0):
    if not chord:
        return f"{CAPTION}  ({HELP_HINT})"
    return f"{CAPTION} - {chord}  (position {voicing + 1}/{len(voicings(chord))})"


def window_size():
    width, height = pygame.display.get_window_size()
    return max(1, width), max(1, height)


class Overlay:
    def __init__(self, surface):
        self.size = surface.get_size()
        self.texture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.texture)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, *self.size, 0,
                        GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, pygame.image.tostring(surface, "RGBA"))

    def draw(self, x0, y0, width=None, height=None):
        width = width or self.size[0]
        height = height or self.size[1]
        window_width, window_height = window_size()
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GL.glOrtho(0, window_width, window_height, 0, -1, 1)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        GL.glDisable(GL.GL_LIGHTING)
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glEnable(GL.GL_TEXTURE_2D)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.texture)
        GL.glTexEnvi(GL.GL_TEXTURE_ENV, GL.GL_TEXTURE_ENV_MODE, GL.GL_MODULATE)
        GL.glColor4f(1, 1, 1, 1)
        GL.glBegin(GL.GL_QUADS)
        for u, v, x, y in ((0, 0, x0, y0), (1, 0, x0 + width, y0),
                           (1, 1, x0 + width, y0 + height), (0, 1, x0, y0 + height)):
            GL.glTexCoord2f(u, v)
            GL.glVertex2f(x, y)
        GL.glEnd()
        GL.glDisable(GL.GL_TEXTURE_2D)
        GL.glDisable(GL.GL_BLEND)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_LIGHTING)


def text_panel(rows, padding, gap, background):
    width = max(r.get_width() for r in rows) + 2 * padding
    height = sum(max(r.get_height(), 12) + gap for r in rows) + 2 * padding - gap
    panel = pygame.Surface((width, height), pygame.SRCALPHA)
    panel.fill(background)
    y = padding
    for row in rows:
        panel.blit(row, (padding, y))
        y += max(row.get_height(), 12) + gap
    return panel


class HelpPanel:
    HEADER = 76
    FOOTER = 34

    def __init__(self):
        self.font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 34)
        self.section_font = pygame.font.Font(None, 26)
        self.small_font = pygame.font.Font(None, 21)
        self.offset = 0
        self.drag_offset = None
        self._content = None
        self._overlay = None
        self._key = None
        self._layout()

    def _wrap(self, text, width):
        lines = []
        line = ""
        for word in text.split():
            if line and self.font.size(line + " " + word)[0] > width:
                lines.append(line)
                line = ""
            while self.font.size(word)[0] > width and len(word) > 1:
                split = len(word) - 1
                while split > 1 and self.font.size(word[:split])[0] > width:
                    split -= 1
                lines.append(word[:split])
                word = word[split:]
            line = (line + " " + word).strip()
        if line:
            lines.append(line)
        return lines

    def _build_content(self, width):
        self.column = max(1, min(230, int(width * 0.38)))
        rows = []
        height = 0
        for title, entries in HELP_SECTIONS:
            rows.append((height, 36, title, None))
            height += 36
            for shortcut, description in entries:
                keys = self._wrap(shortcut, max(1, self.column - 20))
                actions = self._wrap(description, max(1, width - self.column - 20))
                row_height = max(len(keys), len(actions)) * self.font.get_linesize() + 16
                rows.append((height, row_height, keys, actions))
                height += row_height
            height += 12
        content = pygame.Surface((width, height), pygame.SRCALPHA)
        for index, (top, row_height, keys, actions) in enumerate(rows):
            if actions is None:
                content.blit(self.section_font.render(keys, True, (255, 190, 120)), (8, top + 8))
                continue
            color = (28, 31, 39, 255) if index % 2 else (23, 26, 33, 255)
            pygame.draw.rect(content, color, (0, top, width, row_height))
            pygame.draw.line(content, (47, 50, 59), (self.column, top), (self.column, top + row_height))
            for lines, left, text_color in ((keys, 8, (247, 215, 174)),
                                            (actions, self.column + 10, (230, 232, 236))):
                for line_number, text in enumerate(lines):
                    content.blit(self.font.render(text, True, text_color),
                                 (left, top + 8 + line_number * self.font.get_linesize()))
        return content

    def _layout(self):
        width, height = window_size()
        panel_width = max(1, min(760, width - 2 * PANEL_MARGIN))
        content_width = max(1, panel_width - 48)
        if self._content is None or self._content.get_width() != content_width:
            self._content = self._build_content(content_width)
            self.drag_offset = None
        panel_height = max(1, min(height - 2 * PANEL_MARGIN,
                                  self._content.get_height() + self.HEADER + self.FOOTER))
        self.rect = pygame.Rect((width - panel_width) // 2, (height - panel_height) // 2,
                                panel_width, panel_height)
        self.size = self.rect.size
        self.body_height = max(1, panel_height - self.HEADER - self.FOOTER)
        self.max_scroll = max(0, self._content.get_height() - self.body_height)
        self.offset = min(max(0, self.offset), self.max_scroll)
        self.track = pygame.Rect(self.rect.right - 24, self.rect.top + self.HEADER, 10, self.body_height)
        thumb_height = min(self.body_height, max(24, self.body_height ** 2 // self._content.get_height()))
        travel = self.body_height - thumb_height
        thumb_top = self.track.top + (round(travel * self.offset / self.max_scroll) if self.max_scroll else 0)
        self.thumb = pygame.Rect(self.track.left, thumb_top, self.track.width, thumb_height)
        self.close_rect = pygame.Rect(self.rect.right - 42, self.rect.top + 12, 28, 28)

    def scroll(self, amount):
        self.offset = min(max(0, self.offset + amount), self.max_scroll)

    def handle_event(self, event):
        self._layout()
        if event.type == pygame.MOUSEWHEEL:
            self.scroll(-event.y * 48)
        elif event.type == pygame.KEYDOWN:
            amounts = {pygame.K_UP: -36, pygame.K_DOWN: 36,
                       pygame.K_PAGEUP: -self.body_height, pygame.K_PAGEDOWN: self.body_height,
                       pygame.K_HOME: -self.max_scroll, pygame.K_END: self.max_scroll}
            self.scroll(amounts.get(event.key, 0))
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.close_rect.collidepoint(event.pos):
                self.drag_offset = None
                return True
            if self.max_scroll and self.thumb.collidepoint(event.pos):
                self.drag_offset = event.pos[1] - self.thumb.top
            elif self.max_scroll and self.track.collidepoint(event.pos):
                self.scroll(self.body_height if event.pos[1] > self.thumb.bottom else -self.body_height)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.drag_offset = None
        elif event.type == pygame.MOUSEMOTION and self.drag_offset is not None:
            travel = self.track.height - self.thumb.height
            if travel:
                fraction = (event.pos[1] - self.track.top - self.drag_offset) / travel
                self.offset = min(max(0, round(fraction * self.max_scroll)), self.max_scroll)
        self._layout()
        return False

    def draw(self):
        self._layout()
        key = (self.size, self.offset)
        if key != self._key:
            surface = pygame.Surface(self.size, pygame.SRCALPHA)
            surface.fill((16, 18, 24, 248))
            surface.blit(self.title_font.render("Help", True, (255, 255, 255)), (24, 16))
            for text, left in (("KEY / INPUT", 24), ("ACTION", 26 + self.column)):
                surface.blit(self.small_font.render(text, True, (160, 168, 181)), (left, 53))
            surface.blit(self._content, (16, self.HEADER),
                         (0, self.offset, self._content.get_width(), self.body_height))
            if self.max_scroll:
                pygame.draw.rect(surface, (40, 44, 54), self.track.move(-self.rect.x, -self.rect.y), border_radius=4)
                pygame.draw.rect(surface, (157, 165, 181), self.thumb.move(-self.rect.x, -self.rect.y), border_radius=4)
            close = self.close_rect.move(-self.rect.x, -self.rect.y).inflate(-12, -12)
            pygame.draw.line(surface, (215, 220, 229), close.topleft, close.bottomright, 2)
            pygame.draw.line(surface, (215, 220, 229), close.topright, close.bottomleft, 2)
            surface.blit(self.small_font.render("F1 / Esc   Close", True, (160, 168, 181)), (24, self.size[1] - 25))
            if self.max_scroll:
                progress = f"{round(100 * self.offset / self.max_scroll)}%"
                label = self.small_font.render(progress, True, (160, 168, 181))
                surface.blit(label, (self.size[0] - 24 - label.get_width(), self.size[1] - 25))
            if self._overlay is not None:
                GL.glDeleteTextures([self._overlay.texture])
            self._overlay = Overlay(surface)
            self._key = key
        self._overlay.draw(self.rect.x, self.rect.y)


def help_overlay():
    return HelpPanel()


def hand_overlay():
    title = pygame.font.Font(None, 30).render("Which finger?", True, (255, 255, 255))
    legend_font = pygame.font.Font(None, 22)
    legend = [legend_font.render(text, True, (240, 240, 240))
              for text in ("1 index     2 middle", "3 ring     4 little", "T thumb")]
    hand = hand_surface()
    width = max(hand.get_width(), *(row.get_width() for row in legend))
    centered = pygame.Surface((width, hand.get_height()), pygame.SRCALPHA)
    centered.blit(hand, ((width - hand.get_width()) // 2, 0))
    return Overlay(text_panel([title, centered, *legend], 14, 6, (16, 18, 24, 200)))


class ChordLabels:
    def __init__(self):
        self.name_font = pygame.font.Font(None, 64)
        self.small_font = pygame.font.Font(None, 26)
        self.mono_font = pygame.font.SysFont("consolas,couriernew,monospace", 22)
        self._cache = {}

    def get(self, chord, voicing):
        if (chord, voicing) not in self._cache:
            self._cache[chord, voicing] = self._build(chord, voicing)
        return self._cache[chord, voicing]

    def _build(self, chord, voicing):
        shape = voicings(chord)[voicing] if chord else (None,) * 6
        strings = "".join(f"{n:^3}" for n in "EADGBe")
        frets = "".join(f"{'-' if not chord else 'x' if fret is None else fret:^3}" for fret in shape)
        position = f"position {voicing + 1}/{len(voicings(chord))}" if chord else "No chord selected"
        rows = [
            self.name_font.render(chord or "Chord", True, (255, 255, 255)),
            self.small_font.render(position, True, (170, 170, 170)),
            self.mono_font.render(strings, True, (170, 170, 170)),
            self.mono_font.render(frets, True, (255, 190, 120)),
        ]
        return Overlay(text_panel(rows, 14, 4, (16, 18, 24, 200)))


class SavedChords:
    WIDTH = 250
    ROW_TOP = 48
    ROW_HEIGHT = 30
    VISIBLE_ROWS = 8
    SIZE = (WIDTH, ROW_TOP + ROW_HEIGHT * VISIBLE_ROWS + 36)

    def __init__(self, entries):
        self.entries = list(entries)
        self.offset = 0
        self.selected = None
        self.browsed = None
        self.draft = None
        self.save_failed = False
        self.title_font = pygame.font.Font(None, 30)
        self.font = pygame.font.Font(None, 26)
        self.small_font = pygame.font.Font(None, 22)
        self._key = None
        self._overlay = None

    def select(self, index):
        if index < len(self.entries):
            self.selected = index
            self.browsed = index
            self.draft = self.entries[index]
        self.save_failed = False

    def browse(self, direction, current=None):
        if not self.entries or self.draft is not None:
            return None
        index = self.browsed
        if index is None and current in self.entries:
            index = self.entries.index(current)
        if index is None:
            index = 0 if direction > 0 else len(self.entries) - 1
        else:
            index = min(max(0, index + direction), len(self.entries) - 1)
        self.browsed = index
        self.offset = min(self.offset, index)
        self.offset = max(self.offset, index - self.VISIBLE_ROWS + 1)
        self.scroll(0)
        return self.entries[index]

    def preview(self, root, type_index, position):
        self.draft = (root, type_index, position)
        self.save_failed = False
        if self.selected is None:
            self.browsed = None
            self.offset = max(0, len(self.entries) + 1 - self.VISIBLE_ROWS)

    def display_entries(self):
        rows = list(self.entries)
        if self.draft is not None:
            if self.selected is None:
                rows.append(self.draft)
            else:
                rows[self.selected] = self.draft
        return rows

    def confirm(self, accidentals):
        updated = replace_saved_chord(self.entries[self.selected], self.draft, accidentals,
                                      index=self.selected)
        return self._finish(updated)

    def delete_selected(self):
        updated = delete_saved_chord(self.entries[self.selected], index=self.selected)
        return self._finish(updated)

    def reset(self):
        return self._finish([] if clear_saved_chords() else None)

    def _finish(self, updated):
        self.save_failed = updated is None
        if self.save_failed:
            return False
        self.entries = updated
        self.selected = None
        self.browsed = None
        self.draft = None
        self.scroll(0)
        return True

    def cancel(self):
        original = self.entries[self.selected]
        self.browsed = self.selected
        self.selected = None
        self.draft = None
        self.save_failed = False
        return original

    def remember(self, root, type_index, position):
        entry = (root, type_index, position)
        if entry not in self.entries:
            self.entries.append(entry)
            self.offset = max(0, len(self.entries) - self.VISIBLE_ROWS)
        self.browsed = self.entries.index(entry)
        self.draft = None
        self.scroll(0)

    def scroll(self, amount):
        self.offset = min(max(0, self.offset + amount), max(0, len(self.display_entries()) - self.VISIBLE_ROWS))

    def index_at(self, pos):
        if not 0 <= pos[0] < self.WIDTH:
            return None
        row = (pos[1] - self.ROW_TOP) // self.ROW_HEIGHT
        index = self.offset + row
        if 0 <= row < self.VISIBLE_ROWS and index < len(self.display_entries()):
            return index
        return None

    def entry_at(self, pos):
        index = self.index_at(pos)
        return self.display_entries()[index] if index is not None else None

    def get(self, chord, position):
        key = (tuple(self.entries), self.offset, chord, position, self.selected, self.browsed,
               self.draft, self.save_failed)
        if key != self._key:
            surface = pygame.Surface(self.SIZE, pygame.SRCALPHA)
            surface.fill((16, 18, 24, 200))
            surface.blit(self.title_font.render("Saved chords", True, (255, 255, 255)), (14, 14))
            rows = self.display_entries()
            visible = rows[self.offset:self.offset + self.VISIBLE_ROWS]
            for row, entry in enumerate(visible):
                draft_index = self.selected if self.selected is not None else len(self.entries)
                selected = self.draft is not None and self.offset + row == draft_index
                root, type_index, saved_position = entry
                name = root + TYPES[type_index]
                top = self.ROW_TOP + row * self.ROW_HEIGHT
                active = selected or (
                    self.draft is None and (name, saved_position) == (chord, position)
                    and (self.browsed is None or self.offset + row == self.browsed)
                )
                if active:
                    pygame.draw.rect(surface, (70, 57, 44, 235), (8, top, self.WIDTH - 16, self.ROW_HEIGHT))
                if selected:
                    pygame.draw.rect(surface, (255, 190, 120), (8, top, self.WIDTH - 16, self.ROW_HEIGHT), 1)
                color = (255, 190, 120) if active else (240, 240, 240)
                surface.blit(self.font.render(name, True, color), (14, top + 5))
                label = self.small_font.render(f"position {saved_position + 1}", True, (170, 170, 170))
                surface.blit(label, (self.WIDTH - 14 - label.get_width(), top + 6))
            if not rows:
                surface.blit(self.small_font.render("No saved chords", True, (170, 170, 170)), (14, self.ROW_TOP + 5))
            else:
                count = f"{self.offset + 1}-{self.offset + len(visible)} / {len(rows)}"
                surface.blit(self.small_font.render(count, True, (170, 170, 170)), (14, self.SIZE[1] - 26))
                if self.draft is not None or self.save_failed:
                    status = "Editing" if self.selected is not None else "Unsaved"
                    if self.save_failed:
                        status = "Save failed"
                    label = self.small_font.render(status, True, (255, 190, 120))
                    surface.blit(label, (self.WIDTH - 14 - label.get_width(), self.SIZE[1] - 26))
            if self._overlay is not None:
                GL.glDeleteTextures([self._overlay.texture])
            self._overlay = Overlay(surface)
            self._key = key
        return self._overlay


class FingerNumbers:
    MIN_SIZE = 16
    MAX_SIZE = 40

    def __init__(self):
        font = pygame.font.Font(None, 44)
        self.digits = {}
        for finger in range(1, 5):
            glyph = font.render(str(finger), True, (255, 255, 255))
            outline = font.render(str(finger), True, (20, 10, 5))
            surface = pygame.Surface((glyph.get_width() + 6, glyph.get_height() + 6), pygame.SRCALPHA)
            for dx in (0, 3, 6):
                for dy in (0, 3, 6):
                    surface.blit(outline, (dx, dy))
            surface.blit(glyph, (3, 3))
            self.digits[finger] = Overlay(surface)

    @staticmethod
    def _faces_camera(modelview, point):
        eye = [sum(modelview[c][r] * (point[c] if c < 3 else 1) for c in range(4)) for r in range(3)]
        normal = [modelview[2][r] for r in range(3)]
        return sum(n * -e for n, e in zip(normal, eye)) > 0

    def draw(self, marks):
        if not marks:
            return
        window_height = window_size()[1]
        modelview = GL.glGetDoublev(GL.GL_MODELVIEW_MATRIX)
        projection = GL.glGetDoublev(GL.GL_PROJECTION_MATRIX)
        viewport = GL.glGetIntegerv(GL.GL_VIEWPORT)
        placed = []
        for x, y, z, finger in marks:
            if not self._faces_camera(modelview, (x, y, z)):
                continue
            wx, wy, _ = GLU.gluProject(x, y, z, modelview, projection, viewport)
            ex, ey, _ = GLU.gluProject(x + DOT_RADIUS, y, z, modelview, projection, viewport)
            size = min(max(2.2 * math.hypot(ex - wx, ey - wy), self.MIN_SIZE), self.MAX_SIZE)
            placed.append((self.digits[finger], wx, window_height - wy, size))
        for overlay, sx, sy, size in placed:
            width = size * overlay.size[0] / overlay.size[1]
            overlay.draw(sx - width / 2, sy - size / 2, width, size)


def rgb(hex_color):
    return tuple(int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))


def newell(points):
    nx = ny = nz = 0.0
    count = len(points)
    for i in range(count):
        x1, y1, z1 = points[i]
        x2, y2, z2 = points[(i + 1) % count]
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    return (nx, ny, nz)


def bounding_center(faces):
    points = [p for pts, _ in faces for p in pts]
    return tuple((min(p[i] for p in points) + max(p[i] for p in points)) / 2 for i in range(3))


class Scene:
    def __init__(self):
        faces, lines = build_model()
        self.center = bounding_center(faces)
        self.list_id = self._compile(faces, lines)
        self._chord_lists = {}
        self._hand_lists = {}
        self.help = help_overlay()
        self.labels = ChordLabels()
        self.hand = hand_overlay()
        self.fingers = FingerNumbers()

    def chord_list(self, name, index=0):
        if (name, index) not in self._chord_lists:
            self._chord_lists[name, index] = self._compile(chord_faces(name, index), ())
        return self._chord_lists[name, index]

    def hand_list(self, name, index=0):
        if (name, index) not in self._hand_lists:
            faces = hand_faces(name, index)
            self._hand_lists[name, index] = self._compile(faces, ()) if faces else None
        return self._hand_lists[name, index]

    def _compile(self, faces, lines):
        list_id = GL.glGenLists(1)
        GL.glNewList(list_id, GL.GL_COMPILE)
        for points, color in faces:
            normal = newell(points)
            GL.glColor3f(*rgb(color))
            GL.glNormal3f(*normal)
            GL.glBegin(GL.GL_POLYGON)
            for p in points:
                GL.glVertex3f(*p)
            GL.glEnd()
        GL.glDisable(GL.GL_LIGHTING)
        for a, b, color, width in lines:
            GL.glColor3f(*rgb(color))
            GL.glLineWidth(width)
            GL.glBegin(GL.GL_LINES)
            GL.glVertex3f(*a)
            GL.glVertex3f(*b)
            GL.glEnd()
        GL.glEnable(GL.GL_LIGHTING)
        GL.glEndList()
        return list_id


def init_gl():
    GL.glEnable(GL.GL_DEPTH_TEST)
    GL.glEnable(GL.GL_NORMALIZE)
    GL.glEnable(GL.GL_COLOR_MATERIAL)
    GL.glColorMaterial(GL.GL_FRONT_AND_BACK, GL.GL_AMBIENT_AND_DIFFUSE)
    GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_SPECULAR, (0.35, 0.35, 0.35, 1.0))
    GL.glMaterialf(GL.GL_FRONT_AND_BACK, GL.GL_SHININESS, 48.0)
    GL.glLightModelfv(GL.GL_LIGHT_MODEL_AMBIENT, (AMBIENT, AMBIENT, AMBIENT, 1.0))
    GL.glLightModeli(GL.GL_LIGHT_MODEL_TWO_SIDE, GL.GL_TRUE)
    GL.glEnable(GL.GL_LIGHTING)
    GL.glEnable(GL.GL_LIGHT0)
    GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, (0.85, 0.82, 0.76, 1.0))
    GL.glLightfv(GL.GL_LIGHT0, GL.GL_SPECULAR, (0.6, 0.6, 0.6, 1.0))


def draw_background():
    GL.glDisable(GL.GL_LIGHTING)
    GL.glDisable(GL.GL_DEPTH_TEST)
    GL.glMatrixMode(GL.GL_PROJECTION)
    GL.glLoadIdentity()
    GL.glMatrixMode(GL.GL_MODELVIEW)
    GL.glLoadIdentity()
    GL.glBegin(GL.GL_QUADS)
    GL.glColor3f(*rgb(BG_BOTTOM))
    GL.glVertex2f(-1, -1)
    GL.glVertex2f(1, -1)
    GL.glColor3f(*rgb(BG_TOP))
    GL.glVertex2f(1, 1)
    GL.glVertex2f(-1, 1)
    GL.glEnd()
    GL.glEnable(GL.GL_DEPTH_TEST)
    GL.glEnable(GL.GL_LIGHTING)


def field_of_view(zoom):
    return math.degrees(2 * math.atan(math.tan(math.radians(BASE_FOV / 2)) / zoom))


def over_panel(pos, panel_pos, size):
    return (panel_pos[0] <= pos[0] < panel_pos[0] + size[0]
            and panel_pos[1] <= pos[1] < panel_pos[1] + size[1])


def clamp_panel(pos, size):
    width, height = window_size()
    return (min(max(pos[0], 0), max(0, width - size[0])),
            min(max(pos[1], 0), max(0, height - size[1])))


def draw_frame(scene, yaw, pitch, zoom, pan=(0.0, 0.0), chord=None, show_help=False, voicing=0,
               panels=(), show_fingers=True, show_hand=True):
    width, height = window_size()
    GL.glViewport(0, 0, width, height)
    GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
    draw_background()

    GL.glMatrixMode(GL.GL_PROJECTION)
    GL.glLoadIdentity()
    GLU.gluPerspective(field_of_view(zoom), width / height, 10.0, 10000.0)

    GL.glMatrixMode(GL.GL_MODELVIEW)
    GL.glLoadIdentity()
    GLU.gluLookAt(0, 0, CAMERA_DISTANCE, 0, 0, 0, 0, 1, 0)
    GL.glLightfv(GL.GL_LIGHT0, GL.GL_POSITION, (*LIGHT, 0.0))
    GL.glTranslatef(pan[0], pan[1], 0)
    GL.glRotatef(math.degrees(pitch), 1, 0, 0)
    GL.glRotatef(math.degrees(yaw), 0, 1, 0)
    GL.glTranslatef(-scene.center[0], -scene.center[1], -scene.center[2])
    GL.glCallList(scene.list_id)
    if chord:
        GL.glCallList(scene.chord_list(chord, voicing))
        hand = scene.hand_list(chord, voicing) if show_hand else None
        if hand:
            GL.glCallList(hand)
        if show_fingers:
            scene.fingers.draw(finger_marks(chord, voicing))
    for overlay, pos in panels:
        overlay.draw(*pos)
    if show_help:
        scene.help.draw()


def run():
    pygame.init()
    layout = load_layout()
    maximized = layout.get("maximized", False)
    minimized = False
    requested_size = layout.get("window_size", (WIDTH, HEIGHT))
    if maximized:
        requested_size = layout.get("normal_size", (WIDTH, HEIGHT))
    desktop_size = pygame.display.get_desktop_sizes()[0]
    normal_size = tuple(min(requested, desktop) for requested, desktop in zip(requested_size, desktop_size))
    pygame.display.set_caption(caption(None))
    pygame.display.set_mode(normal_size, pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE)
    if maximized:
        Window.from_display_module().maximize()
        pygame.event.pump()
    size = window_size()
    init_gl()
    scene = Scene()

    view = layout.get("view", {})
    yaw = view.get("yaw", START_VIEW[0])
    pitch = max(-1.5, min(1.5, view.get("pitch", START_VIEW[1])))
    zoom = min(MAX_ZOOM, max(MIN_ZOOM, view.get("zoom", START_VIEW[2])))
    pan_x = view.get("pan_x", 0.0)
    pan_y = view.get("pan_y", 0.0)
    chord = None
    root = None
    type_index = 0
    voicing = 0
    last = load_last_chord()
    accidentals = {}
    natural = False
    if last:
        root, type_index, voicing, accidentals = last
        if root:
            chord = root + TYPES[type_index]
            pygame.display.set_caption(caption(chord, voicing))
    show_help = layout.get("show_help", False)
    saved_chords = SavedChords(load_saved_chords())
    shown = {"label": True, "hand": True, "saved": True}
    shown.update(layout.get("shown", {}))
    show_fingers = layout.get("show_fingers", True)
    show_hand = layout.get("show_hand", True)

    def default_positions():
        return {
            "label": (PANEL_MARGIN, PANEL_MARGIN),
            "hand": (size[0] - scene.hand.size[0] - PANEL_MARGIN, PANEL_MARGIN),
            "saved": (PANEL_MARGIN, size[1] - saved_chords.SIZE[1] - PANEL_MARGIN),
        }

    positions = default_positions()
    positions.update(layout.get("positions", {}))
    grab = (0, 0)
    grabbed = None
    dragging = None

    def visible_panels():
        found = []
        if shown["label"]:
            found.append(("label", scene.labels.get(chord, voicing)))
        if shown["hand"]:
            found.append(("hand", scene.hand))
        if shown["saved"]:
            found.append(("saved", saved_chords.get(chord, voicing)))
        return found

    def preview_current_chord():
        saved_chords.preview(root, type_index, voicing)

    def panel_at(pos):
        for name, overlay in reversed(visible_panels()):
            if over_panel(pos, positions[name], overlay.size):
                return name, overlay
        return None
    clock = pygame.time.Clock()
    running = True
    while running:
        events = pygame.event.get()
        resized = window_size()
        if resized != size:
            for name, (left, top) in positions.items():
                positions[name] = (
                    left + resized[0] - size[0] if left > size[0] / 2 else left,
                    top + resized[1] - size[1] if top > size[1] / 2 else top,
                )
            size = resized
        for event in events:
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.WINDOWMAXIMIZED:
                maximized = True
                minimized = False
            elif event.type == pygame.WINDOWMINIMIZED:
                minimized = True
            elif event.type == pygame.WINDOWRESTORED:
                if not minimized:
                    maximized = False
                minimized = False
            elif (show_help and event.type in (pygame.KEYDOWN, pygame.MOUSEWHEEL,
                                               pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP,
                                               pygame.MOUSEMOTION)
                  and not (event.type == pygame.KEYDOWN and event.key in (pygame.K_F1, pygame.K_ESCAPE, pygame.K_F12))):
                dragging = grabbed = None
                if scene.help.handle_event(event):
                    show_help = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if show_help:
                    show_help = False
                    scene.help.drag_offset = None
                elif saved_chords.selected is not None:
                    root, type_index, voicing = saved_chords.cancel()
                    chord = root + TYPES[type_index]
                    accidentals[root[0]] = root[1:]
                    natural = False
                    pygame.display.set_caption(caption(chord, voicing))
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if not show_help:
                    if saved_chords.selected is not None:
                        saved_chords.confirm(accidentals)
                    elif chord:
                        save_last_chord(root, type_index, voicing, accidentals)
                        saved_chords.remember(root, type_index, voicing)
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_UP, pygame.K_DOWN):
                if not show_help:
                    direction = 1 if event.key == pygame.K_DOWN else -1
                    current = (root, type_index, voicing) if chord else None
                    entry = saved_chords.browse(direction, current)
                    if entry is not None:
                        root, type_index, voicing = entry
                        chord = root + TYPES[type_index]
                        accidentals[root[0]] = root[1:]
                        natural = False
                        pygame.display.set_caption(caption(chord, voicing))
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
                show_help = not show_help
                scene.help.drag_offset = None
                dragging = grabbed = None
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F2:
                shown["label"] = not shown["label"]
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F4:
                shown["hand"] = not shown["hand"]
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F5:
                show_fingers = not show_fingers
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F6:
                show_hand = not show_hand
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F7:
                shown["saved"] = not shown["saved"]
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F3:
                if chord:
                    root = root[0]
                    accidentals[root] = ""
                    chord = root + TYPES[type_index]
                    voicing = 0
                    natural = False
                    preview_current_chord()
                    pygame.display.set_caption(caption(chord, voicing))
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                yaw, pitch, zoom = START_VIEW
                pan_x = pan_y = 0.0
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F12:
                window = Window.from_display_module()
                window.restore()
                desktop_size = pygame.display.get_desktop_sizes()[0]
                window.size = (min(WIDTH, desktop_size[0]), min(HEIGHT, desktop_size[1]))
                pygame.event.pump()
                size = window_size()
                normal_size = size
                maximized = minimized = False
                positions = default_positions()
                shown = {"label": True, "hand": True, "saved": True}
                show_help = False
                show_fingers = show_hand = True
                yaw, pitch, zoom = START_VIEW
                pan_x = pan_y = 0.0
                grab = (0, 0)
                grabbed = dragging = None
                if saved_chords.reset():
                    chord = root = None
                    type_index = voicing = 0
                    accidentals.clear()
                    natural = False
                    pygame.display.set_caption(caption(None))
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_n:
                natural = True
            elif event.type == pygame.KEYDOWN and event.key in ROOT_KEYS:
                picked = root_name(event.key, event.mod, accidentals, natural)
                natural = False
                if picked is not None:
                    if picked == root and chord:
                        voicing = (voicing + 1) % len(voicings(chord))
                    else:
                        root = picked
                        chord = root + TYPES[type_index]
                        voicing = 0
                    pygame.display.set_caption(caption(chord, voicing))
                    preview_current_chord()
            elif event.type == pygame.KEYDOWN and event.key in TYPE_KEYS:
                natural = False
                type_index = TYPE_KEYS[event.key]
                chord = root + TYPES[type_index] if chord else None
                voicing = 0
                pygame.display.set_caption(caption(chord, voicing))
                if chord:
                    preview_current_chord()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_BACKSPACE:
                if show_help:
                    continue
                if saved_chords.selected is not None and not saved_chords.delete_selected():
                    continue
                saved_chords.draft = None
                saved_chords.browsed = None
                saved_chords.scroll(0)
                natural = False
                chord = None
                voicing = 0
                pygame.display.set_caption(caption(chord))
            elif (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                  and not show_help
                  and (grabbed := panel_at(event.pos))):
                grab = (event.pos[0] - positions[grabbed[0]][0], event.pos[1] - positions[grabbed[0]][1])
                index = saved_chords.index_at(grab) if grabbed[0] == "saved" else None
                if index is not None:
                    dragging = None
                    if saved_chords.selected is None:
                        saved_chords.select(index)
                        root, type_index, voicing = saved_chords.draft
                        chord = root + TYPES[type_index]
                        accidentals[root[0]] = root[1:]
                        natural = False
                        pygame.display.set_caption(caption(chord, voicing))
                else:
                    dragging = "panel"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 2, 3):
                shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
                dragging = "pan" if event.button in (2, 3) or shift else "rotate"
            elif event.type == pygame.MOUSEBUTTONUP and event.button in (1, 2, 3):
                dragging = None
            elif event.type == pygame.MOUSEMOTION and dragging == "panel":
                name, overlay = grabbed
                positions[name] = clamp_panel((event.pos[0] - grab[0], event.pos[1] - grab[1]), overlay.size)
            elif event.type == pygame.MOUSEMOTION and dragging == "rotate":
                dx, dy = event.rel
                yaw += dx * 0.01
                pitch = max(-1.5, min(1.5, pitch + dy * 0.01))
            elif event.type == pygame.MOUSEMOTION and dragging == "pan":
                dx, dy = event.rel
                visible = 2 * CAMERA_DISTANCE * math.tan(math.radians(field_of_view(zoom) / 2))
                per_pixel = visible / size[1]
                pan_x += dx * per_pixel
                pan_y -= dy * per_pixel
            elif event.type == pygame.MOUSEWHEEL:
                hovered = panel_at(pygame.mouse.get_pos()) if not show_help else None
                if hovered and hovered[0] == "saved":
                    saved_chords.scroll(-event.y)
                else:
                    zoom = min(MAX_ZOOM, max(MIN_ZOOM, zoom * ZOOM_STEP ** event.y))

        if not maximized and not minimized:
            normal_size = size
        panels = visible_panels()
        for name, overlay in panels:
            positions[name] = clamp_panel(positions[name], overlay.size)
        draw_frame(scene, yaw, pitch, zoom, (pan_x, pan_y), chord, show_help, voicing,
                   [(overlay, positions[name]) for name, overlay in panels], show_fingers, show_hand)
        pygame.display.flip()
        clock.tick(60)

    save_layout({
        "view": {"yaw": yaw, "pitch": pitch, "zoom": zoom, "pan_x": pan_x, "pan_y": pan_y},
        "window_size": size,
        "normal_size": normal_size,
        "maximized": maximized,
        "positions": positions,
        "shown": shown,
        "show_help": show_help,
        "show_fingers": show_fingers,
        "show_hand": show_hand,
    })
    pygame.quit()
