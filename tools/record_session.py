"""Ferramenta de dev: grava a sequência real de (hip_y, knee_y) de
uma sessão de webcam num CSV.

Por quê: agachamentos reais têm ruído, jitter do mediapipe, oclusões etc.
Gravando uma sessão real uma vez, você ganha um "replay" determinístico
para usar em testes de regressão sem precisar ligar a câmera de novo
toda hora. Veja tests/test_squat_counter_replay.py.

Uso:
    python -m tools.record_session --out tests/fixtures/minha_sessao.csv
"""
from __future__ import annotations

import argparse
import csv
import time

import cv2

from src.capture import WebcamSource
from src.pose_estimator import PoseEstimator


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="tests/fixtures/sessao_gravada.csv")
    parser.add_argument("--camera-index", type=int, default=0)
    args = parser.parse_args()

    pose_estimator = PoseEstimator()
    rows = []

    with WebcamSource(camera_index=args.camera_index) as webcam:
        print("Gravando... pressione 'q' na janela de vídeo para parar.")
        start = time.time()
        while True:
            frame = webcam.read()
            if frame is None:
                break
            frame = cv2.flip(frame, 1)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            landmarks = pose_estimator.process(frame_rgb)
            if landmarks is not None:
                hip_y, knee_y, _ankle_y = pose_estimator.get_leg_joints_y(landmarks)
                if hip_y is not None and knee_y is not None:
                    rows.append((time.time() - start, hip_y, knee_y))

            cv2.imshow("Gravando sessão (q para sair)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    pose_estimator.close()
    cv2.destroyAllWindows()

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["t_seconds", "hip_y", "knee_y"])
        writer.writerows(rows)

    print(f"{len(rows)} frames salvos em {args.out}")


if __name__ == "__main__":
    main()
