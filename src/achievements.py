"""Regras de achievements: puro Python, sem I/O (exceto persistência em storage.py)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Set


@dataclass(frozen=True)
class Achievement:
    id: str
    name: str
    description: str
    threshold: int  # total de agachamentos necessário


DEFAULT_ACHIEVEMENTS: List[Achievement] = [
    Achievement("first_squat", "Primeiro Passo", "Complete seu 1º agachamento", 1),
    Achievement("warmup_5", "Aquecendo", "Complete 5 agachamentos", 5),
    Achievement("getting_serious_10", "Ficando Sério", "Complete 10 agachamentos", 10),
    Achievement("quarter_century_25", "Quarto de Século", "Complete 25 agachamentos", 25),
    Achievement("half_century_50", "Meia Centena", "Complete 50 agachamentos", 50),
    Achievement("century_100", "Centena!", "Complete 100 agachamentos", 100),
]


class AchievementEngine:
    def __init__(
        self,
        achievements: Optional[Iterable[Achievement]] = None,
        unlocked: Optional[Iterable[str]] = None,
    ) -> None:
        self.achievements = list(achievements) if achievements is not None else list(DEFAULT_ACHIEVEMENTS)
        self.unlocked: Set[str] = set(unlocked or [])

    def check(self, total_count: int) -> List[Achievement]:
        """Dado o total de agachamentos até agora, retorna a lista de
        achievements recém-desbloqueados (pode ser vazia)."""
        newly: List[Achievement] = []
        for ach in self.achievements:
            if ach.id not in self.unlocked and total_count >= ach.threshold:
                self.unlocked.add(ach.id)
                newly.append(ach)
        return newly
