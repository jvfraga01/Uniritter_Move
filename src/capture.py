"""Abstração da fonte de vídeo. Hoje é a webcam do PC; amanhã pode virar
uma câmera IP ou USB dedicada no totem, sem mudar o resto do app."""
from __future__ import annotations

import cv2


class WebcamSource:
    def __init__(self, camera_index: int = 0, max_reconnect_attempts: int = 3):
        self.camera_index = camera_index
        self.max_reconnect_attempts = max_reconnect_attempts
        self._cap = None

    def __enter__(self) -> "WebcamSource":
        if not self._try_open():
            raise RuntimeError(f"Não foi possível abrir a câmera {self.camera_index}")
        return self

    def _try_open(self) -> bool:
        # CAP_DSHOW evita um bug conhecido do backend padrão (Media
        # Foundation) no Windows, que às vezes para de entregar frames do
        # nada depois de alguns segundos de uso, sem erro nenhum.
        self._cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        return self._cap.isOpened()

    def __exit__(self, *exc) -> None:
        if self._cap is not None:
            self._cap.release()

    def read(self):
        """Retorna um frame BGR (formato OpenCV) ou None se falhar mesmo
        depois de tentar reabrir a câmera (mitiga o bug do MSMF acima).
        Uma falha ao RECONECTAR (câmera momentaneamente ocupada/lenta pra
        responder) não deve derrubar o app -- só falha esse frame, o loop
        principal tenta de novo no próximo."""
        ok, frame = self._cap.read()
        if ok:
            return frame

        for _ in range(self.max_reconnect_attempts):
            self._cap.release()
            if not self._try_open():
                continue
            ok, frame = self._cap.read()
            if ok:
                return frame
        return None
