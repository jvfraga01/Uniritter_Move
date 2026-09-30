import pytest

from src.pose_metrics import StandingBaseline, visible_midpoint_y


def test_visible_midpoint_y_averages_visible_points():
    points = [(0.4, 0.9), (0.6, 0.9)]
    assert visible_midpoint_y(points) == pytest.approx(0.5)


def test_visible_midpoint_y_ignores_low_visibility_points():
    points = [(0.4, 0.9), (0.9, 0.1)]  # segundo ponto não confiável
    assert visible_midpoint_y(points) == pytest.approx(0.4)


def test_visible_midpoint_y_returns_none_if_nothing_visible():
    points = [(0.4, 0.1), (0.6, 0.05)]
    assert visible_midpoint_y(points) is None


def test_visible_midpoint_y_ignores_points_outside_the_frame():
    # o mediapipe extrapola uma posição com visibility alta mesmo quando o
    # ponto real está fora do quadro capturado (ex.: pé cortado por baixo,
    # pessoa perto demais da câmera) -- y > 1.0 nesse caso. Isso não pode
    # contar como "visível" mesmo com visibility=0.99.
    points = [(0.5, 0.9), (1.4, 0.99)]
    assert visible_midpoint_y(points) == pytest.approx(0.5)

    points_all_out_of_frame = [(-0.1, 0.9), (1.2, 0.95)]
    assert visible_midpoint_y(points_all_out_of_frame) is None


def test_standing_baseline_starts_uncalibrated():
    baseline = StandingBaseline(warmup_frames=3)
    assert not baseline.is_calibrated
    assert baseline.drop_ratio(hip_y=0.6, knee_y=0.8) is None


def test_standing_baseline_calibrates_after_warmup():
    baseline = StandingBaseline(warmup_frames=3)

    baseline.update(hip_y=0.5, knee_y=0.75, is_standing=True)
    baseline.update(hip_y=0.5, knee_y=0.75, is_standing=True)
    assert not baseline.is_calibrated  # ainda não bateu o warmup

    baseline.update(hip_y=0.5, knee_y=0.75, is_standing=True)
    assert baseline.is_calibrated
    assert baseline.hip_knee_gap == pytest.approx(0.25)


def test_drop_ratio_after_calibration():
    baseline = StandingBaseline(warmup_frames=1)
    baseline.update(hip_y=0.5, knee_y=0.75, is_standing=True)  # gap calibrado = 0.25

    # quadril desceu até 0.625 (y cresce pra baixo) -> gap agora = 0.125,
    # que é metade do gap calibrado -> drop_ratio = 0.5
    assert baseline.drop_ratio(hip_y=0.625, knee_y=0.75) == pytest.approx(0.5)


def test_drop_ratio_is_robust_to_moving_closer_to_camera():
    # a pessoa se aproxima da câmera: tudo fica maior em pixels, inclusive
    # o gap quadril-joelho -- mas a PROPORÇÃO da queda continua igual, já
    # que hip_y e knee_y são medidos no mesmo frame.
    baseline = StandingBaseline(warmup_frames=1)
    baseline.update(hip_y=0.5, knee_y=0.75, is_standing=True)  # gap = 0.25, longe da câmera

    # mais perto da câmera: gap "em pé" dobraria (0.5) se calibrasse de novo,
    # mas aqui simulamos o quadril na mesma FRAÇÃO de queda (50%) já mais
    # perto -- o método antigo (baseado em posição de pixel) erraria isso.
    ratio_longe = baseline.drop_ratio(hip_y=0.625, knee_y=0.75)

    baseline2 = StandingBaseline(warmup_frames=1)
    baseline2.update(hip_y=0.3, knee_y=0.8, is_standing=True)  # gap = 0.5, perto da câmera
    ratio_perto = baseline2.drop_ratio(hip_y=0.55, knee_y=0.8)  # mesma fração de queda (50%)

    assert ratio_longe == pytest.approx(ratio_perto)


def test_baseline_does_not_drift_while_squatting():
    baseline = StandingBaseline(warmup_frames=1, smoothing=0.5)
    baseline.update(hip_y=0.5, knee_y=0.75, is_standing=True)

    # em pleno agachamento (is_standing=False): baseline não deve mudar
    baseline.update(hip_y=0.7, knee_y=0.75, is_standing=False)

    assert baseline.hip_knee_gap == pytest.approx(0.25)


def test_baseline_adapts_slowly_while_standing():
    baseline = StandingBaseline(warmup_frames=1, smoothing=0.5)
    baseline.update(hip_y=0.5, knee_y=0.75, is_standing=True)  # gap = 0.25

    baseline.update(hip_y=0.5, knee_y=0.85, is_standing=True)  # gap = 0.35

    assert baseline.hip_knee_gap == pytest.approx(0.30)  # média ponderada (smoothing=0.5)


def test_reset_clears_calibration():
    baseline = StandingBaseline(warmup_frames=1)
    baseline.update(hip_y=0.5, knee_y=0.75, is_standing=True)
    assert baseline.is_calibrated

    baseline.reset()

    assert not baseline.is_calibrated
    assert baseline.drop_ratio(hip_y=0.5, knee_y=0.75) is None
