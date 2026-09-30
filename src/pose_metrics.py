"""Cálculos puros de métricas da pose usados pelo método de contagem por
queda do quadril em relação ao joelho. Só recebem números (coordenadas y
e visibilidade) -- sem depender de mediapipe, opencv ou webcam. É isso
que os torna 100% testáveis sem câmera."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Tuple

PointVis = Tuple[float, float]  # (y, visibility)


def visible_midpoint_y(points: Iterable[PointVis], min_visibility: float = 0.5) -> Optional[float]:
    """Média do y entre pontos visíveis o suficiente e DENTRO do quadro
    (ex.: quadril esquerdo/direito). Retorna None se nenhum estiver
    visível.

    O score de "visibility" do mediapipe mede oclusão, não se o ponto está
    dentro da imagem capturada -- quando um pé sai por baixo do quadro
    (pessoa perto demais da câmera), o modelo ainda extrapola uma posição
    com visibility alta, só que com y fora de [0, 1] (fora da tela). Por
    isso o filtro de y também é necessário aqui, não só o de visibility.
    """
    ys = [y for y, vis in points if vis >= min_visibility and 0.0 <= y <= 1.0]
    if not ys:
        return None
    return sum(ys) / len(ys)


@dataclass
class StandingBaseline:
    """Calibração contínua e automática da distância "quadril até joelho"
    quando em pé.

    Por que existe: em vez de pedir pra calibrar manualmente (botão), a
    baseline se ajusta sozinha sempre que o contador confirma que a pessoa
    está parada em pé -- assim cada pessoa nova que usa o totem é
    recalibrada automaticamente, sem fricção.

    Por que quadril-joelho e não "altura total da pose" (versão antiga):
    a distância entre dois pontos DO MESMO FRAME é local -- ela se
    recalcula do zero a cada leitura, então não importa se a pessoa se
    afastou, chegou mais perto ou se moveu de lado desde a calibração; o
    sinal continua proporcional ao quanto o quadril desceu em relação ao
    joelho, não à posição absoluta em pixels. A versão antiga (hip_y
    relativo a uma posição de pixel calibrada, normalizado pela altura
    total da pose) quebrava exatamente nesse cenário: mover-se no espaço
    mudava a leitura mesmo sem agachar.

    `warmup_frames`: quantos frames iniciais são usados pra calibração
    inicial (assume que a pessoa começa parada em pé). `smoothing`:
    o quanto cada leitura nova pesa na atualização da baseline depois
    disso (0 = nunca mais atualiza, 1 = sempre usa só o valor mais
    recente).
    """

    smoothing: float = 0.15
    warmup_frames: int = 15

    hip_knee_gap: Optional[float] = None  # distância (em y) quadril->joelho quando em pé

    _warmup_gap: List[float] = field(default_factory=list, repr=False)

    @property
    def is_calibrated(self) -> bool:
        return self.hip_knee_gap is not None

    def update(self, hip_y: float, knee_y: float, is_standing: bool) -> None:
        gap = knee_y - hip_y
        if gap <= 0:
            return

        if not self.is_calibrated:
            self._warmup_gap.append(gap)
            if len(self._warmup_gap) >= self.warmup_frames:
                self.hip_knee_gap = sum(self._warmup_gap) / len(self._warmup_gap)
            return

        if is_standing:
            self.hip_knee_gap = (1 - self.smoothing) * self.hip_knee_gap + self.smoothing * gap

    def drop_ratio(self, hip_y: float, knee_y: float) -> Optional[float]:
        """Quanto o quadril desceu agora em relação ao joelho (medidos no
        mesmo frame), como fração da distância quadril-joelho calibrada em
        pé (0.0 = na baseline, 0.5 = o gap encolheu pela metade). None se
        ainda não calibrado."""
        if not self.is_calibrated:
            return None
        gap = knee_y - hip_y
        return 1 - (gap / self.hip_knee_gap)

    def reset(self) -> None:
        self.hip_knee_gap = None
        self._warmup_gap.clear()
