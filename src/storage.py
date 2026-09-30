"""Persistência simples em JSON. Sem banco de dados: é um totem de prototipagem."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List

DEFAULT_PATH = Path("data/state.json")


@dataclass
class UserState:
    total_squats: int = 0
    unlocked_achievements: List[str] = field(default_factory=list)


def load_state(path: Path = DEFAULT_PATH) -> UserState:
    if not path.exists():
        return UserState()
    data = json.loads(path.read_text(encoding="utf-8"))
    return UserState(
        total_squats=data.get("total_squats", 0),
        unlocked_achievements=data.get("unlocked_achievements", []),
    )


def save_state(state: UserState, path: Path = DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(state), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
