"""Desenho simples de HUD no frame: esqueleto, estado da sessão, botões
(meta de reps e odômetro geral) e toasts de achievement."""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import cv2

from .achievements import Achievement
from .session import SessionState

Rect = Tuple[int, int, int, int]  # x1, y1, x2, y2


def draw_skeleton(frame, landmarks, connections: Sequence[Tuple[int, int]]) -> None:
    """Desenha os pontos e "ossos" do MediaPipe Pose sobre o frame (BGR),
    convertendo coordenadas normalizadas (0..1) pra pixels."""
    h, w = frame.shape[:2]
    points = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]

    for i, j in connections:
        cv2.line(frame, points[i], points[j], (0, 220, 255), 2, cv2.LINE_AA)
    for x, y in points:
        cv2.circle(frame, (x, y), 4, (0, 140, 255), -1, cv2.LINE_AA)


def draw_session_hud(
    frame,
    session_state: SessionState,
    session_count: int,
    target_reps: int,
    depth_ratio: Optional[float] = None,
    calibrating: bool = False,
    distance_ok: bool = True,
) -> None:
    if session_state == SessionState.WAITING_FOR_PERSON:
        cv2.putText(
            frame, "Aguardando pessoa...", (20, 50),
            cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 200, 255), 3, cv2.LINE_AA,
        )
        return

    if session_state == SessionState.COMPLETE:
        cv2.putText(
            frame, "Sessao completa!", (20, 50),
            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3, cv2.LINE_AA,
        )
        cv2.putText(
            frame, "Afaste-se e volte pra jogar de novo", (20, 90),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2, cv2.LINE_AA,
        )
        return

    cv2.putText(
        frame, f"Sessao: {session_count}/{target_reps}", (20, 50),
        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3, cv2.LINE_AA,
    )

    # Feedback de enquadramento: o app só consegue medir o agachamento com
    # margem segura se quadril, joelho e tornozelo estiverem visíveis (ver
    # pose_estimator.get_leg_joints_y) -- sem essa margem, o quadril sai de
    # quadro assim que a pessoa agacha.
    if not distance_ok:
        cv2.putText(
            frame, "Ajuste a distancia: pernas inteiras precisam aparecer",
            (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 140, 255), 2, cv2.LINE_AA,
        )
        return

    cv2.putText(
        frame, "Distancia ideal detectada", (20, 90),
        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA,
    )

    if calibrating:
        depth_text = "calibrando... fique em pe parado"
    elif depth_ratio is not None:
        depth_text = f"{depth_ratio * 100:.0f}%"
    else:
        depth_text = "sem deteccao confiavel"

    cv2.putText(
        frame, f"Queda do quadril: {depth_text}", (20, 120),
        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2, cv2.LINE_AA,
    )


def draw_target_button(frame, target_reps: int, minus_rect: Rect, plus_rect: Rect, enabled: bool) -> None:
    """Desenha o botao [-] Meta: N [+] pra escolher agachamentos por
    sessao. `enabled` controla se o botao aparece ativo (sessao aguardando
    pessoa) ou apagado (sessao em andamento, nao editavel)."""
    color = (255, 255, 255) if enabled else (90, 90, 90)

    for rect, label in ((minus_rect, "-"), (plus_rect, "+")):
        x1, y1, x2, y2 = rect
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
        cv2.putText(
            frame, label, (x1 + 10, y2 - 8),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA,
        )

    label_x = minus_rect[2] + 15
    cv2.putText(
        frame, f"Meta: {target_reps}", (label_x, minus_rect[3] - 8),
        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA,
    )


def draw_sensitivity_button(frame, bottom_threshold: float, minus_rect: Rect, plus_rect: Rect) -> None:
    """Desenha o botao [-] Sensibilidade: N% [+] que ajusta o quanto o
    quadril precisa descer (bottom_threshold) pra confirmar um
    agachamento. Editavel a qualquer momento, inclusive durante a sessao,
    pra dar pra calibrar na hora vendo o percentual de queda no HUD."""
    color = (255, 255, 255)

    for rect, label in ((minus_rect, "-"), (plus_rect, "+")):
        x1, y1, x2, y2 = rect
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
        cv2.putText(
            frame, label, (x1 + 10, y2 - 8),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA,
        )

    label_x = minus_rect[2] + 15
    cv2.putText(
        frame, f"Sensibilidade: {bottom_threshold * 100:.0f}%", (label_x, minus_rect[3] - 8),
        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA,
    )


def draw_restart_button(frame, rect: Rect) -> None:
    """Botao que zera a sessao (contagem, calibracao, achievements) na
    hora, sem precisar sair e voltar pro quadro da camera."""
    x1, y1, x2, y2 = rect
    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(
        frame, "Reiniciar sessao", (x1 + 8, y2 - 10),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA,
    )


def draw_total_button(frame, rect: Rect) -> None:
    x1, y1, x2, y2 = rect
    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(
        frame, "Total geral", (x1 + 8, y2 - 10),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA,
    )


def draw_total_readout(frame, lifetime_total: int) -> None:
    """Painel tipo odometro: total historico de agachamentos no
    aparelho, acumulado entre todas as sessoes."""
    h, w = frame.shape[:2]
    panel_w, panel_h = 420, 140
    x1 = (w - panel_w) // 2
    y1 = (h - panel_h) // 2

    overlay = frame.copy()
    cv2.rectangle(overlay, (x1, y1), (x1 + panel_w, y1 + panel_h), (30, 30, 30), -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
    cv2.rectangle(frame, (x1, y1), (x1 + panel_w, y1 + panel_h), (255, 255, 255), 2, cv2.LINE_AA)

    cv2.putText(
        frame, "TOTAL GERAL", (x1 + 30, y1 + 45),
        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2, cv2.LINE_AA,
    )
    cv2.putText(
        frame, f"{lifetime_total} agachamentos", (x1 + 30, y1 + 100),
        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 215, 255), 3, cv2.LINE_AA,
    )


def draw_new_achievements(frame, achievements: List[Achievement]) -> None:
    for i, ach in enumerate(achievements):
        y = 170 + i * 40
        cv2.putText(
            frame, f"🏆 {ach.name}", (20, y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 215, 255), 2, cv2.LINE_AA,
        )
