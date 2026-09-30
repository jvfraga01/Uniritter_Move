"""Máquina de estados que conta agachamentos a partir de uma leitura de
profundidade normalizada (0.0 = em pé na baseline, valores maiores =
mais fundo). Hoje esse sinal é "quanto o quadril caiu, como fração da
altura da pose de pé" (ver pose_metrics.StandingBaseline), mas o contador
em si não sabe nada disso -- só recebe um número por frame.

Propositalmente NÃO sabe nada sobre câmera, mediapipe ou frames de vídeo.
Isso é o que torna essa peça 100% testável sem webcam.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class SquatState(Enum):
    STANDING = auto()
    DESCENDING = auto()
    BOTTOM = auto()
    ASCENDING = auto()


@dataclass
class SquatCounterConfig:
    # valor <= este => considerado "em pé" (perto da baseline)
    standing_threshold: float = 0.10
    # valor >= este => considerado "no fundo" (profundidade válida). Ex.:
    # 0.20 = quadril desceu 20% da altura da pose de pé. Ajustável em tempo
    # real pelo botão de sensibilidade (ver main.py) -- 0.35 (valor antigo)
    # se mostrou alto demais na prática: numa webcam de mesa comum, um
    # agachamento real raramente passa de ~30% mesmo bem profundo.
    bottom_threshold: float = 0.20
    # nº de frames seguidos no fundo antes de confirmar (filtra ruído)
    min_frames_at_bottom: int = 1


@dataclass
class SquatCounter:
    config: SquatCounterConfig = field(default_factory=SquatCounterConfig)
    state: SquatState = SquatState.STANDING
    count: int = 0

    _frames_at_bottom: int = field(default=0, repr=False)
    _reached_valid_depth: bool = field(default=False, repr=False)

    @property
    def is_standing(self) -> bool:
        return self.state == SquatState.STANDING

    def update(self, depth: float) -> bool:
        """Processa uma leitura de profundidade (um frame). Retorna True
        se um agachamento válido acabou de ser contado nesta chamada."""
        cfg = self.config
        counted = False

        if self.state == SquatState.STANDING:
            if depth > cfg.standing_threshold:
                self.state = SquatState.DESCENDING
                self._reached_valid_depth = False
                self._frames_at_bottom = 0

        elif self.state == SquatState.DESCENDING:
            if depth >= cfg.bottom_threshold:
                self._frames_at_bottom += 1
                if self._frames_at_bottom >= cfg.min_frames_at_bottom:
                    self.state = SquatState.BOTTOM
                    self._reached_valid_depth = True
            elif depth <= cfg.standing_threshold:
                # voltou perto da baseline sem descer o suficiente: não conta
                self.state = SquatState.STANDING
                self._frames_at_bottom = 0

        elif self.state == SquatState.BOTTOM:
            if depth < cfg.bottom_threshold:
                self.state = SquatState.ASCENDING

        elif self.state == SquatState.ASCENDING:
            if depth <= cfg.standing_threshold:
                self.state = SquatState.STANDING
                if self._reached_valid_depth:
                    self.count += 1
                    counted = True
                self._reached_valid_depth = False

        return counted

    def reset(self) -> None:
        self.state = SquatState.STANDING
        self.count = 0
        self._frames_at_bottom = 0
        self._reached_valid_depth = False
