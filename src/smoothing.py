"""Suavização simples de um sinal ruidoso (ex.: ângulo do joelho frame a
frame). Reduz o efeito de jitter do mediapipe -- picos de 1-2 frames que
poderiam disparar falsos positivos na contagem de agachamentos."""
from __future__ import annotations

from collections import deque
from typing import Deque


class MovingAverage:
    def __init__(self, window_size: int = 5):
        if window_size < 1:
            raise ValueError("window_size deve ser >= 1")
        self.window_size = window_size
        self._values: Deque[float] = deque(maxlen=window_size)

    def update(self, value: float) -> float:
        """Adiciona um novo valor à janela e retorna a média móvel atual."""
        self._values.append(value)
        return sum(self._values) / len(self._values)

    def reset(self) -> None:
        self._values.clear()
