"""Wrapper fino em torno da MediaPipe Tasks API (PoseLandmarker).

Usamos a API nova (`mediapipe.tasks`), não a antiga `mediapipe.solutions`.
A API legada foi descontinuada pelo Google em 2023 e, em várias versões
recentes do pacote, o atributo `mediapipe.solutions` vem quebrado/ausente
no Windows -- é um bug conhecido e recorrente do próprio pacote, não do
nosso código.

Extrai só o que a lógica de domínio precisa: a posição vertical do
quadril e do joelho (para o método de contagem por queda do quadril em
relação ao joelho -- ver src/pose_metrics.py e src/squat_counter.py).
Medir a distância entre dois pontos do mesmo frame em vez da posição
absoluta do quadril é o que torna o sinal robusto a a pessoa se mover no
espaço (mais perto/longe/de lado da câmera) entre a calibração e o
agachamento.

Requer o arquivo de modelo `models/pose_landmarker_lite.task`.
Baixe uma vez com: `python -m tools.download_model`.
"""
from __future__ import annotations

import os
import time
from typing import Optional, Sequence, Tuple

import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions

from .pose_metrics import visible_midpoint_y

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "pose_landmarker_lite.task")

# Mesma numeração de landmarks da MediaPipe Pose (33 pontos): 23/24 =
# quadril esquerdo/direito, 25/26 = joelho esquerdo/direito, 27/28 =
# tornozelo esquerdo/direito.
LEFT_HIP = 23
RIGHT_HIP = 24
LEFT_KNEE = 25
RIGHT_KNEE = 26
LEFT_ANKLE = 27
RIGHT_ANKLE = 28

# Pares de índices de landmark que formam os "ossos" do esqueleto, pra
# desenho (ver src/overlay.py:draw_skeleton). Hardcoded porque
# mediapipe.solutions.pose.POSE_CONNECTIONS (que teria isso pronto) não
# está disponível na API mediapipe.tasks usada aqui -- ver docstring do
# topo deste arquivo. Cobre tronco, braços e pernas (ignora detalhes do
# rosto, que não importam pra forma do agachamento).
POSE_CONNECTIONS: Tuple[Tuple[int, int], ...] = (
    # ombros e braços
    (11, 12),
    (11, 13), (13, 15),
    (12, 14), (14, 16),
    # tronco
    (11, 23), (12, 24), (23, 24),
    # perna esquerda
    (23, 25), (25, 27), (27, 29), (29, 31), (27, 31),
    # perna direita
    (24, 26), (26, 28), (28, 30), (30, 32), (28, 32),
)


def _visibility(landmark) -> float:
    return getattr(landmark, "visibility", 1.0) or 0.0


class PoseEstimator:
    def __init__(
        self,
        model_path: str = MODEL_PATH,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ):
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Modelo não encontrado em '{model_path}'.\n"
                "Rode primeiro: python -m tools.download_model"
            )
        options = vision.PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._landmarker = vision.PoseLandmarker.create_from_options(options)
        self._start_time_ms = time.time() * 1000
        self._last_timestamp_ms = -1

    def process(self, frame_rgb) -> Optional[Sequence]:
        """Recebe um frame RGB (numpy array) e devolve a lista de landmarks
        (x, y, z, visibility normalizados 0..1) do frame atual, ou None se
        nenhuma pessoa foi detectada."""
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        # detect_for_video exige timestamps (ms) ESTRITAMENTE crescentes --
        # quando dois frames são processados rápido o suficiente pra cair no
        # mesmo milissegundo (int truncado), o wall-clock sozinho repete um
        # valor e a lib lança ValueError, derrubando o app inteiro. Forçamos
        # o mínimo de +1ms sobre o timestamp anterior pra nunca colidir.
        timestamp_ms = max(
            int(time.time() * 1000 - self._start_time_ms),
            self._last_timestamp_ms + 1,
        )
        self._last_timestamp_ms = timestamp_ms
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)
        if not result.pose_landmarks:
            return None
        return result.pose_landmarks[0]

    @staticmethod
    def get_leg_joints_y(
        landmarks, min_visibility: float = 0.5
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Extrai (hip_y, knee_y, ankle_y) em coordenadas normalizadas
        (0..1, já independentes da resolução da câmera). hip_y/knee_y
        alimentam StandingBaseline/SquatCounter; ankle_y só é usado como
        validação de enquadramento ("distância ideal" -- ver main.py):
        exigir os três joints visíveis garante que a perna inteira está em
        quadro, senão o quadril tende a sair de quadro assim que a pessoa
        agacha. Cada valor pode vir None se não houver dados confiáveis o
        suficiente nesse frame."""
        hip_points = [
            (landmarks[LEFT_HIP].y, _visibility(landmarks[LEFT_HIP])),
            (landmarks[RIGHT_HIP].y, _visibility(landmarks[RIGHT_HIP])),
        ]
        hip_y = visible_midpoint_y(hip_points, min_visibility=min_visibility)

        knee_points = [
            (landmarks[LEFT_KNEE].y, _visibility(landmarks[LEFT_KNEE])),
            (landmarks[RIGHT_KNEE].y, _visibility(landmarks[RIGHT_KNEE])),
        ]
        knee_y = visible_midpoint_y(knee_points, min_visibility=min_visibility)

        ankle_points = [
            (landmarks[LEFT_ANKLE].y, _visibility(landmarks[LEFT_ANKLE])),
            (landmarks[RIGHT_ANKLE].y, _visibility(landmarks[RIGHT_ANKLE])),
        ]
        ankle_y = visible_midpoint_y(ankle_points, min_visibility=min_visibility)

        return hip_y, knee_y, ankle_y

    def close(self) -> None:
        self._landmarker.close()
