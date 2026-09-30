"""Máquina de estados de sessão: quando uma pessoa é detectada na frente
da câmera, zera e começa uma sessão nova com meta de repetições; quando a
pessoa some, volta a esperar. Propositalmente NÃO sabe nada sobre câmera,
mediapipe ou frames de vídeo -- só recebe booleanos/eventos de contagem,
igual squat_counter.py e achievements.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class SessionState(Enum):
    WAITING_FOR_PERSON = auto()
    ACTIVE = auto()
    COMPLETE = auto()


class SessionEvent(Enum):
    STARTED = auto()
    PERSON_LOST = auto()
    COMPLETED = auto()


@dataclass
class SessionConfig:
    target_reps: int = 10
    # nº de frames seguidos sem detectar ninguém antes de considerar que a
    # pessoa foi embora. Filtra falhas de detecção de 1-2 frames do
    # mediapipe durante o próprio movimento do agachamento -- sem isso, a
    # sessão resetava no meio da descida e nenhum agachamento fechava.
    absence_grace_frames: int = 10


@dataclass
class SessionManager:
    config: SessionConfig = field(default_factory=SessionConfig)
    state: SessionState = SessionState.WAITING_FOR_PERSON
    session_count: int = 0

    _missed_frames: int = field(default=0, repr=False)

    def update_presence(self, present: bool) -> Optional[SessionEvent]:
        """Chamado a cada frame com se há uma pessoa detectada. Retorna o
        evento da transição (início/fim de sessão) ou None se nada mudou."""
        if self.state == SessionState.COMPLETE:
            # Trava em COMPLETE: sair e voltar do quadro não reinicia mais
            # a sessão sozinho -- só um reset() explícito (botão "Reiniciar
            # sessão") tira daqui.
            return None

        if present:
            self._missed_frames = 0
            if self.state == SessionState.WAITING_FOR_PERSON:
                self.state = SessionState.ACTIVE
                self.session_count = 0
                return SessionEvent.STARTED
            return None

        if self.state == SessionState.WAITING_FOR_PERSON:
            return None

        self._missed_frames += 1
        if self._missed_frames >= self.config.absence_grace_frames:
            self.state = SessionState.WAITING_FOR_PERSON
            self.session_count = 0
            self._missed_frames = 0
            return SessionEvent.PERSON_LOST

        return None

    def record_rep(self) -> Optional[SessionEvent]:
        """Chamado quando o SquatCounter confirma uma repetição. Só conta
        durante uma sessão ativa; retorna COMPLETED se a meta foi atingida
        agora."""
        if self.state != SessionState.ACTIVE:
            return None

        self.session_count += 1
        if self.session_count >= self.config.target_reps:
            self.state = SessionState.COMPLETE
            return SessionEvent.COMPLETED
        return None

    def set_target(self, target_reps: int) -> None:
        self.config.target_reps = max(1, target_reps)

    def reset(self) -> None:
        self.state = SessionState.WAITING_FOR_PERSON
        self.session_count = 0
        self._missed_frames = 0
