"""Entrada do ponteiro. A UI só pergunta 'onde está o cursor?' (0-1, 0-1)."""
import time
import urllib.request
from pathlib import Path

import pygame


class MousePointer:
    """Modo de desenvolvimento: o mouse simula o pulso do usuário."""

    window_space = True  # coordenadas relativas à janela (a UI corrige as barras pretas)

    def __init__(self, size=None):
        self.size = size

    def get(self):
        x, y = pygame.mouse.get_pos()
        w, h = pygame.display.get_surface().get_size()  # janela pode ser redimensionada
        return x / w, y / h


class WristPointer:
    """Adaptador para o MediaPipe Pose.

    `source` é uma função sem argumentos que devolve (x, y) normalizados do
    pulso (landmark 16 = direito, 15 = esquerdo) ou None se não houver pessoa.
    A imagem da câmera é espelhada, então invertemos o x. Suavização EMA
    para o cursor não tremer.
    """

    def __init__(self, source, smooth=0.35):
        self.source, self.smooth, self.pos = source, smooth, None

    def get(self):
        p = self.source()
        if p is None:
            self.pos = None
            return None
        x, y = 1.0 - p[0], p[1]
        if self.pos is None:
            self.pos = (x, y)
        else:
            a = self.smooth
            self.pos = (self.pos[0] + a * (x - self.pos[0]),
                        self.pos[1] + a * (y - self.pos[1]))
        return self.pos


HAND_MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
                  "hand_landmarker/float16/1/hand_landmarker.task")


def ensure_hand_model(root=None):
    """Baixa o modelo de mãos do MediaPipe (~8 MB) na primeira execução."""
    root = Path(root) if root else Path(__file__).resolve().parent.parent
    path = root / "models" / "hand_landmarker.task"
    if not path.exists():
        print("[UI] Baixando modelo de mãos (uma vez só)...")
        path.parent.mkdir(exist_ok=True)
        urllib.request.urlretrieve(HAND_MODEL_URL, path)
    return path


class HandPointer:
    """Cursor controlado pela ponta do dedo indicador (landmark 8 do MediaPipe Hands).

    A UI chama feed(frame) a cada quadro novo da câmera (já espelhado, BGR) e
    get() devolve (x, y) em 0-1 sobre a tela, ou None se não houver mão.
    A região central da câmera (MARGIN..1-MARGIN) é esticada para a tela toda,
    assim a pessoa alcança os cantos sem esticar o braço até a borda da imagem.
    """

    MARGIN = 0.12

    def __init__(self, model_path, smooth=0.45):
        import cv2
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        self.cv2, self.mp, self.smooth = cv2, mp, smooth
        opts = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO, num_hands=1)
        self.det = vision.HandLandmarker.create_from_options(opts)
        self.t0, self.last_ts, self.pos = time.time(), -1, None

    def feed(self, frame):
        rgb = self.cv2.cvtColor(self.cv2.resize(frame, (480, 270)), self.cv2.COLOR_BGR2RGB)
        img = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb)
        ts = max(int((time.time() - self.t0) * 1000), self.last_ts + 1)  # deve crescer sempre
        self.last_ts = ts
        res = self.det.detect_for_video(img, ts)
        if not res.hand_landmarks:
            self.pos = None
            return
        tip = res.hand_landmarks[0][8]  # ponta do indicador
        m = self.MARGIN
        x = min(max((tip.x - m) / (1 - 2 * m), 0.0), 1.0)
        y = min(max((tip.y - m) / (1 - 2 * m), 0.0), 1.0)
        if self.pos is None:
            self.pos = (x, y)
        else:
            a = self.smooth
            self.pos = (self.pos[0] + a * (x - self.pos[0]), self.pos[1] + a * (y - self.pos[1]))

    def get(self):
        return self.pos