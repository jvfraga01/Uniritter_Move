"""Baixa o modelo da Tasks API (pose_landmarker_lite.task) para models/.

Roda uma vez, antes do primeiro `python main.py`:
    python -m tools.download_model
"""
from __future__ import annotations

import os
import urllib.request

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
)
DEST = os.path.join(os.path.dirname(__file__), "..", "models", "pose_landmarker_lite.task")


def main() -> None:
    os.makedirs(os.path.dirname(DEST), exist_ok=True)
    if os.path.exists(DEST):
        print(f"Modelo já existe em {DEST}, nada a fazer.")
        return
    print(f"Baixando modelo de:\n  {MODEL_URL}\npara:\n  {DEST}")
    urllib.request.urlretrieve(MODEL_URL, DEST)
    print("Pronto.")


if __name__ == "__main__":
    main()
