from .body import body_faces
from .parts import (
    body_decal_faces, bridge_faces, headstock_faces, neck_faces, string_lines,
)


def build_model():
    faces = body_faces()
    faces += body_decal_faces()
    faces += neck_faces()
    faces += headstock_faces()
    faces += bridge_faces()
    return faces, string_lines()
