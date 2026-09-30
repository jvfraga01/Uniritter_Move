"""Funções geométricas puras, sem dependência de câmera ou mediapipe.

Isoladas aqui para serem testadas com números simples, sem precisar
de uma webcam ou de um frame de imagem real.
"""
from __future__ import annotations

import math
from typing import Tuple

Point = Tuple[float, float]


def angle_3pts(a: Point, b: Point, c: Point) -> float:
    """Ângulo em graus no vértice `b`, formado pelos pontos a-b-c.

    Exemplo: quadril (a) - joelho (b) - tornozelo (c) dá o ângulo do joelho.
    Perna esticada -> ~180°. Agachado -> ângulo menor (perto de 90-110°).
    """
    ax, ay = a
    bx, by = b
    cx, cy = c

    ba = (ax - bx, ay - by)
    bc = (cx - bx, cy - by)

    mag_ba = math.hypot(*ba)
    mag_bc = math.hypot(*bc)
    if mag_ba == 0 or mag_bc == 0:
        return 0.0

    dot = ba[0] * bc[0] + ba[1] * bc[1]
    cos_angle = max(-1.0, min(1.0, dot / (mag_ba * mag_bc)))
    return math.degrees(math.acos(cos_angle))
