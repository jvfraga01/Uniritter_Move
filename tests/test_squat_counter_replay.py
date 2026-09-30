"""Teste de 'replay': reproduz uma sessão sintética de (hip_y, knee_y)
-- simula o que tools/record_session.py grava de uma sessão real -- pelo
pipeline completo (StandingBaseline -> suavização -> SquatCounter ->
AchievementEngine) e verifica que o resultado bate com o esperado.

Quando você gravar uma sessão de verdade (python -m tools.record_session),
troque o fixture abaixo pelo CSV gravado e ajuste o número esperado de reps.
"""
import csv
from pathlib import Path

from src.achievements import AchievementEngine
from src.pose_metrics import StandingBaseline
from src.smoothing import MovingAverage
from src.squat_counter import SquatCounter

FIXTURE = Path(__file__).parent / "fixtures" / "sample_squat_sequence.csv"


def load_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [(float(row["hip_y"]), float(row["knee_y"])) for row in reader]


def test_replay_sample_session_counts_expected_reps_and_unlocks_achievement():
    rows = load_rows(FIXTURE)

    baseline = StandingBaseline()
    ratio_smoother = MovingAverage(window_size=5)
    counter = SquatCounter()
    achievements = AchievementEngine()
    unlocked_during_session = []

    for hip_y, knee_y in rows:
        if not baseline.is_calibrated:
            baseline.update(hip_y, knee_y, is_standing=True)
            continue

        raw_ratio = baseline.drop_ratio(hip_y, knee_y)
        smoothed_ratio = ratio_smoother.update(raw_ratio)

        if counter.update(smoothed_ratio):
            unlocked_during_session.extend(achievements.check(counter.count))

        baseline.update(hip_y, knee_y, is_standing=counter.is_standing)

    # o CSV de exemplo contém 5 agachamentos completos
    assert counter.count == 5
    assert {a.id for a in unlocked_during_session} == {"first_squat", "warmup_5"}
