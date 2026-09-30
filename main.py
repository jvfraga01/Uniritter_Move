"""Orquestrador: loop principal do protótipo no PC.

Fluxo: webcam -> mediapipe -> (hip_y, knee_y) -> StandingBaseline
(calibração automática da distância quadril-joelho) -> razão de queda do
quadril -> SquatCounter -> SessionManager -> AchievementEngine -> overlay.
Cada seta é uma camada separada (veja src/), trocável e testável
isoladamente.

Sessão: toda vez que uma pessoa é detectada na frente da câmera, zera a
contagem e a calibração e começa uma sessão nova com meta de repetições
configurável (botão [-]/[+] na tela, clicável com o mouse). O total
histórico de agachamentos (independente de sessão) fica persistido à
parte, como um odômetro -- ver botão "Total geral". O botão "Reiniciar
sessão" faz a mesma coisa na hora, sem precisar sair e voltar pro quadro.
"""
from __future__ import annotations

import cv2

from src.achievements import AchievementEngine
from src.capture import WebcamSource
from src.overlay import (
    draw_new_achievements,
    draw_restart_button,
    draw_sensitivity_button,
    draw_session_hud,
    draw_skeleton,
    draw_target_button,
    draw_total_button,
    draw_total_readout,
)
from src.pose_estimator import POSE_CONNECTIONS, PoseEstimator
from src.pose_metrics import StandingBaseline
from src.session import SessionEvent, SessionManager, SessionState
from src.smoothing import MovingAverage
from src.squat_counter import SquatCounter
from src.storage import load_state, save_state

WINDOW_NAME = "Totem de Agachamentos - protótipo"

MINUS_RECT = (20, 140, 60, 180)
PLUS_RECT = (200, 140, 240, 180)
TOTAL_BUTTON_RECT = (20, 200, 180, 240)
SENS_MINUS_RECT = (20, 260, 60, 300)
SENS_PLUS_RECT = (200, 260, 240, 300)
RESTART_BUTTON_RECT = (20, 320, 220, 360)

SENSITIVITY_STEP = 0.02
# limite inferior fica acima de standing_threshold (0.10) pra sempre sobrar
# uma faixa real de "descendo" entre os dois limiares.
MIN_BOTTOM_THRESHOLD = 0.12
MAX_BOTTOM_THRESHOLD = 0.45


def _point_in_rect(x: int, y: int, rect) -> bool:
    x1, y1, x2, y2 = rect
    return x1 <= x <= x2 and y1 <= y <= y2


def main() -> None:
    state = load_state()
    lifetime_total = state.total_squats

    counter = SquatCounter()
    session = SessionManager()
    achievements = AchievementEngine()
    pose_estimator = PoseEstimator()
    baseline = StandingBaseline()
    ratio_smoother = MovingAverage(window_size=5)

    last_new_achievements = []
    display_ratio = None
    show_total_readout = False
    click = {"pos": None}

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            click["pos"] = (x, y)

    cv2.namedWindow(WINDOW_NAME)
    cv2.setMouseCallback(WINDOW_NAME, on_mouse)

    with WebcamSource(camera_index=0) as webcam:
        while True:
            frame = webcam.read()
            if frame is None:
                print("Falha ao ler frame da webcam, encerrando.")
                break

            frame = cv2.flip(frame, 1)  # espelha, fica mais natural pro usuário
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            landmarks = pose_estimator.process(frame_rgb)

            # Presença = mediapipe reconheceu uma pessoa no frame, mesmo que a
            # confiança de quadril/joelho caia por 1-2 frames (comum durante
            # o próprio agachamento). Só essa perda TOTAL de detecção deve
            # encerrar a sessão -- não a perda momentânea de confiança usada
            # abaixo pra calibração/contagem, senão a sessão reseta no meio
            # do movimento e nenhum agachamento chega a fechar.
            person_present = landmarks is not None
            session_event = session.update_presence(person_present)
            if session_event in (SessionEvent.STARTED, SessionEvent.PERSON_LOST):
                counter.reset()
                baseline.reset()
                ratio_smoother.reset()
                achievements = AchievementEngine()
                last_new_achievements = []
                display_ratio = None

            hip_y = knee_y = ankle_y = None
            if landmarks is not None:
                hip_y, knee_y, ankle_y = pose_estimator.get_leg_joints_y(landmarks)

            # Distância ideal = os três joints da perna (quadril, joelho e
            # tornozelo) visíveis o suficiente -- sem o tornozelo em quadro,
            # o quadril tende a sair de quadro assim que a pessoa agacha.
            distance_ok = hip_y is not None and knee_y is not None and ankle_y is not None

            if session.state == SessionState.ACTIVE and distance_ok:
                if not baseline.is_calibrated:
                    baseline.update(hip_y, knee_y, is_standing=True)
                    display_ratio = 0.0
                else:
                    raw_ratio = baseline.drop_ratio(hip_y, knee_y)
                    display_ratio = ratio_smoother.update(raw_ratio)
                    just_counted = counter.update(display_ratio)
                    baseline.update(hip_y, knee_y, is_standing=counter.is_standing)

                    if just_counted:
                        session.record_rep()
                        lifetime_total += 1
                        state.total_squats = lifetime_total
                        save_state(state)
                        last_new_achievements = achievements.check(session.session_count)
            else:
                display_ratio = None

            if landmarks is not None:
                draw_skeleton(frame, landmarks, POSE_CONNECTIONS)

            draw_session_hud(
                frame, session.state, session.session_count, session.config.target_reps,
                depth_ratio=display_ratio, calibrating=not baseline.is_calibrated,
                distance_ok=distance_ok,
            )
            draw_new_achievements(frame, last_new_achievements)

            target_editable = session.state == SessionState.WAITING_FOR_PERSON
            draw_target_button(frame, session.config.target_reps, MINUS_RECT, PLUS_RECT, target_editable)
            draw_total_button(frame, TOTAL_BUTTON_RECT)
            draw_sensitivity_button(frame, counter.config.bottom_threshold, SENS_MINUS_RECT, SENS_PLUS_RECT)
            draw_restart_button(frame, RESTART_BUTTON_RECT)
            if show_total_readout:
                draw_total_readout(frame, lifetime_total)

            if click["pos"] is not None:
                cx, cy = click["pos"]
                if target_editable and _point_in_rect(cx, cy, MINUS_RECT):
                    session.set_target(session.config.target_reps - 1)
                elif target_editable and _point_in_rect(cx, cy, PLUS_RECT):
                    session.set_target(session.config.target_reps + 1)
                elif _point_in_rect(cx, cy, TOTAL_BUTTON_RECT):
                    show_total_readout = not show_total_readout
                elif _point_in_rect(cx, cy, SENS_MINUS_RECT):
                    counter.config.bottom_threshold = max(
                        MIN_BOTTOM_THRESHOLD, counter.config.bottom_threshold - SENSITIVITY_STEP
                    )
                elif _point_in_rect(cx, cy, SENS_PLUS_RECT):
                    counter.config.bottom_threshold = min(
                        MAX_BOTTOM_THRESHOLD, counter.config.bottom_threshold + SENSITIVITY_STEP
                    )
                elif _point_in_rect(cx, cy, RESTART_BUTTON_RECT):
                    counter.reset()
                    baseline.reset()
                    ratio_smoother.reset()
                    achievements = AchievementEngine()
                    last_new_achievements = []
                    display_ratio = None
                    session.reset()
                    if person_present:
                        session.update_presence(True)  # já volta pra sessão ativa
                click["pos"] = None

            cv2.imshow(WINDOW_NAME, frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    pose_estimator.close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
